from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from kvrm_core.context import feature_key
from kvrm_core.registry import load_registry
from kvrm_core.support import evaluate_support_spec


FEATURE_RECOMMENDATIONS: dict[str, list[dict[str, Any]]] = {
    "soc": [
        {
            "priority": "monitoring_only",
            "pairs": [],
            "why": "The current SOC benchmark is already linearly separable under the existing structured feature schema.",
            "features": [
                "asset_isolation_feasibility",
                "identity_scope_size",
                "service_criticality_override",
            ],
        }
    ],
    "sre": [
        {
            "priority": "monitoring_only",
            "pairs": [],
            "why": "The canonical SRE schema now includes locality, failover-policy, deployment-causality, handoff-feasibility, and coordination-state signals, and the current supported pack is separable under the existing audited feature contract.",
            "features": [
                "quorum_recovery_eta",
                "write_consistency_requirement",
                "traffic_shift_capacity_margin",
                "incident_command_ready",
            ],
        },
        {
            "priority": "medium",
            "pairs": [["failover_region", "enable_readonly_mode"], ["failover_region", "page_human_operator"]],
            "why": "The next SRE expansion should target recovery-planning and write-consistency constraints on top of the now-explicit coordination envelope rather than re-adding generic severity features.",
            "features": [
                "quorum_recovery_eta",
                "write_consistency_requirement",
                "control_plane_rate_limit_state",
                "incident_command_ready",
            ],
        },
    ],
    "drone": [
        {
            "priority": "monitoring_only",
            "pairs": [],
            "why": "The canonical drone schema now encodes route-energy, landing safety, takeover feasibility, and airspace-governance signals, and the current supported pack is separable under that audited contract.",
            "features": [
                "airspace_corridor_stability",
                "operator_attention_budget",
                "replan_authorization_state",
                "diversion_site_commitment",
            ],
        },
        {
            "priority": "medium",
            "pairs": [["switch_to_low_observable_path", "manual_handoff"], ["return_to_home", "manual_handoff"]],
            "why": "The next drone expansion should target contested-airspace transitions and command-authority constraints on top of the now-explicit path, recovery, and handoff boundaries.",
            "features": [
                "airspace_corridor_stability",
                "jamming_severity",
                "operator_attention_budget",
                "replan_authorization_state",
            ],
        },
    ],
    "grid": [
        {
            "priority": "medium",
            "pairs": [["dispatch_field_crew", "transfer_load"], ["isolate_faulted_feeder", "transfer_load"]],
            "why": "The grid registry now cleanly separates audited transfer-vs-dispatch behavior with transfer-path availability, so the next step is richer topology and authorization semantics rather than another generic outage severity field.",
            "features": [
                "remote_switching_ready",
                "alternate_topology_capacity_margin",
                "protective_zone_confidence",
                "restoration_sequence_locked",
            ],
        }
    ],
    "finance": [
        {
            "priority": "medium",
            "pairs": [["enhanced_due_diligence", "manual_review"], ["require_additional_docs", "manual_review"]],
            "why": "The finance registry now separates bounded due-diligence and documentation workflows from ambiguous human-review cases, so the next gains come from source-of-funds and identity-assurance signals.",
            "features": [
                "source_of_funds_confidence",
                "beneficial_owner_complexity",
                "document_authenticity_confidence",
                "merchant_risk_cluster",
            ],
        }
    ],
    "medical": [
        {
            "priority": "medium",
            "pairs": [["sepsis_screen_pathway", "respiratory_support_pathway"], ["sepsis_screen_pathway", "escalate_supervisor_review"]],
            "why": "The medical registry now forces explicit sepsis precedence over generic respiratory or supervisor escalation, so the next frontier is multi-protocol coordination and contraindication handling.",
            "features": [
                "protocol_contraindication_flag",
                "icu_bed_pressure",
                "lactate_trend_bucket",
                "antibiotic_delay_risk",
            ],
        }
    ],
    "iam": [
        {
            "priority": "medium",
            "pairs": [["require_manager_approval", "require_security_review"], ["grant_break_glass_access", "escalate_identity_admin"]],
            "why": "The IAM registry now cleanly separates bounded approval, review, break-glass, denial, and manual-admin escalation flows, so the next gains come from stronger identity-assurance and delegated-authority signals rather than another generic risk bucket.",
            "features": [
                "identity_assurance_level",
                "resource_owner_approval",
                "delegated_admin_scope",
                "just_in_time_token_health",
            ],
        }
    ],
}


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def exact_conflict_groups(cases: list[dict[str, Any]], *, supported_only: bool = True) -> list[dict[str, Any]]:
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        if supported_only and not case.get("supported", True):
            continue
        by_key[feature_key(case["input_features"])].append(case)

    groups: list[dict[str, Any]] = []
    for key, items in by_key.items():
        labels = [item.get("expected_action_id") for item in items]
        label_set = {label for label in labels if label is not None}
        if len(label_set) <= 1:
            continue
        groups.append(
            {
                "feature_key": key,
                "size": len(items),
                "label_counts": dict(Counter(labels)),
                "cases": [
                    {
                        "case_id": item.get("case_id"),
                        "expected_action_id": item.get("expected_action_id"),
                    }
                    for item in items
                ],
            }
        )
    groups.sort(key=lambda group: (-group["size"], group["feature_key"]))
    return groups


