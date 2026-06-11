from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PUBLICATION_BUNDLE_DIRNAME = "publication_bundle"
PUBLICATION_BUNDLE_MANIFEST_JSON = "manifest.json"
PUBLICATION_BUNDLE_MANIFEST_MD = "manifest.md"

_EXPLICIT_ARTIFACTS: tuple[tuple[str, str, str], ...] = (
    ("canonical_suite", "demo comparison json", "kvrm-demos/reports/demo_comparison.json"),
    ("canonical_suite", "demo comparison markdown", "kvrm-demos/reports/demo_comparison.md"),
    ("architecture_benchmarks", "support gate stress json", "kvrm-bench/results/support_gate_stress_report.json"),
    ("architecture_benchmarks", "support gate stress markdown", "kvrm-bench/results/support_gate_stress_report.md"),
    ("architecture_benchmarks", "fallback feasibility json", "kvrm-bench/results/fallback_feasibility_report.json"),
    ("architecture_benchmarks", "fallback feasibility markdown", "kvrm-bench/results/fallback_feasibility_report.md"),
    ("architecture_benchmarks", "fallback feasibility cases", "kvrm-bench/results/fallback_feasibility_cases.json"),
    ("architecture_benchmarks", "registry evolution json", "kvrm-bench/results/registry_evolution_report.json"),
    ("architecture_benchmarks", "registry evolution markdown", "kvrm-bench/results/registry_evolution_report.md"),
    ("architecture_benchmarks", "registry evolution cases", "kvrm-bench/results/registry_evolution_cases.json"),
    ("architecture_benchmarks", "incident replay json", "kvrm-bench/results/incident_replay_report.json"),
    ("architecture_benchmarks", "incident replay markdown", "kvrm-bench/results/incident_replay_report.md"),
    ("architecture_benchmarks", "incident replay episodes", "kvrm-bench/results/incident_replay_episodes.json"),
    ("architecture_benchmarks", "counterfactual boundary json", "kvrm-bench/results/counterfactual_boundary_report.json"),
    ("architecture_benchmarks", "counterfactual boundary markdown", "kvrm-bench/results/counterfactual_boundary_report.md"),
    ("architecture_benchmarks", "counterfactual boundary cases", "kvrm-bench/results/counterfactual_boundary_cases.json"),
    ("architecture_benchmarks", "ambiguity regret json", "kvrm-bench/results/ambiguity_regret_report.json"),
    ("architecture_benchmarks", "ambiguity regret markdown", "kvrm-bench/results/ambiguity_regret_report.md"),
    ("architecture_benchmarks", "temporal transition json", "kvrm-bench/results/temporal_transition_report.json"),
    ("architecture_benchmarks", "temporal transition markdown", "kvrm-bench/results/temporal_transition_report.md"),
    ("architecture_benchmarks", "temporal transition sequences", "kvrm-bench/results/temporal_transition_sequences.json"),
    ("architecture_benchmarks", "coordination chain json", "kvrm-bench/results/coordination_chain_report.json"),
    ("architecture_benchmarks", "coordination chain markdown", "kvrm-bench/results/coordination_chain_report.md"),
    ("architecture_benchmarks", "coordination chain sequences", "kvrm-bench/results/coordination_chain_sequences.json"),
    ("architecture_benchmarks", "feature ceiling analysis json", "kvrm-bench/results/feature_ceiling_analysis_cases.json"),
    ("architecture_benchmarks", "feature ceiling analysis markdown", "kvrm-bench/results/feature_ceiling_analysis_cases.md"),
    ("draft_audit", "draft export manifest json", "kvrm-bench/results/draft_exports/manifest.json"),
    ("draft_audit", "draft export manifest markdown", "kvrm-bench/results/draft_exports/manifest.md"),
    ("paper_docs", "publication readiness notes", "docs/reports/KVRM_PUBLICATION_READINESS_2026-04-08.md"),
    ("paper_docs", "flagship paper draft", "docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md"),
    ("paper_docs", "flagship paper scaffold", "docs/papers/KVRM_FLAGSHIP_PAPER_SCAFFOLD.md"),
    ("paper_docs", "evidence matrix", "docs/papers/KVRM_EVIDENCE_MATRIX.md"),
    ("paper_docs", "figure source map", "docs/papers/KVRM_FIGURE_SOURCE_MAP.md"),
    ("paper_docs", "references bib", "docs/papers/kvrm_refs.bib"),
    ("figures", "figure generator", "docs/figures/generate_figures.py"),
)

_GLOB_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("training_reports", "kvrm-bench/results/*_compact_training_report_v1.json"),
    ("draft_audit", "kvrm-bench/results/draft_exports/**/*.json"),
    ("draft_audit", "kvrm-bench/results/draft_exports/**/*.jsonl"),
    ("figures", "docs/figures/*.svg"),
)

_GROUP_ORDER = (
    "canonical_suite",
    "architecture_benchmarks",
    "training_reports",
    "draft_audit",
    "paper_docs",
    "figures",
)


