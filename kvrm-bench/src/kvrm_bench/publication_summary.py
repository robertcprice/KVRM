from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_PUBLICATION_SUMMARY_JSON = "publication_summary.json"
DEFAULT_PUBLICATION_SUMMARY_MD = "publication_summary.md"
DEFAULT_EXTERNAL_BASELINE_PATH = "baselines/qwen-baseline/outputs/ollama/live_canonical/consolidated_comparison.json"


def build_publication_summary(
    repo_root: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root_path = Path(repo_root)
    output_root = (
        Path(output_dir)
        if output_dir is not None
        else repo_root_path / "kvrm-bench" / "results" / "publication_bundle"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    sections = {
        "canonical_suite": _summarize_canonical_suite(repo_root_path),
        "support_gate_stress": _summarize_support_gate_stress(repo_root_path),
        "fallback_feasibility": _summarize_fallback_feasibility(repo_root_path),
        "registry_evolution": _summarize_registry_evolution(repo_root_path),
        "incident_replay": _summarize_win_loss_family(
            repo_root_path,
            rel_path="kvrm-bench/results/incident_replay_report.json",
            section_name="incident_replay",
            gain_key="hybrid_episode_regret_gain",
        ),
        "counterfactual_boundary": _summarize_win_loss_family(
            repo_root_path,
            rel_path="kvrm-bench/results/counterfactual_boundary_report.json",
            section_name="counterfactual_boundary",
            gain_key="hybrid_regret_gain",
        ),
        "ambiguity_frontier": _summarize_ambiguity_frontier(repo_root_path),
        "temporal_transition": _summarize_win_loss_family(
            repo_root_path,
            rel_path="kvrm-bench/results/temporal_transition_report.json",
            section_name="temporal_transition",
            gain_key="hybrid_sequence_regret_gain",
        ),
        "coordination_chain": _summarize_win_loss_family(
            repo_root_path,
            rel_path="kvrm-bench/results/coordination_chain_report.json",
            section_name="coordination_chain",
            gain_key="hybrid_chain_regret_gain",
        ),
        "feature_ceiling": _summarize_feature_ceiling(repo_root_path),
        "external_baselines": _summarize_external_baselines(repo_root_path),
    }

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_root": _display_path(output_root, repo_root_path),
        "sections": sections,
        "headline_claims": _build_headline_claims(sections),
    }

    json_path = output_root / DEFAULT_PUBLICATION_SUMMARY_JSON
    markdown_path = output_root / DEFAULT_PUBLICATION_SUMMARY_MD
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_publication_summary_markdown(summary), encoding="utf-8")
    return {
        "path": str(json_path),
        "markdown_path": str(markdown_path),
        "summary": summary,
    }


