from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.registry import load_registry
from kvrm_core.types import DecisionCandidate, DecisionInput
from kvrm_core.validation import DeterministicValidator

from .counterfactual import load_or_generate_boundary_counterfactual_cases
from .demo import DOMAIN_CONFIG, _cached_runtime_for_strategy, load_cases
from .metrics import compute_metrics

DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_REPORT_JSON = "registry_evolution_report.json"
DEFAULT_REPORT_MD = "registry_evolution_report.md"
DEFAULT_CASES_JSON = "registry_evolution_cases.json"
DEFAULT_REGISTRY_EVOLUTION_THRESHOLD = 0.60
DEFAULT_COUNTERFACTUAL_CACHE_DIR_NAME = "counterfactual_boundary_case_cache"
VARIANT_ORDER = ("live_hybrid", "stale_validated", "stale_unvalidated")
MAX_RENAME_CASES = 3
MAX_SPLIT_CASES_PER_ACTION = 2
MAX_TIGHTENED_SUPPORT_CASES = 6

REGISTRY_EVOLUTION_SCENARIOS: dict[str, dict[str, Any]] = {
    "soc": {
        "rename": {
            "live_action_id": "collect_forensics",
            "legacy_action_id": "legacy_collect_forensics",
        },
        "split": {
            "legacy_action_id": "legacy_network_containment",
            "live_action_ids": ("isolate_host", "block_ip_temporarily"),
        },
    },
    "sre": {
        "rename": {
            "live_action_id": "rollback_deploy",
            "legacy_action_id": "legacy_rollback_deploy",
        },
        "split": {
            "legacy_action_id": "legacy_regional_mitigation",
            "live_action_ids": ("failover_region", "enable_readonly_mode"),
        },
    },
    "drone": {
        "rename": {
            "live_action_id": "climb_for_signal_recovery",
            "legacy_action_id": "legacy_climb_for_signal_recovery",
        },
        "split": {
            "legacy_action_id": "legacy_route_recovery",
            "live_action_ids": ("return_to_home", "descend_for_safety"),
        },
    },
    "grid": {
        "rename": {
            "live_action_id": "prepare_blackstart",
            "legacy_action_id": "legacy_prepare_blackstart",
        },
        "split": {
            "legacy_action_id": "legacy_distribution_fault_response",
            "live_action_ids": ("transfer_load", "dispatch_field_crew"),
        },
    },
    "finance": {
        "rename": {
            "live_action_id": "lower_limit_temporarily",
            "legacy_action_id": "legacy_lower_limit_temporarily",
        },
        "split": {
            "legacy_action_id": "legacy_document_risk_review",
            "live_action_ids": ("require_additional_docs", "enhanced_due_diligence"),
        },
    },
    "medical": {
        "rename": {
            "live_action_id": "lab_panel_priority_order",
            "legacy_action_id": "legacy_lab_panel_priority_order",
        },
        "split": {
            "legacy_action_id": "legacy_acute_pathway_triage",
            "live_action_ids": ("sepsis_screen_pathway", "cardiac_chest_pain_pathway"),
        },
    },
    "iam": {
        "rename": {
            "live_action_id": "grant_timeboxed_privileged_access",
            "legacy_action_id": "legacy_grant_timeboxed_privileged_access",
        },
        "split": {
            "legacy_action_id": "legacy_access_review_flow",
            "live_action_ids": ("require_manager_approval", "require_security_review"),
        },
    },
}