def exact_feature_oracle_accuracy(cases: list[dict[str, Any]], *, supported_only: bool = True) -> float:
    by_key: dict[str, list[str | None]] = defaultdict(list)
    total = 0
    for case in cases:
        if supported_only and not case.get("supported", True):
            continue
        label = case.get("expected_action_id")
        if label is None:
            continue
        by_key[feature_key(case["input_features"])].append(label)
        total += 1
    if total == 0:
        return 0.0
    oracle_correct = sum(Counter(labels).most_common(1)[0][1] for labels in by_key.values())
    return oracle_correct / total


def support_overlap_cases(registry, cases: list[dict[str, Any]], *, supported_only: bool = True) -> list[dict[str, Any]]:
    overlap_rows: list[dict[str, Any]] = []
    for case in cases:
        if supported_only and not case.get("supported", True):
            continue
        matched_actions = []
        for action in registry.actions:
            supported, _ = evaluate_support_spec(action.support_spec, case["input_features"])
            if supported:
                matched_actions.append(action.action_id)
        if len(matched_actions) <= 1:
            continue
        overlap_rows.append(
            {
                "case_id": case.get("case_id"),
                "expected_action_id": case.get("expected_action_id"),
                "matched_actions": matched_actions,
            }
        )
    return overlap_rows


