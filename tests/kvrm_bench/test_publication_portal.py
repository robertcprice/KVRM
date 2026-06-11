from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from kvrm_bench.paper_doc_audit import build_paper_doc_audit
from kvrm_bench.publication_bundle import build_publication_bundle
from kvrm_bench.publication_manuscript_packet import build_publication_manuscript_packet
from kvrm_bench.publication_paper_assets import (
    build_publication_paper_appendix,
    build_publication_paper_assets,
)
from kvrm_bench.publication_portal import build_publication_portal
from kvrm_bench.publication_submission_export import build_publication_submission_export_matrix
from kvrm_bench.publication_summary import build_publication_summary


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("pandoc") is None or shutil.which("pdflatex") is None, reason="pandoc/TeX missing")
def test_build_publication_portal_writes_bundle_landing_page(tmp_path: Path) -> None:
    bundle_payload = build_publication_bundle(REPO_ROOT, output_dir=tmp_path)
    summary_payload = build_publication_summary(REPO_ROOT, output_dir=tmp_path)
    paper_assets_payload = build_publication_paper_assets(
        REPO_ROOT,
        output_dir=tmp_path,
        summary=summary_payload["summary"],
    )
    appendix_docs_path = tmp_path / "docs" / "KVRM_PUBLICATION_APPENDIX.md"
    appendix_payload = build_publication_paper_appendix(
        REPO_ROOT,
        output_dir=tmp_path,
        docs_output_path=appendix_docs_path,
        summary=summary_payload["summary"],
        paper_assets=paper_assets_payload["assets"],
    )
    audit_payload = build_paper_doc_audit(REPO_ROOT, output_dir=tmp_path)
    manuscript_packet_payload = build_publication_manuscript_packet(REPO_ROOT, output_dir=tmp_path)
    submission_export_payload = build_publication_submission_export_matrix(REPO_ROOT, output_dir=tmp_path)

    result = build_publication_portal(
        REPO_ROOT,
        output_dir=tmp_path,
        manifest=bundle_payload["manifest"],
        summary=summary_payload["summary"],
        paper_assets=paper_assets_payload["assets"],
        paper_doc_audit=audit_payload["audit"],
        appendix_path=appendix_payload["path"],
        docs_appendix_path=appendix_payload["docs_path"],
        manuscript_packet_path=manuscript_packet_payload["readme_path"],
        submission_export_path=submission_export_payload["readme_path"],
    )

    json_path = Path(result["path"])
    markdown_path = Path(result["markdown_path"])
    readme_path = Path(result["readme_path"])
    assert json_path.exists()
    assert markdown_path.exists()
    assert readme_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["status"]["paper_doc_all_checks_passed"] is True
    assert payload["status"]["canonical_domain_count"] == 9
    assert any(item["path"] == "paper_doc_audit.md" for item in payload["bundle_files"])
    assert any(item["path"] == "docs/papers/README.md" for item in payload["docs_files"])

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# KVRM Publication Portal" in markdown
    audit_check_count = payload["status"]["paper_doc_check_count"]
    assert f"paper-doc audit: {audit_check_count}/{audit_check_count} checks passed" in markdown
    assert "- paper appendix: `paper_appendix.md`" in markdown
    assert "- manuscript packet: `manuscript/README.md`" in markdown
    assert "- submission export: `submission/README.md`" in markdown
    assert "- paper workflow README: `docs/papers/README.md`" in markdown
    assert "Canonical Seven-Domain Hybrid KVRM Results" in markdown
    assert readme_path.read_text(encoding="utf-8") == markdown