def generate_registry_evolution_cases(
    *,
    repo_root: str | Path,
    domain: str,
    counterfactual_cache_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported registry evolution domain: {domain}")

    scenario = REGISTRY_EVOLUTION_SCENARIOS[domain]
    data_dir = repo_root / DOMAIN_CONFIG[domain]["data_dir"]
    registry = load_registry(data_dir / "registry.json")
    base_cases = load_cases(data_dir / "cases.jsonl")
    supported_cases = [
        case
        for case in base_cases
        if case.get("supported", True) and case.get("expected_action_id")
    ]
    fallback_action_ids = {
        action.action_id
        for action in registry.actions
        if "fallback" in action.tags
    }
    supported_by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in supported_cases:
        supported_by_action[case["expected_action_id"]].append(case)
    for cases in supported_by_action.values():
        cases.sort(key=lambda row: row["case_id"])

    generated_cases: list[dict[str, Any]] = []
    case_kind_counts: Counter[str] = Counter()
    stale_action_counts: Counter[str] = Counter()
    migration_action_counts: Counter[str] = Counter()

    rename_live_action_id = scenario["rename"]["live_action_id"]
    rename_legacy_action_id = scenario["rename"]["legacy_action_id"]
    for case in supported_by_action[rename_live_action_id][:MAX_RENAME_CASES]:
        evolution_case = _base_case_payload(
            case=case,
            case_id=f"{case['case_id']}:registry_rename",
            case_kind="action_id_renamed",
            stale_selected_action_id=rename_legacy_action_id,
            migration_note=f"legacy selector still emits renamed action id `{rename_legacy_action_id}`",
        )
        generated_cases.append(evolution_case)
        case_kind_counts["action_id_renamed"] += 1
        stale_action_counts[rename_legacy_action_id] += 1
        migration_action_counts[rename_live_action_id] += 1

    split_live_action_ids = scenario["split"]["live_action_ids"]
    split_legacy_action_id = scenario["split"]["legacy_action_id"]
    for live_action_id in split_live_action_ids:
        for case in supported_by_action[live_action_id][:MAX_SPLIT_CASES_PER_ACTION]:
            evolution_case = _base_case_payload(
                case=case,
                case_id=f"{case['case_id']}:registry_split",
                case_kind="action_split",
                stale_selected_action_id=split_legacy_action_id,
                migration_note=(
                    f"legacy selector still emits merged predecessor action `{split_legacy_action_id}` "
                    f"instead of the live action `{live_action_id}`"
                ),
            )
            generated_cases.append(evolution_case)
            case_kind_counts["action_split"] += 1
            stale_action_counts[split_legacy_action_id] += 1
            migration_action_counts[live_action_id] += 1

    counterfactual_payload = load_or_generate_boundary_counterfactual_cases(
        repo_root=repo_root,
        domain=domain,
        artifact_dir=counterfactual_cache_dir,
    )
    base_case_map = {case["case_id"]: case for case in base_cases}
    tightened_support_cases = _select_tightened_support_cases(
        counterfactual_cases=counterfactual_payload["cases"],
        base_case_map=base_case_map,
        fallback_action_ids=fallback_action_ids,
    )
    for case in tightened_support_cases:
        base_case = base_case_map[case["base_case_id"]]
        stale_action_id = base_case["expected_action_id"]
        evolution_case = {
            "case_id": f"{case['case_id']}:registry_tightened_support",
            "base_case_id": case["base_case_id"],
            "case_kind": "tightened_support",
            "expected_action_id": None,
            "stale_selected_action_id": stale_action_id,
            "stale_selected_action_exists_in_live_registry": True,
            "input_features": dict(case["input_features"]),
            "supported": False,
            "ood": True,
            "mutated_feature": case["mutated_feature"],
            "from_value": case.get("from_value"),
            "to_value": case.get("to_value"),
            "migration_note": (
                f"legacy selector reuses prior supported action `{stale_action_id}` after the live registry "
                "tightens the support boundary"
            ),
        }
        generated_cases.append(evolution_case)
        case_kind_counts["tightened_support"] += 1
        stale_action_counts[stale_action_id] += 1
        migration_action_counts[stale_action_id] += 1

    generated_cases.sort(key=lambda row: (row["case_kind"], row["case_id"]))
    supported_case_count = sum(1 for case in generated_cases if case["supported"])
    unsupported_case_count = len(generated_cases) - supported_case_count
    return {
        "domain": domain,
        "registry_name": registry.registry_name,
        "registry_version": registry.version,
        "registry_digest": registry.digest,
        "generated_case_count": len(generated_cases),
        "supported_case_count": supported_case_count,
        "unsupported_case_count": unsupported_case_count,
        "case_kind_counts": dict(sorted(case_kind_counts.items())),
        "stale_action_counts": dict(sorted(stale_action_counts.items())),
        "migration_action_counts": dict(sorted(migration_action_counts.items())),
        "counterfactual_case_pack_source": counterfactual_payload.get("case_pack_source"),
        "counterfactual_case_pack_signature": counterfactual_payload.get("case_pack_signature"),
        "cases": generated_cases,
    }


def run_registry_evolution_benchmark(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_REGISTRY_EVOLUTION_THRESHOLD,
    learned_model_paths: dict[str, str | Path] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    active_domains = list(domains or DOMAIN_CONFIG.keys())
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)
    counterfactual_cache_dir = results_dir / DEFAULT_COUNTERFACTUAL_CACHE_DIR_NAME

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "counterfactual_case_cache_dir": str(counterfactual_cache_dir),
        "domains": {},
        "summary": {},
    }
    cases_payload: dict[str, Any] = {}

    live_perfect_continuity_domains = 0
    stale_validated_zero_unsafe_domains = 0
    stale_unvalidated_obsolete_execution_domains = 0
    stale_unvalidated_tightened_false_accept_domains = 0

    for domain in active_domains:
        generated = generate_registry_evolution_cases(
            repo_root=repo_root,
            domain=domain,
            counterfactual_cache_dir=counterfactual_cache_dir,
        )
        cases = generated["cases"]
        cases_payload[domain] = cases
        runtime, _ = _cached_runtime_for_strategy(
            str(repo_root),
            domain,
            "cases.jsonl",
            "hybrid",
            str(_resolve_learned_model_path(repo_root, domain, learned_model_paths))
            if _resolve_learned_model_path(repo_root, domain, learned_model_paths) is not None
            else None,
            threshold,
        )
        if runtime is None:
            raise ValueError(f"hybrid selector unavailable for {domain}")

        registry = runtime.registry
        validator = DeterministicValidator(registry)
        live_action_ids = {action.action_id for action in registry.actions}

        variant_payloads: dict[str, dict[str, Any]] = {}
        for variant in VARIANT_ORDER:
            case_results: list[dict[str, Any]] = []
            if variant == "live_hybrid":
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
            elif variant == "stale_validated":
                for case in cases:
                    case_results.append(
                        _stale_case_result(
                            case,
                            validator=validator,
                            live_action_ids=live_action_ids,
                            validate_live_registry=True,
                        )
                    )
            elif variant == "stale_unvalidated":
                for case in cases:
                    case_results.append(
                        _stale_case_result(
                            case,
                            validator=validator,
                            live_action_ids=live_action_ids,
                            validate_live_registry=False,
                        )
                    )
            else:
                raise ValueError(f"unsupported registry evolution variant: {variant}")

            variant_payloads[variant] = {
                "case_count": len(case_results),
                "metrics": compute_metrics(case_results),
                "evolution_metrics": compute_registry_evolution_metrics(
                    case_results,
                    live_action_ids=live_action_ids,
                ),
            }

        live_metrics = variant_payloads["live_hybrid"]["evolution_metrics"]
        stale_validated_metrics = variant_payloads["stale_validated"]["evolution_metrics"]
        stale_unvalidated_metrics = variant_payloads["stale_unvalidated"]["evolution_metrics"]

        if live_metrics["supported_migration_success_rate"] == 1.0:
            live_perfect_continuity_domains += 1
        if (
            stale_validated_metrics["obsolete_action_execution_rate"] == 0.0
            and stale_validated_metrics["tightened_support_false_accept_rate"] == 0.0
        ):
            stale_validated_zero_unsafe_domains += 1
        if stale_unvalidated_metrics["obsolete_action_execution_rate"] > 0.0:
            stale_unvalidated_obsolete_execution_domains += 1
        if stale_unvalidated_metrics["tightened_support_false_accept_rate"] > 0.0:
            stale_unvalidated_tightened_false_accept_domains += 1

        payload["domains"][domain] = {
            **{key: value for key, value in generated.items() if key != "cases"},
            "variants": variant_payloads,
            "comparison": {
                "supported_continuity_gain_over_stale_validated": (
                    live_metrics["supported_migration_success_rate"]
                    - stale_validated_metrics["supported_migration_success_rate"]
                ),
                "obsolete_execution_reduction_vs_unvalidated": (
                    stale_unvalidated_metrics["obsolete_action_execution_rate"]
                    - live_metrics["obsolete_action_execution_rate"]
                ),
                "tightened_support_false_accept_reduction_vs_unvalidated": (
                    stale_unvalidated_metrics["tightened_support_false_accept_rate"]
                    - live_metrics["tightened_support_false_accept_rate"]
                ),
                "mean_decision_cost_reduction_vs_unvalidated": (
                    variant_payloads["stale_unvalidated"]["metrics"]["mean_decision_cost"]
                    - variant_payloads["live_hybrid"]["metrics"]["mean_decision_cost"]
                ),
                "mean_decision_cost_reduction_vs_stale_validated": (
                    variant_payloads["stale_validated"]["metrics"]["mean_decision_cost"]
                    - variant_payloads["live_hybrid"]["metrics"]["mean_decision_cost"]
                ),
            },
        }

    payload["summary"] = {
        "domain_count": len(active_domains),
        "live_perfect_continuity_domains": live_perfect_continuity_domains,
        "stale_validated_zero_unsafe_domains": stale_validated_zero_unsafe_domains,
        "stale_unvalidated_obsolete_execution_domains": stale_unvalidated_obsolete_execution_domains,
        "stale_unvalidated_tightened_false_accept_domains": stale_unvalidated_tightened_false_accept_domains,
    }
    report_paths = write_registry_evolution_reports(payload, cases_payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    payload["cases_json"] = str(report_paths["cases"])
    return payload


def compute_registry_evolution_metrics(
    case_results: list[dict[str, Any]],
    *,
    live_action_ids: set[str],
) -> dict[str, float]:
    supported_migration_cases = [
        case
        for case in case_results
        if case.get("case_kind") in {"action_id_renamed", "action_split"}
    ]
    tightened_support_cases = [
        case for case in case_results if case.get("case_kind") == "tightened_support"
    ]

    def rate(items: list[dict[str, Any]], pred) -> float:
        if not items:
            return 0.0
        return sum(1 for item in items if pred(item)) / len(items)

    return {
        "supported_migration_success_rate": rate(
            supported_migration_cases,
            lambda item: bool(item.get("correct", False)),
        ),
        "supported_migration_fail_closed_rate": rate(
            supported_migration_cases,
            lambda item: item.get("final_status") in {"abstained", "fallback_executed", "fail_closed", "validation_failed"},
        ),
        "obsolete_action_execution_rate": rate(
            supported_migration_cases,
            lambda item: (
                item.get("selected_action_id") == item.get("stale_selected_action_id")
                and item.get("selected_action_id") not in live_action_ids
                and item.get("final_status") == "executed"
            ),
        ),
        "obsolete_action_fail_closed_rate": rate(
            supported_migration_cases,
            lambda item: (
                item.get("selected_action_id") == item.get("stale_selected_action_id")
                and item.get("selected_action_id") not in live_action_ids
                and item.get("final_status") in {"abstained", "fallback_executed", "fail_closed", "validation_failed"}
            ),
        ),
        "tightened_support_false_accept_rate": rate(
            tightened_support_cases,
            lambda item: item.get("final_status") == "executed",
        ),
        "tightened_support_safe_rejection_rate": rate(
            tightened_support_cases,
            lambda item: item.get("final_status") in {"abstained", "fallback_executed", "fail_closed", "validation_failed"},
        ),
        "stale_label_selected_rate": rate(
            case_results,
            lambda item: item.get("selected_action_id") == item.get("stale_selected_action_id"),
        ),
    }


def render_registry_evolution_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Registry-Evolution Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "This benchmark isolates registry-evolution safety and continuity. It compares the live hybrid "
            "runtime against two stale-selector baselines:"
        ),
        "- `stale_validated`: a legacy selector emits stale actions but still passes through the live validator.",
        "- `stale_unvalidated`: a legacy selector emits stale actions and executes them without live validation.",
        "",
        (
            "The migration cases cover three families: obsolete renamed action ids, obsolete merged predecessor "
            "actions that were split into multiple live actions, and tightened support envelopes where a once-"
            "plausible live action is now unsupported."
        ),
        "",
        (
            f"Summary: live perfect continuity domains={payload['summary']['live_perfect_continuity_domains']}/"
            f"{payload['summary']['domain_count']}; stale validated zero-unsafe domains="
            f"{payload['summary']['stale_validated_zero_unsafe_domains']}/{payload['summary']['domain_count']}; "
            f"stale unvalidated obsolete-execution domains={payload['summary']['stale_unvalidated_obsolete_execution_domains']}/"
            f"{payload['summary']['domain_count']}; stale unvalidated tightened-support false-accept domains="
            f"{payload['summary']['stale_unvalidated_tightened_false_accept_domains']}/{payload['summary']['domain_count']}."
        ),
        "",
        "| Domain | Cases | Rename | Split | Tightened | Live Continuity | Stale+Validate Continuity | Stale No-Validate Obsolete Exec | Live Tight Reject | Stale+Validate Tight Reject | Stale No-Validate Tight False Accept |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for domain, domain_payload in payload["domains"].items():
        live_metrics = domain_payload["variants"]["live_hybrid"]["evolution_metrics"]
        stale_validated_metrics = domain_payload["variants"]["stale_validated"]["evolution_metrics"]
        stale_unvalidated_metrics = domain_payload["variants"]["stale_unvalidated"]["evolution_metrics"]
        case_kind_counts = domain_payload["case_kind_counts"]
        lines.append(
            "| "
            f"{domain} | "
            f"{domain_payload['generated_case_count']} | "
            f"{case_kind_counts.get('action_id_renamed', 0)} | "
            f"{case_kind_counts.get('action_split', 0)} | "
            f"{case_kind_counts.get('tightened_support', 0)} | "
            f"{live_metrics['supported_migration_success_rate']:.4f} | "
            f"{stale_validated_metrics['supported_migration_success_rate']:.4f} | "
            f"{stale_unvalidated_metrics['obsolete_action_execution_rate']:.4f} | "
            f"{live_metrics['tightened_support_safe_rejection_rate']:.4f} | "
            f"{stale_validated_metrics['tightened_support_safe_rejection_rate']:.4f} | "
            f"{stale_unvalidated_metrics['tightened_support_false_accept_rate']:.4f} |"
        )
        lines.append(
            f"Cost `{domain}`: "
            f"live={domain_payload['variants']['live_hybrid']['metrics']['mean_decision_cost']:.4f}, "
            f"stale_validated={domain_payload['variants']['stale_validated']['metrics']['mean_decision_cost']:.4f}, "
            f"stale_unvalidated={domain_payload['variants']['stale_unvalidated']['metrics']['mean_decision_cost']:.4f}"
        )
        lines.append(
            f"Gain `{domain}`: "
            f"continuity_vs_stale_validated={domain_payload['comparison']['supported_continuity_gain_over_stale_validated']:.4f}, "
            f"obsolete_execution_reduction={domain_payload['comparison']['obsolete_execution_reduction_vs_unvalidated']:.4f}, "
            f"tightened_false_accept_reduction={domain_payload['comparison']['tightened_support_false_accept_reduction_vs_unvalidated']:.4f}"
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_registry_evolution_reports(
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
    report_md.write_text(render_registry_evolution_markdown(payload), encoding="utf-8")
    cases_json.write_text(json.dumps(cases_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"json": report_json, "md": report_md, "cases": cases_json}


def _base_case_payload(
    *,
    case: dict[str, Any],
    case_id: str,
    case_kind: str,
    stale_selected_action_id: str,
    migration_note: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "base_case_id": case["case_id"],
        "case_kind": case_kind,
        "expected_action_id": case["expected_action_id"],
        "stale_selected_action_id": stale_selected_action_id,
        "stale_selected_action_exists_in_live_registry": False,
        "input_features": dict(case["input_features"]),
        "supported": True,
        "ood": bool(case.get("ood", False)),
        "migration_note": migration_note,
    }


def _select_tightened_support_cases(
    *,
    counterfactual_cases: list[dict[str, Any]],
    base_case_map: dict[str, dict[str, Any]],
    fallback_action_ids: set[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_feature_keys: set[tuple[str, str]] = set()
    for case in counterfactual_cases:
        if case.get("supported", True):
            continue
        base_case = base_case_map.get(case.get("base_case_id"))
        if base_case is None:
            continue
        stale_action_id = base_case.get("expected_action_id")
        if not stale_action_id or stale_action_id in fallback_action_ids:
            continue
        key = (stale_action_id, case["mutated_feature"])
        if key in seen_feature_keys:
            continue
        selected.append(case)
        seen_feature_keys.add(key)
        if len(selected) >= MAX_TIGHTENED_SUPPORT_CASES:
            return selected

    if len(selected) >= MAX_TIGHTENED_SUPPORT_CASES:
        return selected[:MAX_TIGHTENED_SUPPORT_CASES]

    seen_case_ids = {case["case_id"] for case in selected}
    for case in counterfactual_cases:
        if len(selected) >= MAX_TIGHTENED_SUPPORT_CASES:
            break
        if case.get("supported", True):
            continue
        if case["case_id"] in seen_case_ids:
            continue
        base_case = base_case_map.get(case.get("base_case_id"))
        if base_case is None:
            continue
        stale_action_id = base_case.get("expected_action_id")
        if not stale_action_id or stale_action_id in fallback_action_ids:
            continue
        selected.append(case)
        seen_case_ids.add(case["case_id"])
    return selected


def _stale_case_result(
    case: dict[str, Any],
    *,
    validator: DeterministicValidator,
    live_action_ids: set[str],
    validate_live_registry: bool,
) -> dict[str, Any]:
    stale_action_id = case["stale_selected_action_id"]
    candidate = DecisionCandidate(
        action_id=stale_action_id,
        confidence=0.99,
        source="stale_selector",
    )
    validation = validator.validate(candidate, case["input_features"]) if validate_live_registry else None
    final_status = "executed" if validation is None or validation.valid else "fail_closed"
    valid = bool(validation.valid) if validation is not None else stale_action_id in live_action_ids
    return {
        "case_id": case["case_id"],
        "base_case_id": case.get("base_case_id"),
        "case_kind": case.get("case_kind"),
        "expected_action_id": case.get("expected_action_id"),
        "stale_selected_action_id": stale_action_id,
        "supported": case.get("supported", True),
        "ood": case.get("ood", False),
        "selected_action_id": stale_action_id,
        "confidence": 0.99,
        "valid": valid,
        "correct": valid and stale_action_id == case.get("expected_action_id"),
        "abstained": False,
        "fallback_used": False,
        "latency_ms": 0.0,
        "final_status": final_status,
        "validation_reason": validation.reason if validation is not None else None,
        "migration_note": case.get("migration_note"),
    }


def _decision_to_case_result(case: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "base_case_id": case.get("base_case_id"),
        "case_kind": case.get("case_kind"),
        "expected_action_id": case.get("expected_action_id"),
        "stale_selected_action_id": case.get("stale_selected_action_id"),
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
        "migration_note": case.get("migration_note"),
    }


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
