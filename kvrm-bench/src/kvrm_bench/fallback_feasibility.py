from __future__ import annotations

import importlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.context_schema import evaluate_registry_context
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.support import evaluate_support_spec
from kvrm_core.types import DecisionCandidate, DecisionInput, ValidationResult
from kvrm_core.validation import DeterministicValidator

from .demo import DOMAIN_CONFIG, load_cases
from .metrics import compute_metrics
from .utils import value_token as _value_token

DEFAULT_FALLBACK_FEASIBILITY_THRESHOLD = 0.60
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_REPORT_JSON = "fallback_feasibility_report.json"
DEFAULT_REPORT_MD = "fallback_feasibility_report.md"
DEFAULT_CASES_JSON = "fallback_feasibility_cases.json"
DEFAULT_DOMAINS = ("sre", "drone")
VARIANT_ORDER = ("strict", "legacy_bypass")

FEASIBILITY_MUTATIONS = {
    "sre": {
        "operator_response_eta": ("slow",),
        "mitigation_window_remaining": ("brief",),
    },
    "drone": {
        "pilot_response_eta": ("slow",),
        "takeover_window_remaining": ("brief",),
    },
}


class LegacyFallbackBypassValidator(DeterministicValidator):
    """Reproduces the legacy runtime behavior for publication comparison."""

    def validate(self, candidate: DecisionCandidate, features: dict | None = None) -> ValidationResult:
        if candidate.action_id not in self._actions:
            return ValidationResult(valid=False, reason="unknown_action")
        action = self._actions[candidate.action_id]
        schema = action.parameters_schema or {}
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        for key in required:
            if key not in candidate.parameters:
                return ValidationResult(valid=False, reason=f"missing_required_parameter:{key}")
        for key in candidate.parameters:
            if properties and key not in properties:
                return ValidationResult(valid=False, reason=f"unexpected_parameter:{key}")

        is_runtime_fallback = candidate.source == "fallback" and "fallback" in action.tags
        if features is not None and action.support_spec and not is_runtime_fallback:
            supported, reason = evaluate_support_spec(action.support_spec, features)
            if not supported:
                return ValidationResult(valid=False, reason=f"unsupported_features:{reason}")

        if candidate.action_id in self.preconditions and not self.preconditions[candidate.action_id](candidate.parameters):
            return ValidationResult(valid=False, reason="precondition_failed")
        return ValidationResult(valid=True, reason=None)