def top_overlap_pairs(overlap_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for row in overlap_rows:
        actions = row["matched_actions"]
        for index, left in enumerate(actions):
            for right in actions[index + 1 :]:
                counts[tuple(sorted((left, right)))] += 1
    return [
        {"pair": list(pair), "count": count}
        for pair, count in counts.most_common()
    ]


def load_hybrid_accuracy(results_path: str | Path, domain_name: str) -> float | None:
    path = Path(results_path)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    try:
        return float(payload[domain_name]["hybrid"]["metrics"]["semantic_correctness_rate"])
    except Exception:
        pass
    try:
        return float(payload["demos"][f"{domain_name}_hybrid"]["semantic_correctness_rate"])
    except Exception:
        return None


def analyze_domain(
    *,
    domain_name: str,
    registry_path: str | Path,
    cases_path: str | Path,
    benchmark_results_path: str | Path | None = None,
) -> dict[str, Any]:
    registry = load_registry(Path(registry_path))
    cases = load_cases(cases_path)
    supported_cases = [case for case in cases if case.get("supported", True)]
    conflicts = exact_conflict_groups(cases, supported_only=True)
    overlap_rows = support_overlap_cases(registry, cases, supported_only=True)
    overlap_pair_rows = top_overlap_pairs(overlap_rows)
    oracle_accuracy = exact_feature_oracle_accuracy(cases, supported_only=True)
    hybrid_accuracy = load_hybrid_accuracy(benchmark_results_path, domain_name) if benchmark_results_path else None

    return {
        "domain": domain_name,
        "registry_path": str(registry_path),
        "cases_path": str(cases_path),
        "supported_case_count": len(supported_cases),
        "exact_feature_oracle_accuracy": oracle_accuracy,
        "exact_conflict_group_count": len(conflicts),
        "exact_conflict_case_count": sum(group["size"] for group in conflicts),
        "exact_conflict_groups": conflicts,
        "supported_overlap_case_count": len(overlap_rows),
        "supported_overlap_case_rate": (len(overlap_rows) / len(supported_cases)) if supported_cases else 0.0,
        "top_overlap_pairs": overlap_pair_rows,
        "hybrid_semantic_correctness_rate": hybrid_accuracy,
        "oracle_gap_pp": None if hybrid_accuracy is None else round(100.0 * (oracle_accuracy - hybrid_accuracy), 2),
        "hybrid_matches_exact_feature_oracle": None if hybrid_accuracy is None else abs(oracle_accuracy - hybrid_accuracy) < 1e-9,
        "feature_recommendations": FEATURE_RECOMMENDATIONS.get(domain_name, []),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# KVRM Feature Ceiling Analysis",
        "",
        "This report estimates what the current structured feature schema can separate before any selector improvements.",
        "",
    ]
    for domain_report in report["domains"]:
        domain = domain_report["domain"]
        lines.extend(
            [
                f"## {domain.upper()}",
                "",
                f"- Supported cases: `{domain_report['supported_case_count']}`",
                f"- Exact-feature oracle accuracy: `{domain_report['exact_feature_oracle_accuracy']:.4f}`",
                f"- Exact conflicting feature groups: `{domain_report['exact_conflict_group_count']}`",
                f"- Exact conflicting supported cases: `{domain_report['exact_conflict_case_count']}`",
                f"- Registry overlap rate on supported cases: `{domain_report['supported_overlap_case_rate']:.4f}`",
            ]
        )
        if domain_report["hybrid_semantic_correctness_rate"] is not None:
            lines.append(
                f"- Current hybrid semantic correctness: `{domain_report['hybrid_semantic_correctness_rate']:.4f}`"
            )
            lines.append(
                f"- Oracle gap (percentage points): `{domain_report['oracle_gap_pp']:.2f}`"
            )
            lines.append(
                f"- Hybrid matches exact-feature oracle: `{str(domain_report['hybrid_matches_exact_feature_oracle']).lower()}`"
            )
        lines.append("")

        if domain_report["top_overlap_pairs"]:
            lines.append("Top overlap pairs:")
            for row in domain_report["top_overlap_pairs"][:5]:
                lines.append(f"- `{row['pair'][0]}` vs `{row['pair'][1]}`: `{row['count']}` supported cases")
            lines.append("")

        if domain_report["exact_conflict_groups"]:
            lines.append("Exact conflicting feature groups:")
            for group in domain_report["exact_conflict_groups"][:5]:
                labels = ", ".join(f"{label}={count}" for label, count in group["label_counts"].items())
                case_ids = ", ".join(case["case_id"] for case in group["cases"])
                lines.append(f"- `{labels}` across `{case_ids}`")
            lines.append("")

        if domain_report["feature_recommendations"]:
            lines.append("Recommended next features:")
            for recommendation in domain_report["feature_recommendations"]:
                pair_text = ", ".join(
                    f"{pair[0]} vs {pair[1]}" for pair in recommendation.get("pairs", [])
                ) or "domain-wide robustness"
                feature_text = ", ".join(f"`{feature}`" for feature in recommendation["features"])
                lines.append(
                    f"- `{recommendation['priority']}` for {pair_text}: {recommendation['why']} Add {feature_text}."
                )
            lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "- If hybrid accuracy already equals the exact-feature oracle, more selector tuning alone will not improve benchmark accuracy.",
            "- In those cases the next gains require feature expansion, registry policy features, or relabeling contradictory examples.",
            "",
        ]
    )
    return "\n".join(lines)
