from __future__ import annotations

import json
import sys
from pathlib import Path

from kvrm_bench.paper_doc_audit import build_paper_doc_audit
from kvrm_bench.publication_check import build_publication_check
from kvrm_bench.publication_bundle import build_publication_bundle
from kvrm_bench.publication_paper_assets import (
    build_publication_paper_appendix,
    build_publication_paper_assets,
)
from kvrm_bench.publication_summary import build_publication_summary


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_publication_check_records_command_results(tmp_path: Path) -> None:
    commands = [
        {
            "name": "ok",
            "description": "successful smoke command",
            "argv": [sys.executable, "-c", "print('ok')"],
        },
        {
            "name": "fail",
            "description": "failing smoke command",
            "argv": [sys.executable, "-c", "import sys; print('bad'); sys.exit(2)"],
        },
    ]

    result = build_publication_check(
        REPO_ROOT,
        output_dir=tmp_path,
        commands=commands,
        refresh_portal=False,
    )

    json_path = Path(result["path"])
    markdown_path = Path(result["markdown_path"])
    assert json_path.exists()
    assert markdown_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["all_checks_passed"] is False
    assert payload["passed_check_count"] == 1
    assert payload["failed_check_count"] == 1
    assert payload["portal_refreshed"] is False
    assert [item["name"] for item in payload["checks"]] == ["ok", "fail"]
    assert payload["checks"][0]["passed"] is True
    assert payload["checks"][1]["returncode"] == 2

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# KVRM Publication Check" in markdown
    assert "| Check | Status | Exit Code | Duration (s) | Description |" in markdown
    assert "successful smoke command" in markdown
    assert "failing smoke command" in markdown


def test_build_publication_check_refreshes_portal_when_bundle_artifacts_exist(tmp_path: Path) -> None:
    build_publication_bundle(REPO_ROOT, output_dir=tmp_path)
    summary_payload = build_publication_summary(REPO_ROOT, output_dir=tmp_path)
    paper_assets_payload = build_publication_paper_assets(
        REPO_ROOT,
        output_dir=tmp_path,
        summary=summary_payload["summary"],
    )
    build_publication_paper_appendix(
        REPO_ROOT,
        output_dir=tmp_path,
        docs_output_path=tmp_path / "docs" / "KVRM_PUBLICATION_APPENDIX.md",
        summary=summary_payload["summary"],
        paper_assets=paper_assets_payload["assets"],
    )
    build_paper_doc_audit(REPO_ROOT, output_dir=tmp_path)

    result = build_publication_check(
        REPO_ROOT,
        output_dir=tmp_path,
        commands=[
            {
                "name": "ok",
                "description": "successful smoke command",
                "argv": [sys.executable, "-c", "print('ok')"],
            }
        ],
    )

    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    assert payload["all_checks_passed"] is True
    assert payload["portal_refreshed"] is True

    portal_markdown = (tmp_path / "publication_portal.md").read_text(encoding="utf-8")
    assert "publication check: 1/1 checks passed" in portal_markdown
    assert "- publication check: `publication_check.md`" in portal_markdown
