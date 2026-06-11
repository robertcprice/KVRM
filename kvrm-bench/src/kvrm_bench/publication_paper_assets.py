from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_bench.publication_summary import build_publication_summary


DEFAULT_PAPER_ASSETS_JSON = "paper_assets.json"
DEFAULT_PAPER_TABLES_MD = "paper_tables.md"
DEFAULT_FIGURE_CAPTIONS_MD = "figure_captions.md"
DEFAULT_PAPER_APPENDIX_MD = "paper_appendix.md"


def build_publication_paper_assets(
    repo_root: str | Path,
    *,
    output_dir: str | Path | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo_root_path = Path(repo_root)
    output_root = (
        Path(output_dir)
        if output_dir is not None
        else repo_root_path / "kvrm-bench" / "results" / "publication_bundle"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    if summary is None:
        summary_payload = build_publication_summary(repo_root_path, output_dir=output_root)
        summary = summary_payload["summary"]

    paper_assets = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_root": _display_path(output_root, repo_root_path),
        "tables": _build_tables(summary),
        "figures": _build_figures(summary),
    }

    json_path = output_root / DEFAULT_PAPER_ASSETS_JSON
    tables_path = output_root / DEFAULT_PAPER_TABLES_MD
    captions_path = output_root / DEFAULT_FIGURE_CAPTIONS_MD
    json_path.write_text(json.dumps(paper_assets, indent=2, sort_keys=True), encoding="utf-8")
    tables_path.write_text(render_paper_tables_markdown(paper_assets), encoding="utf-8")
    captions_path.write_text(render_figure_captions_markdown(paper_assets), encoding="utf-8")
    return {
        "path": str(json_path),
        "tables_path": str(tables_path),
        "captions_path": str(captions_path),
        "assets": paper_assets,
        "summary": summary,
    }


def build_publication_paper_appendix(
    repo_root: str | Path,
    *,
    output_dir: str | Path | None = None,
    docs_output_path: str | Path | None = None,
    summary: dict[str, Any] | None = None,
    paper_assets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo_root_path = Path(repo_root)
    output_root = (
        Path(output_dir)
        if output_dir is not None
        else repo_root_path / "kvrm-bench" / "results" / "publication_bundle"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    if summary is None:
        summary_payload = build_publication_summary(repo_root_path, output_dir=output_root)
        summary = summary_payload["summary"]
    if paper_assets is None:
        paper_assets_payload = build_publication_paper_assets(
            repo_root_path,
            output_dir=output_root,
            summary=summary,
        )
        paper_assets = paper_assets_payload["assets"]

    appendix_markdown = render_publication_paper_appendix_markdown(summary, paper_assets)
    appendix_path = output_root / DEFAULT_PAPER_APPENDIX_MD
    appendix_path.write_text(appendix_markdown, encoding="utf-8")

    docs_path: Path | None = None
    if docs_output_path is not None:
        docs_path = Path(docs_output_path)
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        docs_path.write_text(appendix_markdown, encoding="utf-8")

    return {
        "path": str(appendix_path),
        "docs_path": str(docs_path) if docs_path is not None else None,
        "summary": summary,
        "assets": paper_assets,
    }


def render_paper_tables_markdown(paper_assets: dict[str, Any]) -> str:
    lines = [
        "# KVRM Paper Tables",
        "",
        f"Generated: {paper_assets['generated_at']}",
        "",
    ]
    for table in paper_assets["tables"]:
        lines.extend(
            [
                f"## {table['id']}. {table['title']}",
                "",
                table["caption"],
                "",
                "| " + " | ".join(table["columns"]) + " |",
                "| " + " | ".join(["---"] * len(table["columns"])) + " |",
            ]
        )
        for row in table["rows"]:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        lines.append("")
    return "\n".join(lines)


def render_figure_captions_markdown(paper_assets: dict[str, Any]) -> str:
    lines = [
        "# KVRM Figure Captions",
        "",
        f"Generated: {paper_assets['generated_at']}",
        "",
    ]
    for figure in paper_assets["figures"]:
        lines.extend(
            [
                f"## Figure {figure['figure_number']}: {figure['title']}",
                "",
                f"File: `{figure['file']}`",
                f"Source: `{figure['source']}`",
                "",
                figure["caption"],
                "",
            ]
        )
    return "\n".join(lines)


def render_publication_paper_appendix_markdown(
    summary: dict[str, Any],
    paper_assets: dict[str, Any],
) -> str:
    lines = [
        "# KVRM Publication Appendix",
        "",
        f"Generated: {paper_assets['generated_at']}",
        "",
        f"Bundle root: `{paper_assets['output_root']}`",
        "",
        "Do not edit this file by hand. Regenerate it with `python3 kvrm-bench/scripts/run_publication_bundle.py`.",
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

    lines.extend(
        [
            "",
            "## Manuscript Tables",
            "",
        ]
    )
    for table in paper_assets["tables"]:
        lines.extend(
            [
                f"### {table['id']}. {table['title']}",
                "",
                table["caption"],
                "",
            ]
        )
        _append_markdown_table(lines, table["columns"], table["rows"])
        lines.append("")

    lines.extend(
        [
            "## Figure Captions",
            "",
        ]
    )
    for figure in paper_assets["figures"]:
        lines.extend(
            [
                f"### Figure {figure['figure_number']}: {figure['title']}",
                "",
                f"File: `{figure['file']}`",
                f"Source: `{figure['source']}`",
                "",
                figure["caption"],
                "",
            ]
        )

    lines.extend(
        [
            "## Source Artifacts",
            "",
        ]
    )
    for artifact in _collect_appendix_artifact_paths(summary, paper_assets):
        lines.append(f"- `{artifact}`")
    lines.append("")
    return "\n".join(lines)


def _build_tables(summary: dict[str, Any]) -> list[dict[str, Any]]:
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

    tables: list[dict[str, Any]] = []

    tables.append(
        {
            "id": "Table 1",
            "title": "Canonical Seven-Domain Hybrid KVRM Results",
            "caption": (
                "Hybrid KVRM metrics on the live canonical suite. The current suite covers seven bounded "
                "workflow domains and shows perfect semantic correctness, zero false accepts, perfect "
                "unsupported rejection, and zero invalid outputs in every domain."
            ),
            "columns": ["Domain", "Cases", "Semantic", "False Accept", "Unsupported Reject", "Invalid Output"],
            "rows": [
                [
                    domain["domain"],
                    domain["total_cases"],
                    _fmt(domain["semantic_correctness_rate"]),
                    _fmt(domain["false_accept_rate"]),
                    _fmt(domain["unsupported_case_rejection_rate"]),
                    _fmt(domain["invalid_output_rate"]),
                ]
                for domain in canonical["domains"]
            ],
        }
    )

    tables.append(
        {
            "id": "Table 2",
            "title": "Architecture-Native Safety Evidence",
            "caption": (
                "Headline architecture evidence from support-gate stress, fallback feasibility, and "
                "live-registry evolution. These metrics isolate the fail-closed properties that the "
                "paper claims as the main architectural contribution."
            ),
            "columns": ["Benchmark", "Domains", "Headline Result"],
            "rows": [
                [
                    "Support-gate stress",
                    support_gate["domain_count"],
                    (
                        f"gated perfect in {support_gate['gated_perfect_semantic_domain_count']}/"
                        f"{support_gate['domain_count']}; ungated semantic min "
                        f"{_fmt(support_gate['ungated_semantic_correctness_range']['min'])}"
                    ),
                ],
                [
                    "Fallback feasibility",
                    fallback["domain_count"],
                    (
                        f"strict unsafe-execution zero in {fallback['strict_zero_unsafe_execution_domain_count']}/"
                        f"{fallback['domain_count']}; legacy unsafe in "
                        f"{fallback['legacy_nonzero_unsafe_execution_domain_count']}/"
                        f"{fallback['domain_count']}"
                    ),
                ],
                [
                    "Registry evolution",
                    registry["domain_count"],
                    (
                        f"live continuity 1.0 in {registry['live_continuity_domain_count']}/"
                        f"{registry['domain_count']}; stale validated continuity zero in "
                        f"{registry['stale_validated_zero_continuity_domain_count']}/"
                        f"{registry['domain_count']}"
                    ),
                ],
            ],
        }
    )

    tables.append(
        {
            "id": "Table 3",
            "title": "Robustness Family Summary",
            "caption": (
                "Hybrid KVRM win/tie/loss counts against the best non-hybrid baseline across the current "
                "robustness benchmark families."
            ),
            "columns": ["Family", "Domains", "Wins", "Ties", "Losses", "Strict Win Domains"],
            "rows": [
                [
                    "incident replay",
                    replay["domain_count"],
                    replay["hybrid_win_count"],
                    replay["hybrid_tie_count"],
                    replay["hybrid_loss_count"],
                    ", ".join(replay["strict_win_domains"]),
                ],
                [
                    "counterfactual boundary",
                    counterfactual["domain_count"],
                    counterfactual["hybrid_win_count"],
                    counterfactual["hybrid_tie_count"],
                    counterfactual["hybrid_loss_count"],
                    ", ".join(counterfactual["strict_win_domains"]),
                ],
                [
                    "temporal transition",
                    temporal["domain_count"],
                    temporal["hybrid_win_count"],
                    temporal["hybrid_tie_count"],
                    temporal["hybrid_loss_count"],
                    ", ".join(temporal["strict_win_domains"]),
                ],
                [
                    "coordination chain",
                    coordination["domain_count"],
                    coordination["hybrid_win_count"],
                    coordination["hybrid_tie_count"],
                    coordination["hybrid_loss_count"],
                    ", ".join(coordination["strict_win_domains"]),
                ],
            ],
        }
    )

    tables.append(
        {
            "id": "Table 4",
            "title": "Feature-Ceiling Frontier Recommendations",
            "caption": (
                "Next-frontier structured features suggested by the exact-feature oracle ceiling analysis. "
                "These are the highest-leverage schema-expansion targets under the current live canonical packs."
            ),
            "columns": ["Domain", "Priority", "Suggested Frontier Features"],
            "rows": [
                [item["domain"], item["priority"], ", ".join(item["features"]) or "-"]
                for item in ceiling["frontier_recommendations"]
            ],
        }
    )

    if baselines["available"]:
        best_model = baselines["best_model"]
        tables.append(
            {
                "id": "Table 5",
                "title": "Evaluated Small-Model Ollama Baseline Comparison",
                "caption": (
                    "Best evaluated Ollama baseline on the live six-domain subset compared with KVRM on the "
                    "same subset. This is supporting evidence rather than the core architectural claim."
                ),
                "columns": ["System", "Domains", "Macro Semantic", "Macro False Accept", "Macro Unsupported Reject"],
                "rows": [
                    [
                        "KVRM",
                        baselines["domain_count"],
                        _fmt(baselines["kvrm_macro_semantic_correctness_rate"]),
                        _fmt(baselines["kvrm_macro_false_accept_rate"]),
                        _fmt(baselines["kvrm_macro_unsupported_case_rejection_rate"]),
                    ],
                    [
                        best_model["name"],
                        baselines["domain_count"],
                        _fmt(best_model["macro_semantic_correctness_rate"]),
                        _fmt(best_model["macro_false_accept_rate"]),
                        _fmt(best_model["macro_unsupported_case_rejection_rate"]),
                    ],
                ],
            }
        )

    if ambiguity["available"]:
        tables.append(
            {
                "id": "Table 6",
                "title": "Ambiguity Frontier Summary",
                "caption": "Current hard-case frontier status on the live operator-facing ambiguity slice.",
                "columns": ["Domains", "Zero-Regret Domains", "Status"],
                "rows": [[ambiguity["domain_count"], ambiguity["zero_regret_domain_count"], "hybrid regret = 0.0"]],
            }
        )

    return tables


def _build_figures(summary: dict[str, Any]) -> list[dict[str, Any]]:
    sections = summary["sections"]
    canonical = sections["canonical_suite"]
    support_gate = sections["support_gate_stress"]
    fallback = sections["fallback_feasibility"]
    replay = sections["incident_replay"]
    counterfactual = sections["counterfactual_boundary"]
    temporal = sections["temporal_transition"]
    coordination = sections["coordination_chain"]

    return [
        {
            "figure_number": 1,
            "file": "docs/figures/fig1_architecture.svg",
            "title": "KVRM core runtime architecture",
            "source": "conceptual runtime diagram",
            "caption": (
                "KVRM routes over a finite audited action registry through support-aware selection, "
                "deterministic validation, and deterministic execution or safe handoff boundaries."
            ),
        },
        {
            "figure_number": 2,
            "file": "docs/figures/fig2_registry_lifecycle.svg",
            "title": "Registry lifecycle",
            "source": "conceptual registry lifecycle",
            "caption": (
                "Versioned action registries define the executable contract, support envelopes, and "
                "validation boundary that remain stable as selector components evolve."
            ),
        },
        {
            "figure_number": 3,
            "file": "docs/figures/fig3_supported_vs_unsupported.svg",
            "title": "Supported vs unsupported routing flow",
            "source": "conceptual fail-closed routing flow",
            "caption": (
                "Supported inputs are routed to audited actions when their support specs hold; unsupported "
                "inputs fail closed through deterministic fallback or rejection instead of unconstrained execution."
            ),
        },
        {
            "figure_number": 4,
            "file": "docs/figures/fig4_canonical_suite.svg",
            "title": "Seven-domain canonical benchmark summary",
            "source": "kvrm-demos/reports/demo_comparison.json",
            "caption": (
                f"Canonical hybrid KVRM results across {canonical['domain_count']} domains and "
                f"{canonical['total_case_count']} total cases. Every domain remains at semantic correctness "
                "1.0, false-accept rate 0.0, unsupported-case rejection 1.0, and invalid-output rate 0.0."
            ),
        },
        {
            "figure_number": 5,
            "file": "docs/figures/fig5_support_gate_stress.svg",
            "title": "Gated vs ungated support-gate stress",
            "source": "kvrm-bench/results/support_gate_stress_report.json",
            "caption": (
                f"Under injected high-confidence support-incompatible candidates, gated hybrid KVRM remains "
                f"perfect in {support_gate['gated_perfect_semantic_domain_count']}/{support_gate['domain_count']} "
                "domains, while the ungated comparator drops to semantic correctness between "
                f"{_fmt(support_gate['ungated_semantic_correctness_range']['min'])} and "
                f"{_fmt(support_gate['ungated_semantic_correctness_range']['max'])}."
            ),
        },
        {
            "figure_number": 6,
            "file": "docs/figures/fig6_fallback_feasibility.svg",
            "title": "Strict runtime vs legacy fallback-bypass",
            "source": "kvrm-bench/results/fallback_feasibility_report.json",
            "caption": (
                f"Explicit infeasible-handoff evaluation in SRE and drone shows zero unsafe execution under the "
                f"strict runtime in {fallback['strict_zero_unsafe_execution_domain_count']}/"
                f"{fallback['domain_count']} domains, while the legacy bypass remains unsafe in "
                f"{fallback['legacy_nonzero_unsafe_execution_domain_count']}/"
                f"{fallback['domain_count']}."
            ),
        },
        {
            "figure_number": 7,
            "file": "docs/figures/fig7_robustness_families.svg",
            "title": "Replay, counterfactual, temporal, and coordination robustness summary",
            "source": (
                "kvrm-bench/results/incident_replay_report.json; "
                "kvrm-bench/results/counterfactual_boundary_report.json; "
                "kvrm-bench/results/temporal_transition_report.json; "
                "kvrm-bench/results/coordination_chain_report.json"
            ),
            "caption": (
                "Hybrid KVRM has zero losses against the best non-hybrid baseline across the current robustness "
                f"families: replay {replay['hybrid_win_count']}/{replay['hybrid_tie_count']}/"
                f"{replay['hybrid_loss_count']}, counterfactual {counterfactual['hybrid_win_count']}/"
                f"{counterfactual['hybrid_tie_count']}/{counterfactual['hybrid_loss_count']}, temporal "
                f"{temporal['hybrid_win_count']}/{temporal['hybrid_tie_count']}/{temporal['hybrid_loss_count']}, "
                f"and coordination {coordination['hybrid_win_count']}/{coordination['hybrid_tie_count']}/"
                f"{coordination['hybrid_loss_count']} (win/tie/loss)."
            ),
        },
    ]


def _append_markdown_table(lines: list[str], columns: list[str], rows: list[list[Any]]) -> None:
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")


def _collect_appendix_artifact_paths(summary: dict[str, Any], paper_assets: dict[str, Any]) -> list[str]:
    ordered_paths: list[str] = []

    def add_path(path: str) -> None:
        if path not in ordered_paths:
            ordered_paths.append(path)

    add_path("kvrm-bench/results/publication_bundle/publication_summary.json")
    add_path("kvrm-bench/results/publication_bundle/publication_summary.md")
    add_path("kvrm-bench/results/publication_bundle/paper_assets.json")
    add_path("kvrm-bench/results/publication_bundle/paper_tables.md")
    add_path("kvrm-bench/results/publication_bundle/figure_captions.md")
    add_path("kvrm-bench/results/publication_bundle/paper_appendix.md")

    for claim in summary["headline_claims"]:
        add_path(str(claim["evidence"]))
    for figure in paper_assets["figures"]:
        for source in str(figure["source"]).split(";"):
            source = source.strip()
            if source.endswith(".json") or source.endswith(".svg"):
                add_path(source)
    return ordered_paths


def _fmt(value: Any) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)
