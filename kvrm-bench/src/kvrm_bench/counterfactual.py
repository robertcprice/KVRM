from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.context_schema import evaluate_registry_context
from kvrm_core.registry import load_registry
from kvrm_core.types import DecisionCandidate, DecisionInput
from kvrm_core.validation import DeterministicValidator

from .demo import DOMAIN_CONFIG, STRATEGY_ORDER, _cached_runtime_for_strategy, load_cases
from .metrics import compute_metrics, compute_regret_metrics
from .utils import value_token as _value_token

DEFAULT_COUNTERFACTUAL_THRESHOLD = 0.60
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_CASE_PACK_DIR_NAME = "counterfactual_boundary_case_cache"
DEFAULT_REPORT_JSON = "counterfactual_boundary_report.json"
DEFAULT_REPORT_MD = "counterfactual_boundary_report.md"
DEFAULT_CASES_JSON = "counterfactual_boundary_cases.json"
COUNTERFACTUAL_CASE_PACK_VERSION = "2026-04-09"


def generate_boundary_counterfactual_cases(
    *,
    repo_root: str | Path,
    domain: str,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported counterfactual domain: {domain}")

    data_dir = repo_root / DOMAIN_CONFIG[domain]["data_dir"]
    registry = load_registry(data_dir / "registry.json")
    validator = DeterministicValidator(registry)
    base_cases = [case for case in load_cases(data_dir / "cases.jsonl") if case.get("supported", True)]
    boundary_values = _collect_feature_boundary_values(registry)
    fallback_action_ids = {action.action_id for action in registry.actions if "fallback" in action.tags}

    generated_cases: list[dict[str, Any]] = []
    feature_counts: Counter[str] = Counter()
    expected_action_counts: Counter[str] = Counter()
    seen_feature_payloads: set[str] = set()

    for base_case in base_cases:
        base_features = base_case["input_features"]
        for feature_name in registry.context_schema:
            if feature_name not in base_features:
                continue
            current_value = base_features[feature_name]
            for candidate_value in _candidate_values_for_feature(
                feature_name=feature_name,
                field_spec=registry.context_schema[feature_name],
                boundary_values=boundary_values,
            ):
                if candidate_value == current_value:
                    continue
                mutated_features = dict(base_features)
                mutated_features[feature_name] = candidate_value
                context_valid, _ = evaluate_registry_context(registry, mutated_features)
                if not context_valid:
                    continue
                supported_actions = _supported_non_fallback_actions(
                    registry=registry,
                    validator=validator,
                    fallback_action_ids=fallback_action_ids,
                    features=mutated_features,
                )
                if len(supported_actions) > 1:
                    continue

                supported = len(supported_actions) == 1
                expected_action_id = supported_actions[0] if supported_actions else None
                if supported and expected_action_id == base_case.get("expected_action_id"):
                    continue

                dedupe_key = json.dumps(mutated_features, sort_keys=True)
                if dedupe_key in seen_feature_payloads:
                    continue
                seen_feature_payloads.add(dedupe_key)

                generated_case = {
                    "case_id": f"{base_case['case_id']}:{feature_name}:{_value_token(candidate_value)}",
                    "base_case_id": base_case["case_id"],
                    "mutated_feature": feature_name,
                    "from_value": current_value,
                    "to_value": candidate_value,
                    "expected_action_id": expected_action_id,
                    "input_features": mutated_features,
                    "supported": supported,
                    "ood": True,
                    "mutation_type": "single_feature_boundary_counterfactual",
                }
                generated_cases.append(generated_case)
                feature_counts[feature_name] += 1
                expected_action_counts[expected_action_id or "__unsupported__"] += 1

    generated_cases.sort(
        key=lambda case: (
            case["base_case_id"],
            case["mutated_feature"],
            case["case_id"],
        )
    )
    supported_case_count = sum(1 for case in generated_cases if case["supported"])
    unsupported_case_count = len(generated_cases) - supported_case_count
    return {
        "domain": domain,
        "source_supported_case_count": len(base_cases),
        "generated_case_count": len(generated_cases),
        "supported_case_count": supported_case_count,
        "unsupported_case_count": unsupported_case_count,
        "feature_counts": dict(sorted(feature_counts.items())),
        "expected_action_counts": dict(sorted(expected_action_counts.items())),
        "cases": generated_cases,
    }


def load_or_generate_boundary_counterfactual_cases(
    *,
    repo_root: str | Path,
    domain: str,
    artifact_dir: str | Path | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    case_pack_path, case_pack_signature, source_metadata = _build_case_pack_metadata(
        repo_root=repo_root,
        domain=domain,
        artifact_dir=artifact_dir,
    )

    if not refresh:
        cached_payload = _load_cached_case_pack(
            case_pack_path=case_pack_path,
            expected_signature=case_pack_signature,
        )
        if cached_payload is not None:
            return {
                **_extract_case_pack_payload(cached_payload),
                **source_metadata,
                "case_pack_source": "cache",
                "case_pack_path": str(case_pack_path),
                "case_pack_signature": case_pack_signature,
                "case_pack_generated_at": cached_payload.get("case_pack_generated_at"),
            }

    generated_payload = generate_boundary_counterfactual_cases(
        repo_root=repo_root,
        domain=domain,
    )
    case_pack_path.parent.mkdir(parents=True, exist_ok=True)
    case_pack_generated_at = datetime.now(timezone.utc).isoformat()
    cache_payload = {
        **source_metadata,
        **generated_payload,
        "case_pack_generated_at": case_pack_generated_at,
    }
    case_pack_path.write_text(
        json.dumps(cache_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        **generated_payload,
        **source_metadata,
        "case_pack_source": "generated",
        "case_pack_path": str(case_pack_path),
        "case_pack_signature": case_pack_signature,
        "case_pack_generated_at": case_pack_generated_at,
    }


def run_counterfactual_boundary_benchmark(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_COUNTERFACTUAL_THRESHOLD,
    learned_model_paths: dict[str, str | Path] | None = None,
    output_dir: str | Path | None = None,
    refresh_case_cache: bool = False,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    active_domains = list(domains or DOMAIN_CONFIG.keys())
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)
    case_pack_dir = results_dir / DEFAULT_CASE_PACK_DIR_NAME

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "case_pack_dir": str(case_pack_dir),
        "domains": {},
        "summary": {},
    }
    cases_payload: dict[str, Any] = {}

    hybrid_wins = 0
    hybrid_ties = 0
    hybrid_losses = 0

    for domain in active_domains:
        generated = load_or_generate_boundary_counterfactual_cases(
            repo_root=repo_root,
            domain=domain,
            artifact_dir=case_pack_dir,
            refresh=refresh_case_cache,
        )
        cases = generated["cases"]
        cases_payload[domain] = cases
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

            case_results: list[dict[str, Any]] = []
            for case in cases:
                decision = runtime.decide_and_execute(
                    DecisionInput(
                        case_id=case["case_id"],
                        features=case["input_features"],
                        supported=case.get("supported", True),
                        ood=case.get("ood", False),
                        expected_action_id=case.get("expected_action_id"),
                    )
                )
                case_results.append(_decision_to_case_result(case, decision.model_dump(mode="json")))

            strategy_payloads[strategy] = {
                "case_count": len(case_results),
                "metrics": compute_metrics(case_results),
                "regret": compute_regret_metrics(case_results),
            }

        best_non_hybrid_strategy = _best_non_hybrid_strategy(strategy_payloads)
        hybrid_payload = strategy_payloads["hybrid"]
        baseline_payload = strategy_payloads[best_non_hybrid_strategy]
        hybrid_regret = hybrid_payload["regret"]["mean_decision_regret"]
        baseline_regret = baseline_payload["regret"]["mean_decision_regret"]
        if hybrid_regret < baseline_regret:
            hybrid_wins += 1
        elif hybrid_regret > baseline_regret:
            hybrid_losses += 1
        else:
            hybrid_ties += 1

        payload["domains"][domain] = {
            **{key: value for key, value in generated.items() if key != "cases"},
            "strategies": strategy_payloads,
            "comparison": {
                "best_non_hybrid_strategy": best_non_hybrid_strategy,
                "hybrid_regret_gain": baseline_regret - hybrid_regret,
                "hybrid_cost_reduction": baseline_payload["metrics"]["mean_decision_cost"] - hybrid_payload["metrics"]["mean_decision_cost"],
                "hybrid_correctness_gain": hybrid_payload["metrics"]["semantic_correctness_rate"] - baseline_payload["metrics"]["semantic_correctness_rate"],
                "hybrid_false_accept_reduction": baseline_payload["metrics"]["false_accept_rate"] - hybrid_payload["metrics"]["false_accept_rate"],
                "hybrid_supported_abstention_reduction": baseline_payload["regret"]["supported_abstention_regret_rate"] - hybrid_payload["regret"]["supported_abstention_regret_rate"],
            },
        }

    payload["summary"] = {
        "domain_count": len(active_domains),
        "hybrid_win_count": hybrid_wins,
        "hybrid_tie_count": hybrid_ties,
        "hybrid_loss_count": hybrid_losses,
    }
    report_paths = write_counterfactual_boundary_reports(payload, cases_payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    payload["cases_json"] = str(report_paths["cases"])
    return payload


def render_counterfactual_boundary_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Counterfactual Boundary Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "This benchmark mutates one feature at a time from supported canonical cases, keeping only "
            "schema-valid counterfactuals that the registry maps to either exactly one supported "
            "non-fallback action or to safe rejection."
        ),
        "",
        (
            "Candidate mutation values are derived from the live registry context schema and support-spec "
            "boundary values, so the slice stays architecture-native instead of relying on synthetic text prompts."
        ),
        "",
        (
            "Generated case packs are cached under `counterfactual_boundary_case_cache/` and reused until "
            "the live registry, canonical eval pack, or case-pack version changes."
        ),
        "",
        (
            f"Hybrid comparison summary: wins={payload['summary']['hybrid_win_count']}, "
            f"ties={payload['summary']['hybrid_tie_count']}, "
            f"losses={payload['summary']['hybrid_loss_count']}."
        ),
        "",
        "| Domain | Cases | Supported | Unsupported | Hybrid Correctness | Hybrid Cost | Hybrid Regret | Best Non-Hybrid | Baseline Correctness | Baseline Regret | Gain |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]

    for domain, domain_payload in payload["domains"].items():
        hybrid = domain_payload["strategies"]["hybrid"]
        baseline_name = domain_payload["comparison"]["best_non_hybrid_strategy"]
        baseline = domain_payload["strategies"][baseline_name]
        lines.append(
            "| "
            f"{domain} | "
            f"{domain_payload['generated_case_count']} | "
            f"{domain_payload['supported_case_count']} | "
            f"{domain_payload['unsupported_case_count']} | "
            f"{hybrid['metrics']['semantic_correctness_rate']:.4f} | "
            f"{hybrid['metrics']['mean_decision_cost']:.4f} | "
            f"{hybrid['regret']['mean_decision_regret']:.4f} | "
            f"{baseline_name} | "
            f"{baseline['metrics']['semantic_correctness_rate']:.4f} | "
            f"{baseline['regret']['mean_decision_regret']:.4f} | "
            f"{domain_payload['comparison']['hybrid_regret_gain']:.4f} |"
        )
        lines.append(
            f"Features `{domain}`: "
            + ", ".join(
                f"{feature}={count}"
                for feature, count in domain_payload["feature_counts"].items()
            )
        )
        lines.append(
            f"Expected `{domain}`: "
            + ", ".join(
                f"{name}={count}"
                for name, count in domain_payload["expected_action_counts"].items()
            )
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_counterfactual_boundary_reports(
    payload: dict[str, Any],
    cases_payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / DEFAULT_REPORT_JSON
    report_md = output_dir / DEFAULT_REPORT_MD
    cases_json = output_dir / DEFAULT_CASES_JSON
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_counterfactual_boundary_markdown(payload), encoding="utf-8")
    cases_json.write_text(json.dumps(cases_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"json": report_json, "md": report_md, "cases": cases_json}


def _build_case_pack_metadata(
    *,
    repo_root: Path,
    domain: str,
    artifact_dir: str | Path | None,
) -> tuple[Path, str, dict[str, Any]]:
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported counterfactual domain: {domain}")

    artifact_root = (
        repo_root / DEFAULT_RESULTS_DIR / DEFAULT_CASE_PACK_DIR_NAME
        if artifact_dir is None
        else Path(artifact_dir)
    )
    data_dir = repo_root / DOMAIN_CONFIG[domain]["data_dir"]
    registry_path = data_dir / "registry.json"
    cases_path = data_dir / "cases.jsonl"
    source_registry_digest = _sha256_file(registry_path)
    source_eval_cases_digest = _sha256_file(cases_path)
    signature_payload = json.dumps(
        {
            "case_pack_version": COUNTERFACTUAL_CASE_PACK_VERSION,
            "domain": domain,
            "source_registry_digest": source_registry_digest,
            "source_eval_cases_digest": source_eval_cases_digest,
        },
        sort_keys=True,
    )
    case_pack_signature = hashlib.sha256(signature_payload.encode("utf-8")).hexdigest()
    metadata = {
        "case_pack_version": COUNTERFACTUAL_CASE_PACK_VERSION,
        "source_registry_digest": source_registry_digest,
        "source_eval_cases_digest": source_eval_cases_digest,
    }
    return (artifact_root / f"{domain}.json", case_pack_signature, metadata)


def _load_cached_case_pack(
    *,
    case_pack_path: Path,
    expected_signature: str,
) -> dict[str, Any] | None:
    if not case_pack_path.exists():
        return None
    try:
        payload = json.loads(case_pack_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("case_pack_version") != COUNTERFACTUAL_CASE_PACK_VERSION:
        return None
    signature_payload = json.dumps(
        {
            "case_pack_version": payload.get("case_pack_version"),
            "domain": payload.get("domain"),
            "source_registry_digest": payload.get("source_registry_digest"),
            "source_eval_cases_digest": payload.get("source_eval_cases_digest"),
        },
        sort_keys=True,
    )
    actual_signature = hashlib.sha256(signature_payload.encode("utf-8")).hexdigest()
    if actual_signature != expected_signature:
        return None
    return payload


def _extract_case_pack_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "domain": payload["domain"],
        "source_supported_case_count": payload["source_supported_case_count"],
        "generated_case_count": payload["generated_case_count"],
        "supported_case_count": payload["supported_case_count"],
        "unsupported_case_count": payload["unsupported_case_count"],
        "feature_counts": payload["feature_counts"],
        "expected_action_counts": payload["expected_action_counts"],
        "cases": payload["cases"],
    }


def _candidate_values_for_feature(
    *,
    feature_name: str,
    field_spec: dict[str, Any],
    boundary_values: dict[str, set[Any]],
) -> list[Any]:
    values = set(boundary_values.get(feature_name, set()))
    field_type = field_spec.get("type")
    if "enum" in field_spec:
        values.update(field_spec["enum"])
    elif field_type == "boolean":
        values.update({True, False})
    elif field_type == "integer":
        minimum = field_spec.get("minimum")
        maximum = field_spec.get("maximum")
        if minimum is not None:
            values.add(minimum)
        if maximum is not None:
            values.add(maximum)
        if minimum is not None and maximum is not None:
            values.add(int((minimum + maximum) // 2))
    elif field_type == "number":
        minimum = field_spec.get("minimum")
        maximum = field_spec.get("maximum")
        if minimum is not None:
            values.add(float(minimum))
        if maximum is not None:
            values.add(float(maximum))
        if minimum is not None and maximum is not None:
            values.add(round((float(minimum) + float(maximum)) / 2.0, 6))
    return sorted(values, key=_sort_key)


def _collect_feature_boundary_values(registry) -> dict[str, set[Any]]:
    values: dict[str, set[Any]] = defaultdict(set)
    for action in registry.actions:
        _collect_support_spec_values(
            spec=action.support_spec,
            schema=registry.context_schema,
            values=values,
        )
    return values


def _collect_support_spec_values(
    *,
    spec: dict[str, Any] | None,
    schema: dict[str, dict[str, Any]],
    values: dict[str, set[Any]],
) -> None:
    if not spec:
        return
    if "feature" in spec:
        feature_name = spec["feature"]
        field_spec = schema.get(feature_name, {})
        op = spec.get("op")
        raw_value = spec.get("value")
        if op in {"eq", "neq", "gt", "gte", "lt", "lte"} and raw_value is not None:
            values[feature_name].add(raw_value)
            values[feature_name].update(_numeric_neighbors(raw_value, field_spec))
        elif op in {"in", "not_in"} and isinstance(raw_value, list):
            for item in raw_value:
                values[feature_name].add(item)
                values[feature_name].update(_numeric_neighbors(item, field_spec))
        return
    if "all" in spec:
        for child in spec["all"]:
            _collect_support_spec_values(spec=child, schema=schema, values=values)
        return
    if "any" in spec:
        for child in spec["any"]:
            _collect_support_spec_values(spec=child, schema=schema, values=values)
        return
    if "not" in spec:
        _collect_support_spec_values(spec=spec["not"], schema=schema, values=values)


def _numeric_neighbors(value: Any, field_spec: dict[str, Any]) -> set[Any]:
    if isinstance(value, bool):
        return set()
    field_type = field_spec.get("type")
    minimum = field_spec.get("minimum")
    maximum = field_spec.get("maximum")
    neighbors: set[Any] = set()
    if field_type == "integer" and type(value) is int:
        for candidate in (value - 1, value + 1):
            if minimum is not None and candidate < minimum:
                continue
            if maximum is not None and candidate > maximum:
                continue
            neighbors.add(candidate)
    elif field_type == "number" and isinstance(value, (int, float)):
        if minimum is not None and maximum is not None and float(maximum) > float(minimum):
            delta = max(0.01, (float(maximum) - float(minimum)) / 20.0)
        else:
            delta = 0.05
        for candidate in (float(value) - delta, float(value) + delta):
            if minimum is not None and candidate < float(minimum):
                continue
            if maximum is not None and candidate > float(maximum):
                continue
            neighbors.add(round(candidate, 6))
    return neighbors


def _supported_non_fallback_actions(
    *,
    registry,
    validator: DeterministicValidator,
    fallback_action_ids: set[str],
    features: dict[str, Any],
) -> list[str]:
    supported_actions: list[str] = []
    for action in registry.actions:
        if action.action_id in fallback_action_ids:
            continue
        valid = validator.validate(
            DecisionCandidate(action_id=action.action_id, confidence=1.0),
            features,
        ).valid
        if valid:
            supported_actions.append(action.action_id)
    return supported_actions


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
        raise ValueError("counterfactual benchmark requires at least one non-hybrid strategy")
    return min(
        non_hybrid,
        key=lambda strategy: (
            non_hybrid[strategy]["regret"]["mean_decision_regret"],
            non_hybrid[strategy]["metrics"]["mean_decision_cost"],
            -non_hybrid[strategy]["metrics"]["semantic_correctness_rate"],
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


def _sort_key(value: Any) -> tuple[int, Any]:
    if isinstance(value, bool):
        return (0, int(value))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (1, float(value))
    return (2, str(value))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
