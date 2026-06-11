from __future__ import annotations

import json
from pathlib import Path

from kvrm_bench.paper_doc_audit import build_paper_doc_audit


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_paper_doc_audit_writes_expected_outputs(tmp_path: Path) -> None:
    result = build_paper_doc_audit(REPO_ROOT, output_dir=tmp_path)

    json_path = Path(result["path"])
    markdown_path = Path(result["markdown_path"])

    assert json_path.exists()
    assert markdown_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["all_checks_passed"] is True
    assert len(payload["checks"]) >= 10

    check_names = {item["name"] for item in payload["checks"]}
    assert "draft duplicate benchmark tables absent" in check_names
    assert "draft internal-only markers absent" in check_names
    assert "draft citekeys present" in check_names
    assert "draft citekeys resolve in bibliography" in check_names
    assert "draft duplicate references block absent" in check_names
    assert "scaffold duplicate benchmark tables absent" in check_names
    assert "paper README documents generated appendix rules" in check_names

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# KVRM Paper Doc Audit" in markdown
    assert "| Check | Status | Details |" in markdown
    assert "draft duplicate benchmark tables absent" in markdown
    assert "draft internal-only markers absent" in markdown
    assert "draft citekeys resolve in bibliography" in markdown
    assert "paper README documents generated appendix rules" in markdown