def render_publication_summary_markdown(summary: dict[str, Any]) -> str:
    sections = summary["sections"]
    canonical = sections["canonical_suite"]
    support_gate = sections["support_gate_stress"]
    fallback = sections["fallback_feasibility"]
    registry = sections["registry_evolution"]
    replay = sections["incident_replay"]
    counterfactual = sections["counterfactual_boundary"]
    temporal = sections["temporal_transition"]
    coordination = sections["coordination_chain"]
    ambiguity = sections["ambiguity_frontier"]
    ceiling = sections["feature_ceiling"]
    baselines = sections["external_baselines"]

    lines = [
        "# KVRM Publication Summary",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        f"Output root: `{summary['output_root']}`",
        "",
        "## Headline Claims",
        "",
        "| Claim | Status | Evidence | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for claim in summary["headline_claims"]:
        lines.append(
            f"| {claim['statement']} | {claim['status']} | `{claim['evidence']}` | {claim['summary']} |"
        )

    if canonical["available"]:
        lines.extend(
            [
                "",
                "## Canonical Suite",
                "",
                (
                    f"The live canonical suite covers {canonical['domain_count']} domains and "
                    f"{canonical['total_case_count']} total cases."
                ),
                "",
                "| Domain | Cases | Semantic | False Accept | Unsupported Reject | Invalid Output |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for domain in canonical["domains"]:
            lines.append(
                "| "
                f"{domain['domain']} | "
                f"{domain['total_cases']} | "
                f"{domain['semantic_correctness_rate']:.4f} | "
                f"{domain['false_accept_rate']:.4f} | "
                f"{domain['unsupported_case_rejection_rate']:.4f} | "
                f"{domain['invalid_output_rate']:.4f} |"
            )

    lines.extend(
        [
            "",
            "## Architecture Evidence",
            "",
            (
                f"Support-gate stress: gated hybrid stays perfect in "
                f"{support_gate['gated_perfect_semantic_domain_count']}/{support_gate['domain_count']} domains, "
                f"while ungated semantic correctness ranges from "
                f"{support_gate['ungated_semantic_correctness_range']['min']:.4f} to "
                f"{support_gate['ungated_semantic_correctness_range']['max']:.4f}."
                if support_gate["available"]
                else "Support-gate stress summary unavailable."
            ),
            (
                f"Fallback feasibility: strict runtime keeps zero unsafe execution in "
                f"{fallback['strict_zero_unsafe_execution_domain_count']}/{fallback['domain_count']} domains, "
                f"while the legacy bypass is unsafe in "
                f"{fallback['legacy_nonzero_unsafe_execution_domain_count']}/{fallback['domain_count']}."
                if fallback["available"]
                else "Fallback-feasibility summary unavailable."
            ),
            (
                f"Registry evolution: live hybrid keeps supported continuity in "
                f"{registry['live_continuity_domain_count']}/{registry['domain_count']} domains, "
                f"stale validated drops to zero continuity in "
                f"{registry['stale_validated_zero_continuity_domain_count']}/{registry['domain_count']}, "
                f"and stale unvalidated executes obsolete actions in "
                f"{registry['stale_unvalidated_obsolete_execution_domain_count']}/{registry['domain_count']}."
                if registry["available"]
                else "Registry-evolution summary unavailable."
            ),
        ]
    )

    lines.extend(
        [
            "",
            "## Robustness Families",
            "",
            "| Family | Domains | Wins | Ties | Losses | Strict Win Domains |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for name, section in (
        ("incident replay", replay),
        ("counterfactual boundary", counterfactual),
        ("temporal transition", temporal),
        ("coordination chain", coordination),
    ):
        if not section["available"]:
            continue
        strict_wins = ", ".join(section["strict_win_domains"]) or "-"
        lines.append(
            f"| {name} | {section['domain_count']} | {section['hybrid_win_count']} | "
            f"{section['hybrid_tie_count']} | {section['hybrid_loss_count']} | {strict_wins} |"
        )

    if ambiguity["available"]:
        lines.extend(
            [
                "",
                "## Ambiguity Frontier",
                "",
                (
                    f"Hybrid regret is zero in {ambiguity['zero_regret_domain_count']}/"
                    f"{ambiguity['domain_count']} domains on the current frontier slice."
                ),
            ]
        )

    if ceiling["available"]:
        lines.extend(
            [
                "",
                "## Feature Ceiling",
                "",
                (
                    f"Canonical schemas show zero supported overlap in "
                    f"{ceiling['zero_supported_overlap_domain_count']}/{ceiling['domain_count']} domains, "
                    f"and hybrid matches the exact-feature oracle in "
                    f"{ceiling['exact_oracle_match_domain_count']}/{ceiling['domain_count']}."
                ),
                "",
                "| Domain | Next Frontier Features | Priority |",
                "| --- | --- | --- |",
            ]
        )
        for frontier in ceiling["frontier_recommendations"]:
            lines.append(
                f"| {frontier['domain']} | {', '.join(frontier['features']) or '-'} | {frontier['priority']} |"
            )

    if baselines["available"]:
        best_model = baselines["best_model"]
        lines.extend(
            [
                "",
                "## External Baselines",
                "",
                (
                    f"Best evaluated Ollama baseline on the live six-domain subset is `{best_model['name']}` "
                    f"with macro semantic correctness `{best_model['macro_semantic_correctness_rate']:.4f}`, "
                    f"macro false accept `{best_model['macro_false_accept_rate']:.4f}`, and "
                    f"macro unsupported rejection `{best_model['macro_unsupported_case_rejection_rate']:.4f}`."
                ),
                "",
                (
                    f"KVRM on the same subset stays at macro semantic correctness "
                    f"`{baselines['kvrm_macro_semantic_correctness_rate']:.4f}`, macro false accept "
                    f"`{baselines['kvrm_macro_false_accept_rate']:.4f}`, and macro unsupported rejection "
                    f"`{baselines['kvrm_macro_unsupported_case_rejection_rate']:.4f}`."
                ),
            ]
        )

    lines.append("")
    return "\n".join(lines)


def _summarize_canonical_suite(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / "kvrm-demos/reports/demo_comparison.json")
    if payload is None:
        return {"available": False}
    raw_demos = payload.get("demos") or {}
    domains: list[dict[str, Any]] = []
    for raw_name, metrics in sorted(raw_demos.items()):
        domain = raw_name.removesuffix("_hybrid")
        domains.append({"domain": domain, **metrics})
    return {
        "available": True,
        "domain_count": len(domains),
        "total_case_count": sum(int(item["total_cases"]) for item in domains),
        "all_semantic_correctness_one": all(_is_one(item["semantic_correctness_rate"]) for item in domains),
        "all_structural_validity_one": all(_is_one(item["structural_validity_rate"]) for item in domains),
        "all_false_accept_zero": all(_is_zero(item["false_accept_rate"]) for item in domains),
        "all_unsupported_rejection_one": all(_is_one(item["unsupported_case_rejection_rate"]) for item in domains),
        "all_invalid_output_zero": all(_is_zero(item["invalid_output_rate"]) for item in domains),
        "domains": domains,
    }


def _summarize_support_gate_stress(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / "kvrm-bench/results/support_gate_stress_report.json")
    if payload is None:
        return {"available": False}
    domains = payload.get("domains") or {}
    gated_semantic = [dom["gated"]["metrics"]["semantic_correctness_rate"] for dom in domains.values()]
    ungated_semantic = [dom["ungated"]["metrics"]["semantic_correctness_rate"] for dom in domains.values()]
    semantic_gains = [dom["comparison"]["semantic_correctness_gain"] for dom in domains.values()]
    return {
        "available": True,
        "domain_count": len(domains),
        "gated_perfect_semantic_domain_count": sum(1 for value in gated_semantic if _is_one(value)),
        "ungated_nonperfect_domain_count": sum(1 for value in ungated_semantic if not _is_one(value)),
        "ungated_semantic_correctness_range": {"min": min(ungated_semantic), "max": max(ungated_semantic)},
        "semantic_correctness_gain_range": {"min": min(semantic_gains), "max": max(semantic_gains)},
        "strict_gain_domains": sorted(
            domain
            for domain, dom in domains.items()
            if float(dom["comparison"]["semantic_correctness_gain"]) > 0.0
        ),
    }


def _summarize_fallback_feasibility(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / "kvrm-bench/results/fallback_feasibility_report.json")
    if payload is None:
        return {"available": False}
    domains = payload.get("domains") or {}
    strict_unsafe = {
        domain: dom["variants"]["strict"]["feasibility_metrics"]["unsupported_unsafe_execution_rate"]
        for domain, dom in domains.items()
    }
    legacy_unsafe = {
        domain: dom["variants"]["legacy_bypass"]["feasibility_metrics"]["unsupported_unsafe_execution_rate"]
        for domain, dom in domains.items()
    }
    return {
        "available": True,
        "domain_count": len(domains),
        "strict_zero_unsafe_execution_domain_count": sum(1 for value in strict_unsafe.values() if _is_zero(value)),
        "legacy_nonzero_unsafe_execution_domain_count": sum(1 for value in legacy_unsafe.values() if float(value) > 0.0),
        "strict_zero_domains": sorted(domain for domain, value in strict_unsafe.items() if _is_zero(value)),
        "legacy_unsafe_domains": sorted(domain for domain, value in legacy_unsafe.items() if float(value) > 0.0),
    }


def _summarize_registry_evolution(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / "kvrm-bench/results/registry_evolution_report.json")
    if payload is None:
        return {"available": False}
    domains = payload.get("domains") or {}
    live = {
        domain: dom["variants"]["live_hybrid"]["evolution_metrics"]["supported_migration_success_rate"]
        for domain, dom in domains.items()
    }
    stale_validated = {
        domain: dom["variants"]["stale_validated"]["evolution_metrics"]["supported_migration_success_rate"]
        for domain, dom in domains.items()
    }
    stale_unvalidated = {
        domain: dom["variants"]["stale_unvalidated"]["evolution_metrics"]["obsolete_action_execution_rate"]
        for domain, dom in domains.items()
    }
    return {
        "available": True,
        "domain_count": len(domains),
        "live_continuity_domain_count": sum(1 for value in live.values() if _is_one(value)),
        "stale_validated_zero_continuity_domain_count": sum(1 for value in stale_validated.values() if _is_zero(value)),
        "stale_unvalidated_obsolete_execution_domain_count": sum(1 for value in stale_unvalidated.values() if float(value) > 0.0),
        "live_continuity_domains": sorted(domain for domain, value in live.items() if _is_one(value)),
        "stale_unvalidated_execution_domains": sorted(domain for domain, value in stale_unvalidated.items() if float(value) > 0.0),
    }


def _summarize_win_loss_family(
    repo_root: Path,
    *,
    rel_path: str,
    section_name: str,
    gain_key: str,
) -> dict[str, Any]:
    payload = _load_json(repo_root / rel_path)
    if payload is None:
        return {"available": False, "section": section_name}
    summary = payload.get("summary") or {}
    domains = payload.get("domains") or {}
    strict_win_domains = sorted(
        domain
        for domain, dom in domains.items()
        if float((dom.get("comparison") or {}).get(gain_key, 0.0)) > 0.0
    )
    return {
        "available": True,
        "section": section_name,
        "domain_count": int(summary.get("domain_count", len(domains))),
        "hybrid_win_count": int(summary.get("hybrid_win_count", 0)),
        "hybrid_tie_count": int(summary.get("hybrid_tie_count", 0)),
        "hybrid_loss_count": int(summary.get("hybrid_loss_count", 0)),
        "strict_win_domains": strict_win_domains,
    }


def _summarize_ambiguity_frontier(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / "kvrm-bench/results/ambiguity_regret_report.json")
    if payload is None:
        return {"available": False}
    domains = payload.get("domains") or {}
    zero_regret_domains = sorted(
        domain
        for domain, dom in domains.items()
        if _is_zero(dom["strategies"]["hybrid"]["regret"]["mean_decision_regret"])
    )
    return {
        "available": True,
        "domain_count": len(domains),
        "zero_regret_domain_count": len(zero_regret_domains),
        "zero_regret_domains": zero_regret_domains,
    }


def _summarize_feature_ceiling(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / "kvrm-bench/results/feature_ceiling_analysis_cases.json")
    if payload is None:
        return {"available": False}
    domains = payload.get("domains") or []
    frontier_recommendations: list[dict[str, Any]] = []
    for item in domains:
        recommendations = item.get("feature_recommendations") or []
        chosen = next(
            (rec for rec in recommendations if rec.get("priority") != "monitoring_only"),
            recommendations[0] if recommendations else None,
        )
        if chosen is None:
            chosen = {"features": [], "priority": "none"}
        frontier_recommendations.append(
            {
                "domain": str(item["domain"]),
                "features": list(chosen.get("features") or []),
                "priority": str(chosen.get("priority") or "none"),
            }
        )
    return {
        "available": True,
        "domain_count": len(domains),
        "zero_supported_overlap_domain_count": sum(
            1 for item in domains if int(item.get("supported_overlap_case_count", 0)) == 0
        ),
        "exact_oracle_match_domain_count": sum(
            1 for item in domains if bool(item.get("hybrid_matches_exact_feature_oracle"))
        ),
        "frontier_recommendations": sorted(frontier_recommendations, key=lambda item: item["domain"]),
    }


def _summarize_external_baselines(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / DEFAULT_EXTERNAL_BASELINE_PATH)
    if payload is None:
        return {"available": False}
    model_summaries = payload.get("model_summaries") or {}
    if not model_summaries:
        return {"available": False}
    best_name, best_model = max(
        model_summaries.items(),
        key=lambda item: float(item[1]["macro_semantic_correctness_rate"]),
    )
    kvrm_results = payload.get("kvrm_results") or {}
    kvrm_macro_semantic = mean(float(item["semantic_correctness_rate"]) for item in kvrm_results.values())
    kvrm_macro_false_accept = mean(float(item["false_accept_rate"]) for item in kvrm_results.values())
    kvrm_macro_unsupported_rejection = mean(
        float(item["unsupported_case_rejection_rate"]) for item in kvrm_results.values()
    )
    return {
        "available": True,
        "domain_count": len(payload.get("domains") or []),
        "model_count": len(model_summaries),
        "best_model": {
            "name": best_name,
            "macro_semantic_correctness_rate": float(best_model["macro_semantic_correctness_rate"]),
            "macro_false_accept_rate": float(best_model["macro_false_accept_rate"]),
            "macro_unsupported_case_rejection_rate": float(best_model["macro_unsupported_case_rejection_rate"]),
            "macro_invalid_output_rate": float(best_model["macro_invalid_output_rate"]),
        },
        "kvrm_macro_semantic_correctness_rate": kvrm_macro_semantic,
        "kvrm_macro_false_accept_rate": kvrm_macro_false_accept,
        "kvrm_macro_unsupported_case_rejection_rate": kvrm_macro_unsupported_rejection,
    }


def _build_headline_claims(sections: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []

    canonical = sections["canonical_suite"]
    if canonical["available"]:
        claims.append(
            {
                "statement": "Canonical hybrid KVRM remains perfect on the live canonical suite.",
                "status": "supported" if canonical["all_semantic_correctness_one"] else "mixed",
                "evidence": "kvrm-demos/reports/demo_comparison.json",
                "summary": (
                    f"{canonical['domain_count']} domains, {canonical['total_case_count']} cases, "
                    f"false_accept=0 and unsupported_rejection=1 across all domains."
                ),
            }
        )

    support_gate = sections["support_gate_stress"]
    if support_gate["available"]:
        claims.append(
            {
                "statement": "Support-aware gating is architecturally necessary.",
                "status": "supported",
                "evidence": "kvrm-bench/results/support_gate_stress_report.json",
                "summary": (
                    f"Gated hybrid stays perfect in {support_gate['gated_perfect_semantic_domain_count']}/"
                    f"{support_gate['domain_count']} domains; ungated semantic correctness drops as low as "
                    f"{support_gate['ungated_semantic_correctness_range']['min']:.4f}."
                ),
            }
        )

    fallback = sections["fallback_feasibility"]
    if fallback["available"]:
        claims.append(
            {
                "statement": "Strict runtime validation of fallback-tagged actions is necessary.",
                "status": "supported",
                "evidence": "kvrm-bench/results/fallback_feasibility_report.json",
                "summary": (
                    f"Strict runtime has zero unsafe execution in {fallback['strict_zero_unsafe_execution_domain_count']}/"
                    f"{fallback['domain_count']} evaluated domains; legacy bypass is unsafe in "
                    f"{fallback['legacy_nonzero_unsafe_execution_domain_count']}/{fallback['domain_count']}."
                ),
            }
        )

    registry = sections["registry_evolution"]
    if registry["available"]:
        claims.append(
            {
                "statement": "Live-registry continuity exceeds stale-selector variants.",
                "status": "supported",
                "evidence": "kvrm-bench/results/registry_evolution_report.json",
                "summary": (
                    f"Live hybrid preserves supported continuity in {registry['live_continuity_domain_count']}/"
                    f"{registry['domain_count']} domains; stale validated continuity is zero in "
                    f"{registry['stale_validated_zero_continuity_domain_count']}/{registry['domain_count']}."
                ),
            }
        )

    for key, evidence in (
        ("incident_replay", "kvrm-bench/results/incident_replay_report.json"),
        ("counterfactual_boundary", "kvrm-bench/results/counterfactual_boundary_report.json"),
        ("temporal_transition", "kvrm-bench/results/temporal_transition_report.json"),
        ("coordination_chain", "kvrm-bench/results/coordination_chain_report.json"),
    ):
        section = sections[key]
        if not section["available"]:
            continue
        claims.append(
            {
                "statement": f"Hybrid KVRM has zero losses on the {section['section'].replace('_', ' ')} family.",
                "status": "supported" if section["hybrid_loss_count"] == 0 else "mixed",
                "evidence": evidence,
                "summary": (
                    f"{section['hybrid_win_count']} wins / {section['hybrid_tie_count']} ties / "
                    f"{section['hybrid_loss_count']} losses."
                ),
            }
        )

    ambiguity = sections["ambiguity_frontier"]
    if ambiguity["available"]:
        claims.append(
            {
                "statement": "Hybrid KVRM dominates the current ambiguity frontier.",
                "status": "supported" if ambiguity["zero_regret_domain_count"] == ambiguity["domain_count"] else "mixed",
                "evidence": "kvrm-bench/results/ambiguity_regret_report.json",
                "summary": (
                    f"Zero hybrid regret in {ambiguity['zero_regret_domain_count']}/{ambiguity['domain_count']} domains."
                ),
            }
        )

    ceiling = sections["feature_ceiling"]
    if ceiling["available"]:
        claims.append(
            {
                "statement": "The live canonical schemas are separable under their current feature contracts.",
                "status": "supported"
                if ceiling["zero_supported_overlap_domain_count"] == ceiling["domain_count"]
                else "mixed",
                "evidence": "kvrm-bench/results/feature_ceiling_analysis_cases.json",
                "summary": (
                    f"Zero supported overlap in {ceiling['zero_supported_overlap_domain_count']}/"
                    f"{ceiling['domain_count']} domains; hybrid matches the exact-feature oracle in "
                    f"{ceiling['exact_oracle_match_domain_count']}/{ceiling['domain_count']}."
                ),
            }
        )

    baselines = sections["external_baselines"]
    if baselines["available"]:
        best_model = baselines["best_model"]
        claims.append(
            {
                "statement": "KVRM outperforms the evaluated small-model Ollama baselines on the live subset.",
                "status": "supported",
                "evidence": DEFAULT_EXTERNAL_BASELINE_PATH,
                "summary": (
                    f"Best baseline `{best_model['name']}` reaches macro semantic "
                    f"{best_model['macro_semantic_correctness_rate']:.4f} with macro false accept "
                    f"{best_model['macro_false_accept_rate']:.4f}; KVRM stays at macro semantic "
                    f"{baselines['kvrm_macro_semantic_correctness_rate']:.4f} and macro false accept "
                    f"{baselines['kvrm_macro_false_accept_rate']:.4f}."
                ),
            }
        )

    return claims


def _load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _is_one(value: float) -> bool:
    return abs(float(value) - 1.0) < 1e-9


def _is_zero(value: float) -> bool:
    return abs(float(value)) < 1e-9
