from __future__ import annotations

import json
from pathlib import Path

from kvrm_bench.publication_bundle import build_publication_bundle


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_publication_bundle_copies_existing_artifacts_and_cleans_stale_outputs(tmp_path: Path) -> None:
    _write(tmp_path / "kvrm-demos" / "reports" / "demo_comparison.json", json.dumps({"demos": []}))
    _write(tmp_path / "kvrm-demos" / "reports" / "demo_comparison.md", "# Demo Comparison\n")
    _write(tmp_path / "kvrm-bench" / "results" / "support_gate_stress_report.json", json.dumps({"domains": {}}))
    _write(tmp_path / "kvrm-bench" / "results" / "support_gate_stress_report.md", "# Support Gate\n")
    _write(tmp_path / "kvrm-bench" / "results" / "finance_compact_training_report_v1.json", json.dumps({"domain": "finance"}))
    _write(tmp_path / "kvrm-bench" / "results" / "draft_exports" / "manifest.json", json.dumps({"export_count": 1}))
    _write(tmp_path / "kvrm-bench" / "results" / "draft_exports" / "manifest.md", "# Draft Manifest\n")
    _write(
        tmp_path / "kvrm-bench" / "results" / "draft_exports" / "finance" / "review" / "packet.json",
        json.dumps({"domain": "finance", "target": "review"}),
    )
    _write(
        tmp_path / "kvrm-bench" / "results" / "draft_exports" / "finance" / "review" / "packet.jsonl",
        json.dumps({"case_id": "finance_draft_001"}) + "\n",
    )
    _write(tmp_path / "docs" / "reports" / "KVRM_PUBLICATION_READINESS_2026-04-08.md", "# Readiness\n")
    _write(tmp_path / "docs" / "papers" / "KVRM_EVIDENCE_MATRIX.md", "# Evidence Matrix\n")
    _write(tmp_path / "docs" / "papers" / "KVRM_FLAGSHIP_PAPER_DRAFT.md", "# Paper Draft\n")
    _write(tmp_path / "docs" / "papers" / "KVRM_FLAGSHIP_PAPER_SCAFFOLD.md", "# Paper Scaffold\n")
    _write(tmp_path / "docs" / "papers" / "KVRM_FIGURE_SOURCE_MAP.md", "# Figure Sources\n")
    _write(tmp_path / "docs" / "papers" / "kvrm_refs.bib", "@article{kvrm, title={KVRM}}\n")
    _write(tmp_path / "docs" / "figures" / "generate_figures.py", "print('ok')\n")
    _write(tmp_path / "docs" / "figures" / "fig1_architecture.svg", "<svg></svg>\n")

    first = build_publication_bundle(tmp_path)
    bundle_root = Path(first["output_dir"])
    artifact_root = Path(first["artifact_root"])

    assert Path(first["manifest_path"]).exists()
    assert Path(first["markdown_path"]).exists()
    assert first["manifest"]["copied_artifact_count"] == 17
    assert first["manifest"]["missing_artifact_count"] > 0
    assert (artifact_root / "kvrm-demos" / "reports" / "demo_comparison.json").exists()
    assert (artifact_root / "kvrm-bench" / "results" / "draft_exports" / "finance" / "review" / "packet.jsonl").exists()
    assert (artifact_root / "docs" / "figures" / "fig1_architecture.svg").exists()

    stale_path = artifact_root / "stale.txt"
    stale_path.write_text("stale\n", encoding="utf-8")
    assert stale_path.exists()

    second = build_publication_bundle(tmp_path)
    assert Path(second["manifest_path"]).exists()
    assert not stale_path.exists()

    manifest = json.loads(Path(second["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["bundle_root"] == "kvrm-bench/results/publication_bundle"
    assert manifest["artifact_root"] == "kvrm-bench/results/publication_bundle/artifacts"
    assert manifest["copied_artifact_count"] == 17
    assert any(item["relative_path"] == "kvrm-demos/reports/demo_comparison.json" for item in manifest["artifacts"])
    assert any(
        item["relative_path"] == "kvrm-bench/results/draft_exports/finance/review/packet.jsonl"
        for item in manifest["artifacts"]
    )

    markdown = Path(second["markdown_path"]).read_text(encoding="utf-8")
    assert "# KVRM Publication Bundle" in markdown
    assert "| canonical_suite |" in markdown
    assert "`artifacts/kvrm-demos/reports/demo_comparison.json`" in markdown
