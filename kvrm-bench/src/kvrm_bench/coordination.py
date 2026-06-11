from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.types import DecisionInput

from .counterfactual import DEFAULT_CASE_PACK_DIR_NAME, load_or_generate_boundary_counterfactual_cases
from .demo import DOMAIN_CONFIG, STRATEGY_ORDER, _cached_runtime_for_strategy, load_cases
from .temporal import _decision_to_case_result, _is_safe_reject, _outcome_score, _resolve_learned_model_path
from .metrics import DEFAULT_DECISION_COSTS, DEFAULT_REGRET_COSTS, compute_metrics, compute_regret_metrics

DEFAULT_COORDINATION_THRESHOLD = 0.60
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_REPORT_JSON = "coordination_chain_report.json"
DEFAULT_REPORT_MD = "coordination_chain_report.md"
DEFAULT_CHAINS_JSON = "coordination_chain_sequences.json"

CHAIN_TYPE_ORDER = (
    "supported_fail_closed_recovery",
    "supported_switch_fail_closed",
    "fail_closed_recovery_switch",
    # 5-step chain types
    "full_degradation_recovery_switch_stabilize",
    "cascading_fail_progressive_recovery",
)


def generate_coordination_chain_sequences(
    *,
    repo_root: str | Path,
    domain: str,
    artifact_dir: str | Path | None = None,
    refresh_counterfactual_cases: bool = False,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported coordination domain: {domain}")

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

    supported_switches: dict[str, list[dict[str, Any]]] = {}
    unsupported_cases: dict[str, list[dict[str, Any]]] = {}
    for case in counterfactual_payload["cases"]:
        base_case = base_cases.get(case["base_case_id"])
        if base_case is None:
            continue
        if not case.get("supported", True):
            unsupported_cases.setdefault(base_case["case_id"], []).append(case)
            continue
        if case.get("expected_action_id") != base_case.get("expected_action_id"):
            supported_switches.setdefault(base_case["case_id"], []).append(case)

    chains: list[dict[str, Any]] = []
    chain_type_counts: Counter[str] = Counter()
    mutated_feature_counts: Counter[str] = Counter()

    for base_case_id in sorted(base_cases):
        base_case = base_cases[base_case_id]
        switch_case = _representative_case(supported_switches.get(base_case_id, []))
        unsupported_case = _representative_case(unsupported_cases.get(base_case_id, []))

        if unsupported_case is not None:
            chains.append(
                _build_chain(
                    chain_id=f"{unsupported_case['case_id']}:fail_closed_recovery",
                    chain_type="supported_fail_closed_recovery",
                    base_case=base_case,
                    switch_case=None,
                    unsupported_case=unsupported_case,
                    counterfactual_payload=counterfactual_payload,
                    steps=[base_case, unsupported_case, base_case],
                )
            )
            chain_type_counts["supported_fail_closed_recovery"] += 1
            mutated_feature_counts[unsupported_case["mutated_feature"]] += 1

        if switch_case is not None and unsupported_case is not None:
            chains.append(
                _build_chain(
                    chain_id=f"{base_case_id}:{switch_case['mutated_feature']}:{unsupported_case['mutated_feature']}:switch_fail_closed",
                    chain_type="supported_switch_fail_closed",
                    base_case=base_case,
                    switch_case=switch_case,
                    unsupported_case=unsupported_case,
                    counterfactual_payload=counterfactual_payload,
                    steps=[base_case, switch_case, unsupported_case],
                )
            )
            chains.append(
                _build_chain(
                    chain_id=f"{base_case_id}:{unsupported_case['mutated_feature']}:{switch_case['mutated_feature']}:recovery_switch",
                    chain_type="fail_closed_recovery_switch",
                    base_case=base_case,
                    switch_case=switch_case,
                    unsupported_case=unsupported_case,
                    counterfactual_payload=counterfactual_payload,
                    steps=[unsupported_case, base_case, switch_case],
                )
            )
            chain_type_counts["supported_switch_fail_closed"] += 1
            chain_type_counts["fail_closed_recovery_switch"] += 1
            mutated_feature_counts[switch_case["mutated_feature"]] += 2
            mutated_feature_counts[unsupported_case["mutated_feature"]] += 2

    # --- 5-step chains ---
    for base_case_id in sorted(base_cases):
        base_case = base_cases[base_case_id]
        switch_list = supported_switches.get(base_case_id, [])
        unsupported_list = unsupported_cases.get(base_case_id, [])

        if not switch_list or not unsupported_list:
            continue

        switch_case = _representative_case(switch_list)
        unsupported_case = _representative_case(unsupported_list)
        if switch_case is None or unsupported_case is None:
            continue

        # full_degradation_recovery_switch_stabilize:
        #   base -> unsupported -> base (recovery) -> switch -> base (stabilize)
        chains.append(
            _build_chain(
                chain_id=(
                    f"{base_case_id}:{unsupported_case['mutated_feature']}:"
                    f"{switch_case['mutated_feature']}:full_degradation"
                ),
                chain_type="full_degradation_recovery_switch_stabilize",
                base_case=base_case,
                switch_case=switch_case,
                unsupported_case=unsupported_case,
                counterfactual_payload=counterfactual_payload,
                steps=[base_case, unsupported_case, base_case, switch_case, base_case],
            )
        )
        chain_type_counts["full_degradation_recovery_switch_stabilize"] += 1
        mutated_feature_counts[unsupported_case["mutated_feature"]] += 1
        mutated_feature_counts[switch_case["mutated_feature"]] += 1

        # cascading_fail_progressive_recovery:
        #   base -> switch -> unsupported -> base (recovery) -> switch (back to B)
        chains.append(
            _build_chain(
                chain_id=(
                    f"{base_case_id}:{switch_case['mutated_feature']}:"
                    f"{unsupported_case['mutated_feature']}:cascading_fail"
                ),
                chain_type="cascading_fail_progressive_recovery",
                base_case=base_case,
                switch_case=switch_case,
                unsupported_case=unsupported_case,
                counterfactual_payload=counterfactual_payload,
                steps=[base_case, switch_case, unsupported_case, base_case, switch_case],
            )
        )
        chain_type_counts["cascading_fail_progressive_recovery"] += 1
        mutated_feature_counts[switch_case["mutated_feature"]] += 2
        mutated_feature_counts[unsupported_case["mutated_feature"]] += 1

    return {
        "domain": domain,
        "source_supported_case_count": len(base_cases),
        "source_counterfactual_case_count": counterfactual_payload["generated_case_count"],
        "chain_count": len(chains),
        "chain_type_counts": {
            chain_type: chain_type_counts.get(chain_type, 0)
            for chain_type in CHAIN_TYPE_ORDER
        },
        "mutated_feature_counts": dict(sorted(mutated_feature_counts.items())),
        "counterfactual_case_pack_path": counterfactual_payload["case_pack_path"],
        "counterfactual_case_pack_signature": counterfactual_payload["case_pack_signature"],
        "counterfactual_case_pack_source": counterfactual_payload["case_pack_source"],
        "chains": chains,
    }


def run_coordination_chain_benchmark(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_COORDINATION_THRESHOLD,
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
    chains_payload: dict[str, Any] = {}

    hybrid_wins = 0
    hybrid_ties = 0
    hybrid_losses = 0

    for domain in active_domains:
        chain_pack = generate_coordination_chain_sequences(
            repo_root=repo_root,
            domain=domain,
            artifact_dir=results_dir,
            refresh_counterfactual_cases=refresh_counterfactual_cases,
        )
        chains = chain_pack["chains"]
        chains_payload[domain] = chains
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
            chain_results: list[dict[str, Any]] = []
            for chain in chains:
                step_results: list[dict[str, Any]] = []
                for step_index, case in enumerate(chain["steps"], start=1):
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
                    case_result["chain_id"] = chain["chain_id"]
                    case_result["chain_type"] = chain["chain_type"]
                    step_case_results.append(case_result)
                    step_results.append(case_result)
                chain_results.append(_evaluate_chain(chain, step_results))

            strategy_payloads[strategy] = {
                "chain_count": len(chain_results),
                "step_case_count": len(step_case_results),
                "metrics": compute_metrics(step_case_results),
                "regret": compute_regret_metrics(step_case_results),
                "chain_metrics": compute_coordination_chain_metrics(chain_results),
            }

        best_non_hybrid_strategy = _best_non_hybrid_strategy(strategy_payloads)
        hybrid_payload = strategy_payloads["hybrid"]
        baseline_payload = strategy_payloads[best_non_hybrid_strategy]
        hybrid_chain_regret = hybrid_payload["chain_metrics"]["mean_chain_regret"]
        baseline_chain_regret = baseline_payload["chain_metrics"]["mean_chain_regret"]
        if hybrid_chain_regret < baseline_chain_regret:
            hybrid_wins += 1
        elif hybrid_chain_regret > baseline_chain_regret:
            hybrid_losses += 1
        else:
            hybrid_ties += 1

        payload["domains"][domain] = {
            **{key: value for key, value in chain_pack.items() if key != "chains"},
            "strategies": strategy_payloads,
            "comparison": {
                "best_non_hybrid_strategy": best_non_hybrid_strategy,
                "hybrid_chain_regret_gain": baseline_chain_regret - hybrid_chain_regret,
                "hybrid_chain_cost_reduction": (
                    baseline_payload["chain_metrics"]["mean_chain_cost"]
                    - hybrid_payload["chain_metrics"]["mean_chain_cost"]
                ),
                "hybrid_chain_success_gain": (
                    hybrid_payload["chain_metrics"]["all_steps_success_rate"]
                    - baseline_payload["chain_metrics"]["all_steps_success_rate"]
                ),
                "hybrid_recovery_chain_success_gain": (
                    hybrid_payload["chain_metrics"]["fail_closed_recovery_success_rate"]
                    - baseline_payload["chain_metrics"]["fail_closed_recovery_success_rate"]
                ),
            },
        }

    payload["summary"] = {
        "domain_count": len(active_domains),
        "hybrid_win_count": hybrid_wins,
        "hybrid_tie_count": hybrid_ties,
        "hybrid_loss_count": hybrid_losses,
    }
    report_paths = write_coordination_chain_reports(payload, chains_payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    payload["chains_json"] = str(report_paths["chains"])
    return payload


def compute_coordination_chain_metrics(chain_results: list[dict[str, Any]]) -> dict[str, float]:
    def rate(items: list[dict[str, Any]], pred) -> float:
        if not items:
            return 0.0
        return sum(1 for item in items if pred(item)) / len(items)

    def mean(items: list[dict[str, Any]], key: str) -> float:
        if not items:
            return 0.0
        return sum(float(item[key]) for item in items) / len(items)

    def subset(chain_type: str) -> list[dict[str, Any]]:
        return [item for item in chain_results if item["chain_type"] == chain_type]

    recovery_chains = subset("supported_fail_closed_recovery")
    switch_fail_closed_chains = subset("supported_switch_fail_closed")
    recovery_switch_chains = subset("fail_closed_recovery_switch")
    full_degradation_chains = subset("full_degradation_recovery_switch_stabilize")
    cascading_fail_chains = subset("cascading_fail_progressive_recovery")

    return {
        "mean_chain_regret": mean(chain_results, "chain_regret"),
        "mean_chain_cost": mean(chain_results, "chain_cost"),
        "all_steps_success_rate": rate(chain_results, lambda item: bool(item["all_steps_success"])),
        "any_fallback_rate": rate(chain_results, lambda item: bool(item["any_fallback_used"])),
        "any_invalid_output_rate": rate(chain_results, lambda item: bool(item["any_invalid_output"])),
        "fail_closed_recovery_success_rate": rate(recovery_chains, lambda item: bool(item["chain_success"])),
        "switch_fail_closed_success_rate": rate(switch_fail_closed_chains, lambda item: bool(item["chain_success"])),
        "recovery_switch_success_rate": rate(recovery_switch_chains, lambda item: bool(item["chain_success"])),
        "full_degradation_recovery_switch_stabilize_success_rate": rate(
            full_degradation_chains, lambda item: bool(item["chain_success"])
        ),
        "cascading_fail_progressive_recovery_success_rate": rate(
            cascading_fail_chains, lambda item: bool(item["chain_success"])
        ),
    }


def render_coordination_chain_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Coordination Chain Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "This benchmark composes the cached counterfactual packs into deterministic three-step and "
            "five-step chains that stress fail-closed behavior, recovery, and action switching in one "
            "sequence rather than in isolated adjacent transitions."
        ),
        "",
        (
            f"Hybrid comparison summary: wins={payload['summary']['hybrid_win_count']}, "
            f"ties={payload['summary']['hybrid_tie_count']}, "
            f"losses={payload['summary']['hybrid_loss_count']}."
        ),
        "",
        "| Domain | Chains | Fail->Recover | Switch->Fail | Recover->Switch | Full Degrade | Cascading Fail | Hybrid Success | Hybrid Chain Regret | Best Non-Hybrid | Baseline Chain Regret | Gain |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]

    for domain, domain_payload in payload["domains"].items():
        hybrid = domain_payload["strategies"]["hybrid"]
        baseline_name = domain_payload["comparison"]["best_non_hybrid_strategy"]
        baseline = domain_payload["strategies"][baseline_name]
        lines.append(
            "| "
            f"{domain} | "
            f"{domain_payload['chain_count']} | "
            f"{domain_payload['chain_type_counts']['supported_fail_closed_recovery']} | "
            f"{domain_payload['chain_type_counts']['supported_switch_fail_closed']} | "
            f"{domain_payload['chain_type_counts']['fail_closed_recovery_switch']} | "
            f"{domain_payload['chain_type_counts']['full_degradation_recovery_switch_stabilize']} | "
            f"{domain_payload['chain_type_counts']['cascading_fail_progressive_recovery']} | "
            f"{hybrid['chain_metrics']['all_steps_success_rate']:.4f} | "
            f"{hybrid['chain_metrics']['mean_chain_regret']:.4f} | "
            f"{baseline_name} | "
            f"{baseline['chain_metrics']['mean_chain_regret']:.4f} | "
            f"{domain_payload['comparison']['hybrid_chain_regret_gain']:.4f} |"
        )
        lines.append(
            f"Chains `{domain}`: "
            + ", ".join(
                f"{chain_type}={count}"
                for chain_type, count in domain_payload["chain_type_counts"].items()
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


def write_coordination_chain_reports(
    payload: dict[str, Any],
    chains_payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / DEFAULT_REPORT_JSON
    report_md = output_dir / DEFAULT_REPORT_MD
    chains_json = output_dir / DEFAULT_CHAINS_JSON
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_coordination_chain_markdown(payload), encoding="utf-8")
    chains_json.write_text(json.dumps(chains_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"json": report_json, "md": report_md, "chains": chains_json}


def _build_chain(
    *,
    chain_id: str,
    chain_type: str,
    base_case: dict[str, Any],
    switch_case: dict[str, Any] | None,
    unsupported_case: dict[str, Any] | None,
    counterfactual_payload: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "chain_id": chain_id,
        "chain_type": chain_type,
        "base_case_id": base_case["case_id"],
        "switch_case_id": switch_case["case_id"] if switch_case is not None else None,
        "unsupported_case_id": unsupported_case["case_id"] if unsupported_case is not None else None,
        "switch_mutated_feature": switch_case["mutated_feature"] if switch_case is not None else None,
        "unsupported_mutated_feature": unsupported_case["mutated_feature"] if unsupported_case is not None else None,
        "counterfactual_case_pack_path": counterfactual_payload["case_pack_path"],
        "counterfactual_case_pack_signature": counterfactual_payload["case_pack_signature"],
        "steps": [dict(step) for step in steps],
    }


def _evaluate_chain(chain: dict[str, Any], step_results: list[dict[str, Any]]) -> dict[str, Any]:
    chain_type = chain["chain_type"]
    all_steps_success = all(_step_success(step_result) for step_result in step_results)

    # 3-step chains
    if chain_type in (
        "supported_fail_closed_recovery",
        "supported_switch_fail_closed",
        "fail_closed_recovery_switch",
    ):
        if len(step_results) != 3:
            raise ValueError(
                f"coordination chain type {chain_type!r} expects exactly 3 steps, got {len(step_results)}"
            )
        if chain_type == "supported_fail_closed_recovery":
            chain_success = (
                bool(step_results[0].get("correct", False))
                and _is_safe_reject(step_results[1])
                and bool(step_results[2].get("correct", False))
            )
        elif chain_type == "supported_switch_fail_closed":
            chain_success = (
                bool(step_results[0].get("correct", False))
                and bool(step_results[1].get("correct", False))
                and step_results[0].get("selected_action_id") != step_results[1].get("selected_action_id")
                and _is_safe_reject(step_results[2])
            )
        else:  # fail_closed_recovery_switch
            chain_success = (
                _is_safe_reject(step_results[0])
                and bool(step_results[1].get("correct", False))
                and bool(step_results[2].get("correct", False))
                and step_results[1].get("selected_action_id") != step_results[2].get("selected_action_id")
            )

    # 5-step chains
    elif chain_type in (
        "full_degradation_recovery_switch_stabilize",
        "cascading_fail_progressive_recovery",
    ):
        if len(step_results) != 5:
            raise ValueError(
                f"coordination chain type {chain_type!r} expects exactly 5 steps, got {len(step_results)}"
            )
        if chain_type == "full_degradation_recovery_switch_stabilize":
            chain_success = (
                bool(step_results[0].get("correct", False))           # base correct
                and _is_safe_reject(step_results[1])                   # fail closed
                and bool(step_results[2].get("correct", False))        # recovery correct
                and bool(step_results[3].get("correct", False))        # switch correct
                and step_results[0].get("selected_action_id")
                != step_results[3].get("selected_action_id")           # different actions
                and bool(step_results[4].get("correct", False))        # stabilize correct
            )
        else:  # cascading_fail_progressive_recovery
            chain_success = (
                bool(step_results[0].get("correct", False))           # base correct
                and bool(step_results[1].get("correct", False))        # switch correct
                and step_results[0].get("selected_action_id")
                != step_results[1].get("selected_action_id")           # different actions
                and _is_safe_reject(step_results[2])                   # fail closed
                and bool(step_results[3].get("correct", False))        # recovery correct
                and bool(step_results[4].get("correct", False))        # switch back correct
            )

    else:
        raise ValueError(f"unsupported coordination chain type: {chain_type}")

    return {
        "chain_id": chain["chain_id"],
        "chain_type": chain_type,
        "chain_regret": sum(_regret_score(step_result) for step_result in step_results),
        "chain_cost": sum(_decision_cost(step_result) for step_result in step_results),
        "all_steps_success": all_steps_success,
        "chain_success": chain_success,
        "any_fallback_used": any(bool(step_result.get("fallback_used", False)) for step_result in step_results),
        "any_invalid_output": any(not bool(step_result.get("valid", False)) for step_result in step_results),
    }


def _step_success(step_result: dict[str, Any]) -> bool:
    if bool(step_result.get("supported", True)):
        return bool(step_result.get("correct", False))
    return _is_safe_reject(step_result)


def _decision_cost(case_result: dict[str, Any]) -> float:
    return _outcome_score(case_result, DEFAULT_DECISION_COSTS)


def _regret_score(case_result: dict[str, Any]) -> float:
    return _outcome_score(case_result, DEFAULT_REGRET_COSTS)


def _best_non_hybrid_strategy(strategy_payloads: dict[str, dict[str, Any]]) -> str:
    non_hybrid = {
        strategy: payload
        for strategy, payload in strategy_payloads.items()
        if strategy != "hybrid"
    }
    if not non_hybrid:
        raise ValueError("coordination benchmark requires at least one non-hybrid strategy")
    return min(
        non_hybrid,
        key=lambda strategy: (
            non_hybrid[strategy]["chain_metrics"]["mean_chain_regret"],
            non_hybrid[strategy]["chain_metrics"]["mean_chain_cost"],
            -non_hybrid[strategy]["chain_metrics"]["all_steps_success_rate"],
        ),
    )


def _representative_case(cases: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not cases:
        return None
    return min(
        cases,
        key=lambda case: (
            case["mutated_feature"],
            case["case_id"],
        ),
    )