def build_publication_bundle(
    repo_root: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root_path = Path(repo_root)
    output_root = Path(output_dir) if output_dir is not None else _publication_bundle_root(repo_root_path)
    artifact_root = output_root / "artifacts"

    artifacts = collect_publication_artifacts(repo_root_path)
    shutil.rmtree(artifact_root, ignore_errors=True)
    artifact_root.mkdir(parents=True, exist_ok=True)

    copied_count = 0
    copied_bytes = 0
    group_copied_counts: Counter[str] = Counter()

    for artifact in artifacts:
        if not artifact["exists"]:
            continue
        source_path = repo_root_path / artifact["relative_path"]
        bundle_relative_path = Path("artifacts") / artifact["relative_path"]
        target_path = output_root / bundle_relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        artifact["bundle_path"] = str(bundle_relative_path)
        copied_count += 1
        copied_bytes += int(artifact["size_bytes"] or 0)
        group_copied_counts[str(artifact["group"])] += 1

    group_counts: Counter[str] = Counter()
    group_missing_counts: Counter[str] = Counter()
    for artifact in artifacts:
        group_counts[str(artifact["group"])] += 1
        if not artifact["exists"]:
            group_missing_counts[str(artifact["group"])] += 1

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_root": _display_path(output_root, repo_root_path),
        "artifact_root": _display_path(artifact_root, repo_root_path),
        "artifact_count": len(artifacts),
        "copied_artifact_count": copied_count,
        "missing_artifact_count": sum(1 for artifact in artifacts if not artifact["exists"]),
        "copied_bytes": copied_bytes,
        "groups": [
            {
                "group": group,
                "artifact_count": group_counts[group],
                "copied_count": group_copied_counts[group],
                "missing_count": group_missing_counts[group],
            }
            for group in _GROUP_ORDER
            if group_counts[group] > 0
        ],
        "artifacts": artifacts,
    }

    manifest_path = output_root / PUBLICATION_BUNDLE_MANIFEST_JSON
    markdown_path = output_root / PUBLICATION_BUNDLE_MANIFEST_MD
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_publication_bundle_markdown(manifest), encoding="utf-8")
    return {
        "output_dir": str(output_root),
        "artifact_root": str(artifact_root),
        "manifest_path": str(manifest_path),
        "markdown_path": str(markdown_path),
        "manifest": manifest,
    }


def collect_publication_artifacts(repo_root: str | Path) -> list[dict[str, Any]]:
    repo_root_path = Path(repo_root)
    artifacts: list[dict[str, Any]] = []
    seen_relative_paths: set[str] = set()

    for group, label, relative_path in _EXPLICIT_ARTIFACTS:
        artifacts.append(_artifact_record(repo_root_path, relative_path, group, label))
        seen_relative_paths.add(relative_path)

    for group, pattern in _GLOB_ARTIFACTS:
        for source_path in sorted(repo_root_path.glob(pattern)):
            if not source_path.is_file():
                continue
            relative_path = str(source_path.relative_to(repo_root_path))
            if relative_path in seen_relative_paths:
                continue
            artifacts.append(_artifact_record(repo_root_path, relative_path, group, source_path.name))
            seen_relative_paths.add(relative_path)

    artifacts.sort(key=lambda item: (_GROUP_ORDER.index(str(item["group"])), str(item["relative_path"])))
    return artifacts


def render_publication_bundle_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# KVRM Publication Bundle",
        "",
        f"Generated: {manifest['generated_at']}",
        "",
        f"Bundle root: `{manifest['bundle_root']}`",
        f"Artifact root: `{manifest['artifact_root']}`",
        "",
        (
            "This bundle copies the current publication-facing benchmark, audit, paper, and figure "
            "artifacts into one deterministic tree so the evidence set can be handed off or cited "
            "without walking multiple repo directories."
        ),
        "",
        f"Artifact count: {manifest['artifact_count']}",
        f"Copied artifacts: {manifest['copied_artifact_count']}",
        f"Missing artifacts: {manifest['missing_artifact_count']}",
        f"Copied bytes: {manifest['copied_bytes']}",
        "",
        "## Group Summary",
        "",
        "| Group | Artifacts | Copied | Missing |",
        "| --- | ---: | ---: | ---: |",
    ]

    for group in manifest.get("groups") or []:
        lines.append(
            f"| {group['group']} | {group['artifact_count']} | {group['copied_count']} | {group['missing_count']} |"
        )

    artifact_groups: dict[str, list[dict[str, Any]]] = {}
    for artifact in manifest.get("artifacts") or []:
        artifact_groups.setdefault(str(artifact["group"]), []).append(artifact)

    for group_name in _GROUP_ORDER:
        group_artifacts = artifact_groups.get(group_name)
        if not group_artifacts:
            continue
        lines.extend(
            [
                "",
                f"## {group_name}",
                "",
                "| Label | Source | Status | Bundle Path | Size |",
                "| --- | --- | --- | --- | ---: |",
            ]
        )
        for artifact in group_artifacts:
            status = "copied" if artifact["exists"] else "missing"
            bundle_path = f"`{artifact['bundle_path']}`" if artifact.get("bundle_path") else "-"
            size_bytes = int(artifact["size_bytes"] or 0)
            lines.append(
                "| "
                f"{artifact['label']} | "
                f"`{artifact['relative_path']}` | "
                f"{status} | "
                f"{bundle_path} | "
                f"{size_bytes} |"
            )

    lines.append("")
    return "\n".join(lines)


def _artifact_record(
    repo_root: Path,
    relative_path: str,
    group: str,
    label: str,
) -> dict[str, Any]:
    source_path = repo_root / relative_path
    exists = source_path.is_file()
    size_bytes = source_path.stat().st_size if exists else None
    modified_at = (
        datetime.fromtimestamp(source_path.stat().st_mtime, tz=timezone.utc).isoformat()
        if exists
        else None
    )
    sha256 = _sha256_file(source_path) if exists else None
    return {
        "group": group,
        "label": label,
        "relative_path": relative_path,
        "exists": exists,
        "size_bytes": size_bytes,
        "modified_at": modified_at,
        "sha256": sha256,
    }


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _publication_bundle_root(repo_root: Path) -> Path:
    return repo_root / "kvrm-bench" / "results" / DEFAULT_PUBLICATION_BUNDLE_DIRNAME


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
