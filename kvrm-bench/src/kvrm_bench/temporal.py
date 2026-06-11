from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.types import DecisionInput

from .counterfactual import DEFAULT_CASE_PACK_DIR_NAME, load_or_generate_boundary_counterfactual_cases
from .demo import DOMAIN_CONFIG, STRATEGY_ORDER, _cached_runtime_for_strategy, load_cases
from .metrics import (
    DEFAULT_DECISION_COSTS,
    DEFAULT_REGRET_COSTS,
    compute_metrics,
    compute_regret_metrics,
)

DEFAULT_TEMPORAL_THRESHOLD = 0.60
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_REPORT_JSON = "temporal_transition_report.json"
DEFAULT_REPORT_MD = "temporal_transition_report.md"
DEFAULT_SEQUENCES_JSON = "temporal_transition_sequences.json"

TRANSITION_ORDER = (
    "supported_action_switch",
    "supported_to_unsupported_fail_closed",
    "unsupported_to_supported_recovery",
)


def generate_temporal_transition_sequences(
    *,
    repo_root: str | Path,
    domain: str,
    artifact_dir: str | Path | None = None,
    refresh_counterfactual_cases: bool = False,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported temporal domain: {domain}")

    results_dir = repo_root / DEFAULT_RESULTS_DIR if artifact_dir is None else Path(artifact_dir)
    counterfactual_case_dir = results_dir / DEFAULT_CASE_PACK_DIR_NAME
    counterfactual_payload = load_or_generate_boundary_counterfactual_cases(
        repo_root=repo_root,
        domain=domain,
        artifact_dir=counterfactual_case_dir,
        refresh=refresh_counterfactual_cases,
    )

    data_dir = repo_root / DOMAIN_CONFIG[domain]["data_dir"]
    base_cases = {
        case["case_id"]: case
        for case in load_cases(data_dir / "cases.jsonl")
        if case.get("supported", True)
    }

    selected_counterfactuals: dict[tuple[str, str, str], dict[str, Any]] = {}
    for case in counterfactual_payload["cases"]:
        base_case = base_cases.get(case["base_case_id"])
        if base_case is None:
            continue
        if not case.get("supported", True):
            key = (
                base_case["case_id"],
                case["mutated_feature"],
                "supported_to_unsupported_fail_closed",
            )
            selected_counterfactuals.setdefault(key, case)
            continue
        if case.get("expected_action_id") != base_case.get("expected_action_id"):
            key = (
                base_case["case_id"],
                case["mutated_feature"],
                "supported_action_switch",
            )
            selected_counterfactuals.setdefault(key, case)

    sequences: list[dict[str, Any]] = []
    transition_type_counts: Counter[str] = Counter()
    mutated_feature_counts: Counter[str] = Counter()
    for key in sorted(selected_counterfactuals):
        base_case_id, mutated_feature, transition_type = key
        base_case = base_cases[base_case_id]
        counterfactual_case = selected_counterfactuals[key]
        if transition_type == "supported_action_switch":
            sequence = _build_sequence(
                sequence_id=f"{counterfactual_case['case_id']}:switch",
                transition_type=transition_type,
                mutated_feature=mutated_feature,
                source_case_pack=counterfactual_payload,
                steps=[base_case, counterfactual_case],
            )
            sequences.append(sequence)
            transition_type_counts[transition_type] += 1
            mutated_feature_counts[mutated_feature] += 1
            continue

        fail_closed_sequence = _build_sequence(
            sequence_id=f"{counterfactual_case['case_id']}:fail_closed",
            transition_type="supported_to_unsupported_fail_closed",
            mutated_feature=mutated_feature,
            source_case_pack=counterfactual_payload,
            steps=[base_case, counterfactual_case],
        )
        recovery_sequence = _build_sequence(
            sequence_id=f"{counterfactual_case['case_id']}:recovery",
            transition_type="unsupported_to_supported_recovery",
            mutated_feature=mutated_feature,
            source_case_pack=counterfactual_payload,
            steps=[counterfactual_case, base_case],
        )
        sequences.extend([fail_closed_sequence, recovery_sequence])
        transition_type_counts["supported_to_unsupported_fail_closed"] += 1
        transition_type_counts["unsupported_to_supported_recovery"] += 1
        mutated_feature_counts[mutated_feature] += 2

    return {
        "domain": domain,
        "source_supported_case_count": len(base_cases),
        "source_counterfactual_case_count": counterfactual_payload["generated_case_count"],
        "sequence_count": len(sequences),
        "transition_type_counts": {
            transition_type: transition_type_counts.get(transition_type, 0)
            for transition_type in TRANSITION_ORDER
        },
        "mutated_feature_counts": dict(sorted(mutated_feature_counts.items())),
        "counterfactual_case_pack_path": counterfactual_payload["case_pack_path"],
        "counterfactual_case_pack_signature": counterfactual_payload["case_pack_signature"],
        "counterfactual_case_pack_source": counterfactual_payload["case_pack_source"],
        "sequences": sequences,
    }


def run_temporal_transition_benchmark(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_TEMPORAL_THRESHOLD,
    learned_model_paths: dict[str, str | Path] | None = None,
    output_dir: str | Path | None = None,
    refresh_counterfactual_cases: bool = False,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    active_domains = list(domains or DOMAIN_CONFIG.keys())
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "domains": {},
        "summary": {},
    }
    sequences_payload: dict[str, Any] = {}

    hybrid_wins = 0
    hybrid_ties = 0
    hybrid_losses = 0

    for domain in active_domains:
        sequence_pack = generate_temporal_transition_sequences(
            repo_root=repo_root,
            domain=domain,
            artifact_dir=results_dir,
            refresh_counterfactual_cases=refresh_counterfactual_cases,
        )
        sequences = sequence_pack["sequences"]
        sequences_payload[domain] = sequences
        strategy_payloads: dict[str, dict[str, Any]] = {}
        learned_model_path = _resolve_learned_model_path(repo_root, domain, learned_model_paths)

        for strategy in STRATEGY_ORDER:
            runtime, _ = _cached_runtime_for_strategy(
                str(repo_root),
                domain,
                "cases.jsonl",
                strategy,
                str(learned_model_path) if learned_model_path is not None else None,
                threshold,
            )
            if runtime is None:
                continue

            step_case_results: list[dict[str, Any]] = []
            sequence_results: list[dict[str, Any]] = []
            for sequence in sequences:
                step_results: list[dict[str, Any]] = []
                for step_index, case in enumerate(sequence["steps"], start=1):
                    decision = runtime.decide_and_execute(
                        DecisionInput(
                            case_id=case["case_id"],
                            features=case["input_features"],
                            supported=case.get("supported", True),
                            ood=case.get("ood", False),
                            expected_action_id=case.get("expected_action_id"),
                        )
                    )
                    case_result = _decision_to_case_result(case, decision.model_dump(mode="json"))
                    case_result["step_index"] = step_index
                    case_result["sequence_id"] = sequence["sequence_id"]
                    case_result["transition_type"] = sequence["transition_type"]
                    step_case_results.append(case_result)
                    step_results.append(case_result)
                sequence_results.append(_evaluate_sequence(sequence, step_results))

            strategy_payloads[strategy] = {
                "sequence_count": len(sequence_results),
                "step_case_count": len(step_case_results),
                "metrics": compute_metrics(step_case_results),
                "regret": compute_regret_metrics(step_case_results),
                "sequence_metrics": compute_temporal_sequence_metrics(sequence_results),
            }

        best_non_hybrid_strategy = _best_non_hybrid_strategy(strategy_payloads)
        hybrid_payload = strategy_payloads["hybrid"]
        baseline_payload = strategy_payloads[best_non_hybrid_strategy]
        hybrid_sequence_regret = hybrid_payload["sequence_metrics"]["mean_sequence_regret"]
        baseline_sequence_regret = baseline_payload["sequence_metrics"]["mean_sequence_regret"]
        if hybrid_sequence_regret < baseline_sequence_regret:
            hybrid_wins += 1
        elif hybrid_sequence_regret > baseline_sequence_regret:
            hybrid_losses += 1
        else:
            hybrid_ties += 1

        payload["domains"][domain] = {
            **{key: value for key, value in sequence_pack.items() if key != "sequences"},
            "strategies": strategy_payloads,
            "comparison": {
                "best_non_hybrid_strategy": best_non_hybrid_strategy,
                "hybrid_sequence_regret_gain": baseline_sequence_regret - hybrid_sequence_regret,
                "hybrid_sequence_cost_reduction": (
                    baseline_payload["sequence_metrics"]["mean_sequence_cost"]
                    - hybrid_payload["sequence_metrics"]["mean_sequence_cost"]
                ),
                "hybrid_transition_success_gain": (
                    hybrid_payload["sequence_metrics"]["all_steps_success_rate"]
                    - baseline_payload["sequence_metrics"]["all_steps_success_rate"]
                ),
                "hybrid_recovery_success_gain": (
                    hybrid_payload["sequence_metrics"]["recovery_success_rate"]
                    - baseline_payload["sequence_metrics"]["recovery_success_rate"]
                ),
            },
        }

    payload["summary"] = {
        "domain_count": len(active_domains),
        "hybrid_win_count": hybrid_wins,
        "hybrid_tie_count": hybrid_ties,
        "hybrid_loss_count": hybrid_losses,
    }
    report_paths = write_temporal_transition_reports(payload, sequences_payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    payload["sequences_json"] = str(report_paths["sequences"])
    return payload


def compute_temporal_sequence_metrics(sequence_results: list[dict[str, Any]]) -> dict[str, float]:
    def rate(items: list[dict[str, Any]], pred) -> float:
        if not items:
            return 0.0
        return sum(1 for item in items if pred(item)) / len(items)

    def mean(items: list[dict[str, Any]], key: str) -> float:
        if not items:
            return 0.0
        return sum(float(item[key]) for item in items) / len(items)

    def subset(transition_type: str) -> list[dict[str, Any]]:
        return [
            item
            for item in sequence_results
            if item["transition_type"] == transition_type
        ]

    recovery_sequences = subset("unsupported_to_supported_recovery")
    fail_closed_sequences = subset("supported_to_unsupported_fail_closed")
    switch_sequences = subset("supported_action_switch")

    return {
        "mean_sequence_regret": mean(sequence_results, "sequence_regret"),
        "mean_sequence_cost": mean(sequence_results, "sequence_cost"),
        "all_steps_success_rate": rate(sequence_results, lambda item: bool(item["all_steps_success"])),
        "any_fallback_rate": rate(sequence_results, lambda item: bool(item["any_fallback_used"])),
        "any_invalid_output_rate": rate(sequence_results, lambda item: bool(item["any_invalid_output"])),
        "recovery_success_rate": rate(recovery_sequences, lambda item: bool(item["transition_success"])),
        "fail_closed_transition_success_rate": rate(fail_closed_sequences, lambda item: bool(item["transition_success"])),
        "action_switch_success_rate": rate(switch_sequences, lambda item: bool(item["transition_success"])),
    }


def render_temporal_transition_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Temporal Transition Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "This benchmark lifts the cached single-step counterfactual pack into deterministic two-step "
            "temporal transitions. It measures whether each strategy stays safe when a supported state "
            "slides into unsupported territory, recovers cleanly when support returns, and switches "
            "actions correctly when the supported target changes across time."
        ),
        "",
        (
            f"Hybrid comparison summary: wins={payload['summary']['hybrid_win_count']}, "
            f"ties={payload['summary']['hybrid_tie_count']}, "
            f"losses={payload['summary']['hybrid_loss_count']}."
        ),
        "",
        "| Domain | Sequences | Recovery | Fail-Closed | Switch | Hybrid Success | Hybrid Seq Regret | Best Non-Hybrid | Baseline Seq Regret | Gain |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]

    for domain, domain_payload in payload["domains"].items():
        hybrid = domain_payload["strategies"]["hybrid"]
        baseline_name = domain_payload["comparison"]["best_non_hybrid_strategy"]
        baseline = domain_payload["strategies"][baseline_name]
        lines.append(
            "| "
            f"{domain} | "
            f"{domain_payload['sequence_count']} | "
            f"{domain_payload['transition_type_counts']['unsupported_to_supported_recovery']} | "
            f"{domain_payload['transition_type_counts']['supported_to_unsupported_fail_closed']} | "
            f"{domain_payload['transition_type_counts']['supported_action_switch']} | "
            f"{hybrid['sequence_metrics']['all_steps_success_rate']:.4f} | "
            f"{hybrid['sequence_metrics']['mean_sequence_regret']:.4f} | "
            f"{baseline_name} | "
            f"{baseline['sequence_metrics']['mean_sequence_regret']:.4f} | "
            f"{domain_payload['comparison']['hybrid_sequence_regret_gain']:.4f} |"
        )
        lines.append(
            f"Transitions `{domain}`: "
            + ", ".join(
                f"{transition_type}={count}"
                for transition_type, count in domain_payload["transition_type_counts"].items()
            )
        )
        lines.append(
            f"Features `{domain}`: "
            + ", ".join(
                f"{feature}={count}"
                for feature, count in domain_payload["mutated_feature_counts"].items()
            )
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_temporal_transition_reports(
    payload: dict[str, Any],
    sequences_payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / DEFAULT_REPORT_JSON
    report_md = output_dir / DEFAULT_REPORT_MD
    sequences_json = output_dir / DEFAULT_SEQUENCES_JSON
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_temporal_transition_markdown(payload), encoding="utf-8")
    sequences_json.write_text(json.dumps(sequences_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"json": report_json, "md": report_md, "sequences": sequences_json}


def _build_sequence(
    *,
    sequence_id: str,
    transition_type: str,
    mutated_feature: str,
    source_case_pack: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "sequence_id": sequence_id,
        "transition_type": transition_type,
        "mutated_feature": mutated_feature,
        "counterfactual_case_pack_path": source_case_pack["case_pack_path"],
        "counterfactual_case_pack_signature": source_case_pack["case_pack_signature"],
        "steps": [dict(step) for step in steps],
    }


def _evaluate_sequence(sequence: dict[str, Any], step_results: list[dict[str, Any]]) -> dict[str, Any]:
    if len(step_results) != 2:
        raise ValueError("temporal transition benchmark currently expects exactly two steps per sequence")

    all_steps_success = all(_step_success(step_result) for step_result in step_results)
    transition_type = sequence["transition_type"]
    if transition_type == "supported_action_switch":
        transition_success = (
            bool(step_results[0].get("correct", False))
            and bool(step_results[1].get("correct", False))
            and step_results[0].get("selected_action_id") != step_results[1].get("selected_action_id")
        )
    elif transition_type == "supported_to_unsupported_fail_closed":
        transition_success = (
            bool(step_results[0].get("correct", False))
            and _is_safe_reject(step_results[1])
        )
    elif transition_type == "unsupported_to_supported_recovery":
        transition_success = (
            _is_safe_reject(step_results[0])
            and bool(step_results[1].get("correct", False))
        )
    else:
        raise ValueError(f"unsupported temporal transition type: {transition_type}")

    return {
        "sequence_id": sequence["sequence_id"],
        "transition_type": transition_type,
        "sequence_regret": sum(_regret_score(step_result) for step_result in step_results),
        "sequence_cost": sum(_decision_cost(step_result) for step_result in step_results),
        "all_steps_success": all_steps_success,
        "transition_success": transition_success,
        "any_fallback_used": any(bool(step_result.get("fallback_used", False)) for step_result in step_results),
        "any_invalid_output": any(not bool(step_result.get("valid", False)) for step_result in step_results),
    }


def _step_success(step_result: dict[str, Any]) -> bool:
    if bool(step_result.get("supported", True)):
        return bool(step_result.get("correct", False))
    return _is_safe_reject(step_result)


def _is_safe_reject(step_result: dict[str, Any]) -> bool:
    return step_result.get("final_status") in {"abstained", "fallback_executed", "fail_closed"}


def _decision_cost(case_result: dict[str, Any]) -> float:
    return _outcome_score(case_result, DEFAULT_DECISION_COSTS)


def _regret_score(case_result: dict[str, Any]) -> float:
    return _outcome_score(case_result, DEFAULT_REGRET_COSTS)


def _outcome_score(case_result: dict[str, Any], costs: dict[str, float]) -> float:
    supported = bool(case_result.get("supported", True))
    final_status = case_result.get("final_status")
    correct = bool(case_result.get("correct", False))
    if supported:
        if correct:
            return costs["supported_correct"]
        if final_status in {"abstained", "fallback_executed", "fail_closed", "validation_failed"}:
            return costs["supported_abstain"]
        return costs["supported_misroute"]
    if final_status == "executed":
        return costs["unsupported_false_accept"]
    return costs["unsupported_safe_reject"]


def _decision_to_case_result(case: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "expected_action_id": case.get("expected_action_id"),
        "supported": case.get("supported", True),
        "ood": case.get("ood", False),
        "selected_action_id": decision.get("selected_action_id"),
        "confidence": decision.get("confidence"),
        "valid": bool(decision.get("valid", False)),
        "correct": bool(decision.get("correct", False)),
        "abstained": bool(decision.get("abstained", False)),
        "fallback_used": bool(decision.get("fallback_used", False)),
        "latency_ms": float(decision.get("latency_ms", 0.0) or 0.0),
        "final_status": decision.get("final_status"),
        "validation_reason": decision.get("validation_reason"),
    }


def _best_non_hybrid_strategy(strategy_payloads: dict[str, dict[str, Any]]) -> str:
    non_hybrid = {
        strategy: payload
        for strategy, payload in strategy_payloads.items()
        if strategy != "hybrid"
    }
    if not non_hybrid:
        raise ValueError("temporal benchmark requires at least one non-hybrid strategy")
    return min(
        non_hybrid,
        key=lambda strategy: (
            non_hybrid[strategy]["sequence_metrics"]["mean_sequence_regret"],
            non_hybrid[strategy]["sequence_metrics"]["mean_sequence_cost"],
            -non_hybrid[strategy]["sequence_metrics"]["all_steps_success_rate"],
        ),
    )


def _resolve_learned_model_path(
    repo_root: Path,
    domain: str,
    learned_model_paths: dict[str, str | Path] | None,
) -> Path | None:
    if learned_model_paths and domain in learned_model_paths:
        path = Path(learned_model_paths[domain])
        return path if path.exists() else None
    default_path = repo_root / "kvrm-models" / f"{domain}_compact_selector_v1.joblib"
    return default_path if default_path.exists() else None