def generate_fallback_feasibility_cases(
    *,
    repo_root: str | Path,
    domain: str,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    if domain not in FEASIBILITY_MUTATIONS:
        raise ValueError(f"unsupported fallback-feasibility domain: {domain}")

    config = DOMAIN_CONFIG[domain]
    data_dir = repo_root / config["data_dir"]
    registry = load_registry(data_dir / "registry.json")
    validator = DeterministicValidator(registry)
    fallback_action_id = config["fallback_action_id"]
    fallback_probe = DecisionCandidate(
        action_id=fallback_action_id,
        confidence=1.0,
        parameters={"reason": "fallback_feasibility_probe"},
        source="fallback",
    )
    mutation_values = FEASIBILITY_MUTATIONS[domain]
    canonical_cases = load_cases(data_dir / "cases.jsonl")

    generated_cases: list[dict[str, Any]] = []
    kind_counts: Counter[str] = Counter()
    violation_feature_counts: Counter[str] = Counter()
    seen_signatures: set[str] = set()

    for case in canonical_cases:
        if case.get("supported", True) and case.get("expected_action_id") == fallback_action_id:
            _append_case(
                generated_cases,
                kind_counts,
                violation_feature_counts,
                seen_signatures,
                {
                    **case,
                    "case_kind": "supported_handoff_control",
                    "base_case_id": case["case_id"],
                    "violated_feasibility_features": [],
                    "source": "canonical_supported",
                },
            )

    for case in canonical_cases:
        if case.get("supported", True):
            continue
        features = case["input_features"]
        if not _is_infeasible_handoff_case(
            registry=registry,
            validator=validator,
            fallback_probe=fallback_probe,
            fallback_action_id=fallback_action_id,
            features=features,
            mutation_values=mutation_values,
        ):
            continue
        _append_case(
            generated_cases,
            kind_counts,
            violation_feature_counts,
            seen_signatures,
            {
                **case,
                "case_kind": "canonical_infeasible_handoff",
                "base_case_id": case["case_id"],
                "violated_feasibility_features": _violated_feasibility_features(features, mutation_values),
                "source": "canonical_unsupported",
            },
        )

    supported_controls = [
        case
        for case in generated_cases
        if case["case_kind"] == "supported_handoff_control"
    ]
    for base_case in supported_controls:
        base_features = base_case["input_features"]
        for feature_name, invalid_values in mutation_values.items():
            for invalid_value in invalid_values:
                if base_features.get(feature_name) == invalid_value:
                    continue
                mutated_features = dict(base_features)
                mutated_features[feature_name] = invalid_value
                if not _is_infeasible_handoff_case(
                    registry=registry,
                    validator=validator,
                    fallback_probe=fallback_probe,
                    fallback_action_id=fallback_action_id,
                    features=mutated_features,
                    mutation_values=mutation_values,
                ):
                    continue
                _append_case(
                    generated_cases,
                    kind_counts,
                    violation_feature_counts,
                    seen_signatures,
                    {
                        "case_id": f"{base_case['case_id']}:{feature_name}:{_value_token(invalid_value)}",
                        "base_case_id": base_case["case_id"],
                        "expected_action_id": None,
                        "input_features": mutated_features,
                        "supported": False,
                        "ood": True,
                        "case_kind": "generated_infeasible_handoff",
                        "mutation_type": "single_feature_feasibility_violation",
                        "mutated_feature": feature_name,
                        "from_value": base_features.get(feature_name),
                        "to_value": invalid_value,
                        "violated_feasibility_features": [feature_name],
                        "source": "generated_counterfactual",
                    },
                )

        combined_features = dict(base_features)
        combined_violation_features: list[str] = []
        for feature_name, invalid_values in mutation_values.items():
            invalid_value = invalid_values[0]
            if combined_features.get(feature_name) == invalid_value:
                continue
            combined_features[feature_name] = invalid_value
            combined_violation_features.append(feature_name)
        if combined_violation_features and _is_infeasible_handoff_case(
            registry=registry,
            validator=validator,
            fallback_probe=fallback_probe,
            fallback_action_id=fallback_action_id,
            features=combined_features,
            mutation_values=mutation_values,
        ):
            _append_case(
                generated_cases,
                kind_counts,
                violation_feature_counts,
                seen_signatures,
                {
                    "case_id": f"{base_case['case_id']}:combined_feasibility_violation",
                    "base_case_id": base_case["case_id"],
                    "expected_action_id": None,
                    "input_features": combined_features,
                    "supported": False,
                    "ood": True,
                    "case_kind": "generated_combined_infeasible_handoff",
                    "mutation_type": "combined_feasibility_violation",
                    "violated_feasibility_features": combined_violation_features,
                    "source": "generated_counterfactual",
                },
            )

    generated_cases.sort(
        key=lambda case: (
            case["case_kind"],
            case.get("base_case_id") or case["case_id"],
            case["case_id"],
        )
    )
    supported_case_count = sum(1 for case in generated_cases if case.get("supported", True))
    unsupported_case_count = len(generated_cases) - supported_case_count
    return {
        "domain": domain,
        "fallback_action_id": fallback_action_id,
        "source_case_count": len(canonical_cases),
        "generated_case_count": len(generated_cases),
        "supported_case_count": supported_case_count,
        "unsupported_case_count": unsupported_case_count,
        "case_kind_counts": dict(sorted(kind_counts.items())),
        "violation_feature_counts": dict(sorted(violation_feature_counts.items())),
        "cases": generated_cases,
    }


def build_fallback_feasibility_runtime(
    *,
    repo_root: str | Path,
    domain: str,
    variant: str,
    threshold: float = DEFAULT_FALLBACK_FEASIBILITY_THRESHOLD,
    learned_model_path: str | Path | None = None,
) -> KVRMRuntime:
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported fallback-feasibility domain: {domain}")
    if variant not in VARIANT_ORDER:
        raise ValueError(f"unsupported fallback-feasibility variant: {variant}")

    repo_root = Path(repo_root)
    config = DOMAIN_CONFIG[domain]
    data_dir = repo_root / config["data_dir"]
    registry = load_registry(data_dir / "registry.json")
    train_cases_path = data_dir / "train_cases.jsonl"

    selectors_module = importlib.import_module(config["selectors_module"])
    executor_module = importlib.import_module(config["executor_module"])
    selector = selectors_module.build_hybrid_selector(
        train_cases_path,
        learned_model_path=_resolve_learned_model_path(repo_root, domain, learned_model_path),
    )
    validator = DeterministicValidator(registry) if variant == "strict" else LegacyFallbackBypassValidator(registry)
    return KVRMRuntime(
        registry=registry,
        selector=selector,
        validator=validator,
        executor=executor_module.build_executor(),
        threshold=threshold,
        fallback_action_id=config["fallback_action_id"],
    )


def run_fallback_feasibility_benchmark(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_FALLBACK_FEASIBILITY_THRESHOLD,
    learned_model_paths: dict[str, str | Path] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    active_domains = list(domains or DEFAULT_DOMAINS)
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "domains": {},
        "summary": {},
    }
    cases_payload: dict[str, Any] = {}

    strict_zero_unsafe_execution_domains = 0
    legacy_nonzero_unsafe_execution_domains = 0

    for domain in active_domains:
        generated = generate_fallback_feasibility_cases(repo_root=repo_root, domain=domain)
        cases = generated["cases"]
        cases_payload[domain] = cases
        fallback_action_id = generated["fallback_action_id"]
        variant_payloads: dict[str, dict[str, Any]] = {}
        for variant in VARIANT_ORDER:
            runtime = build_fallback_feasibility_runtime(
                repo_root=repo_root,
                domain=domain,
                variant=variant,
                threshold=threshold,
                learned_model_path=(learned_model_paths or {}).get(domain),
            )
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
            variant_payloads[variant] = {
                "case_count": len(case_results),
                "metrics": compute_metrics(case_results),
                "feasibility_metrics": compute_fallback_feasibility_metrics(
                    case_results,
                    fallback_action_id=fallback_action_id,
                ),
            }

        strict_metrics = variant_payloads["strict"]["feasibility_metrics"]
        legacy_metrics = variant_payloads["legacy_bypass"]["feasibility_metrics"]
        if strict_metrics["unsupported_unsafe_execution_rate"] == 0.0:
            strict_zero_unsafe_execution_domains += 1
        if legacy_metrics["unsupported_unsafe_execution_rate"] > 0.0:
            legacy_nonzero_unsafe_execution_domains += 1

        payload["domains"][domain] = {
            **{key: value for key, value in generated.items() if key != "cases"},
            "variants": variant_payloads,
            "comparison": {
                "supported_handoff_success_delta": (
                    strict_metrics["supported_handoff_success_rate"]
                    - legacy_metrics["supported_handoff_success_rate"]
                ),
                "unsafe_execution_reduction": (
                    legacy_metrics["unsupported_unsafe_execution_rate"]
                    - strict_metrics["unsupported_unsafe_execution_rate"]
                ),
                "infeasible_handoff_execution_reduction": (
                    legacy_metrics["unsupported_infeasible_handoff_execution_rate"]
                    - strict_metrics["unsupported_infeasible_handoff_execution_rate"]
                ),
                "feasibility_cost_reduction": (
                    legacy_metrics["mean_feasibility_cost"]
                    - strict_metrics["mean_feasibility_cost"]
                ),
            },
        }

    payload["summary"] = {
        "domain_count": len(active_domains),
        "strict_zero_unsafe_execution_domains": strict_zero_unsafe_execution_domains,
        "legacy_nonzero_unsafe_execution_domains": legacy_nonzero_unsafe_execution_domains,
    }
    report_paths = write_fallback_feasibility_reports(payload, cases_payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    payload["cases_json"] = str(report_paths["cases"])
    return payload


def compute_fallback_feasibility_metrics(
    case_results: list[dict[str, Any]],
    *,
    fallback_action_id: str,
) -> dict[str, float]:
    supported_cases = [case for case in case_results if case.get("supported", True)]
    unsupported_cases = [case for case in case_results if not case.get("supported", True)]

    def rate(items: list[dict[str, Any]], pred) -> float:
        if not items:
            return 0.0
        return sum(1 for item in items if pred(item)) / len(items)

    def mean_feasibility_cost(items: list[dict[str, Any]]) -> float:
        if not items:
            return 0.0
        return sum(_feasibility_cost(item) for item in items) / len(items)

    return {
        "supported_handoff_success_rate": rate(
            supported_cases,
            lambda item: bool(item.get("correct", False)) and item.get("final_status") == "fallback_executed",
        ),
        "unsupported_safe_rejection_rate": rate(
            unsupported_cases,
            lambda item: item.get("final_status") in {"fail_closed", "abstained", "validation_failed"},
        ),
        "unsupported_unsafe_execution_rate": rate(
            unsupported_cases,
            lambda item: item.get("final_status") in {"executed", "fallback_executed"},
        ),
        "unsupported_infeasible_handoff_execution_rate": rate(
            unsupported_cases,
            lambda item: (
                item.get("selected_action_id") == fallback_action_id
                and item.get("final_status") == "fallback_executed"
            ),
        ),
        "mean_feasibility_cost": mean_feasibility_cost(case_results),
        "supported_mean_feasibility_cost": mean_feasibility_cost(supported_cases),
        "unsupported_mean_feasibility_cost": mean_feasibility_cost(unsupported_cases),
    }


def render_fallback_feasibility_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Fallback-Feasibility Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "This benchmark isolates the latest runtime change: fallback-tagged actions with "
            "their own support envelopes must still satisfy those support specs at execution time."
        ),
        "",
        (
            "Each domain pack contains supported handoff controls, canonical infeasible-handoff "
            "cases already present in the live eval pack, and generated feasibility violations "
            "derived by mutating only the handoff-feasibility features from supported handoff cases."
        ),
        "",
        (
            f"Summary: strict zero unsafe-execution domains={payload['summary']['strict_zero_unsafe_execution_domains']}/"
            f"{payload['summary']['domain_count']}; legacy nonzero unsafe-execution domains="
            f"{payload['summary']['legacy_nonzero_unsafe_execution_domains']}/{payload['summary']['domain_count']}."
        ),
        "",
        "| Domain | Cases | Supported Controls | Unsupported Probes | Strict Support | Legacy Support | Strict Unsafe | Legacy Unsafe | Strict Cost | Legacy Cost |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for domain, domain_payload in payload["domains"].items():
        strict_metrics = domain_payload["variants"]["strict"]["feasibility_metrics"]
        legacy_metrics = domain_payload["variants"]["legacy_bypass"]["feasibility_metrics"]
        lines.append(
            "| "
            f"{domain} | "
            f"{domain_payload['generated_case_count']} | "
            f"{domain_payload['supported_case_count']} | "
            f"{domain_payload['unsupported_case_count']} | "
            f"{strict_metrics['supported_handoff_success_rate']:.4f} | "
            f"{legacy_metrics['supported_handoff_success_rate']:.4f} | "
            f"{strict_metrics['unsupported_unsafe_execution_rate']:.4f} | "
            f"{legacy_metrics['unsupported_unsafe_execution_rate']:.4f} | "
            f"{strict_metrics['mean_feasibility_cost']:.4f} | "
            f"{legacy_metrics['mean_feasibility_cost']:.4f} |"
        )
        lines.append(
            f"Kinds `{domain}`: "
            + ", ".join(
                f"{name}={count}"
                for name, count in domain_payload["case_kind_counts"].items()
            )
        )
        lines.append(
            f"Violations `{domain}`: "
            + ", ".join(
                f"{name}={count}"
                for name, count in domain_payload["violation_feature_counts"].items()
            )
        )
        lines.append(
            f"Delta `{domain}`: "
            f"unsafe_execution_reduction={domain_payload['comparison']['unsafe_execution_reduction']:.4f}, "
            f"infeasible_handoff_execution_reduction={domain_payload['comparison']['infeasible_handoff_execution_reduction']:.4f}, "
            f"feasibility_cost_reduction={domain_payload['comparison']['feasibility_cost_reduction']:.4f}"
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_fallback_feasibility_reports(
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
    report_md.write_text(render_fallback_feasibility_markdown(payload), encoding="utf-8")
    cases_json.write_text(json.dumps(cases_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"json": report_json, "md": report_md, "cases": cases_json}


def _append_case(
    generated_cases: list[dict[str, Any]],
    kind_counts: Counter[str],
    violation_feature_counts: Counter[str],
    seen_signatures: set[str],
    case: dict[str, Any],
) -> None:
    signature = json.dumps(
        {
            "supported": case.get("supported", True),
            "expected_action_id": case.get("expected_action_id"),
            "input_features": case["input_features"],
        },
        sort_keys=True,
    )
    if signature in seen_signatures:
        return
    seen_signatures.add(signature)
    generated_cases.append(case)
    kind_counts[case["case_kind"]] += 1
    for feature_name in case.get("violated_feasibility_features", []):
        violation_feature_counts[feature_name] += 1


def _decision_to_case_result(case: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "base_case_id": case.get("base_case_id"),
        "case_kind": case.get("case_kind"),
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
        "violated_feasibility_features": list(case.get("violated_feasibility_features", [])),
    }


def _feasibility_cost(case_result: dict[str, Any]) -> float:
    final_status = case_result.get("final_status")
    supported = bool(case_result.get("supported", True))
    correct = bool(case_result.get("correct", False))
    if supported:
        return 0.0 if correct and final_status == "fallback_executed" else 1.0
    return 0.0 if final_status in {"fail_closed", "abstained", "validation_failed"} else 1.25


def _is_infeasible_handoff_case(
    *,
    registry,
    validator: DeterministicValidator,
    fallback_probe: DecisionCandidate,
    fallback_action_id: str,
    features: dict[str, Any],
    mutation_values: dict[str, tuple[Any, ...]],
) -> bool:
    context_valid, _ = evaluate_registry_context(registry, features)
    if not context_valid:
        return False
    if not _violated_feasibility_features(features, mutation_values):
        return False
    if validator.validate(fallback_probe, features).valid:
        return False
    return not _supported_non_fallback_actions(
        validator=validator,
        registry=registry,
        fallback_action_id=fallback_action_id,
        features=features,
    )


def _supported_non_fallback_actions(
    *,
    validator: DeterministicValidator,
    registry,
    fallback_action_id: str,
    features: dict[str, Any],
) -> list[str]:
    supported_actions: list[str] = []
    for action in registry.actions:
        if action.action_id == fallback_action_id:
            continue
        if validator.validate(
            DecisionCandidate(action_id=action.action_id, confidence=1.0),
            features,
        ).valid:
            supported_actions.append(action.action_id)
    return supported_actions


def _violated_feasibility_features(
    features: dict[str, Any],
    mutation_values: dict[str, tuple[Any, ...]],
) -> list[str]:
    return [
        feature_name
        for feature_name, invalid_values in mutation_values.items()
        if features.get(feature_name) in invalid_values
    ]


def _resolve_learned_model_path(
    repo_root: Path,
    domain: str,
    learned_model_path: str | Path | None,
) -> str | None:
    if learned_model_path is not None:
        path = Path(learned_model_path)
        return str(path) if path.exists() else None
    default_path = repo_root / "kvrm-models" / f"{domain}_compact_selector_v1.joblib"
    return str(default_path) if default_path.exists() else None
