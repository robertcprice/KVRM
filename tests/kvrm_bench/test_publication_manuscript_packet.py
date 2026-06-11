from __future__ import annotations

import json
from pathlib import Path

from kvrm_bench.publication_manuscript_packet import build_publication_manuscript_packet


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_publication_manuscript_packet_copies_expected_files(tmp_path: Path) -> None:
    _write(tmp_path / "docs" / "papers" / "KVRM_FLAGSHIP_PAPER_DRAFT.md", "# Draft\n")
    _write(tmp_path / "docs" / "papers" / "KVRM_PUBLICATION_APPENDIX.md", "# Appendix\n")
    _write(tmp_path / "docs" / "papers" / "kvrm_refs.bib", "@article{kvrm, title={KVRM}}\n")
    _write(tmp_path / "docs" / "papers" / "README.md", "# Workflow\n")
    _write(tmp_path / "docs" / "papers" / "KVRM_EVIDENCE_MATRIX.md", "# Evidence\n")
    _write(tmp_path / "docs" / "papers" / "KVRM_FIGURE_SOURCE_MAP.md", "# Figures\n")
    _write(tmp_path / "publication_summary.md", "# Summary\n")
    _write(tmp_path / "paper_tables.md", "# Tables\n")
    _write(tmp_path / "figure_captions.md", "# Captions\n")
    _write(tmp_path / "paper_doc_audit.md", "# Audit\n")

    result = build_publication_manuscript_packet(tmp_path, output_dir=tmp_path)

    json_path = Path(result["path"])
    markdown_path = Path(result["markdown_path"])
    readme_path = Path(result["readme_path"])
    packet_root = tmp_path / "manuscript"

    assert json_path.exists()
    assert markdown_path.exists()
    assert readme_path.exists()
    assert (packet_root / "KVRM_FLAGSHIP_PAPER_DRAFT.md").exists()
    assert (packet_root / "KVRM_PUBLICATION_APPENDIX.md").exists()
    assert (packet_root / "kvrm_refs.bib").exists()
    assert (packet_root / "PAPER_WORKFLOW.md").exists()
    assert (packet_root / "publication_summary.md").exists()
    assert (packet_root / "paper_doc_audit.md").exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["copied_file_count"] == payload["file_count"]
    assert payload["missing_file_count"] == 0
    assert any(item["packet_path"] == "manuscript/KVRM_FLAGSHIP_PAPER_DRAFT.md" for item in payload["files"])

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# KVRM Manuscript Packet" in markdown
    assert "manuscript/KVRM_FLAGSHIP_PAPER_DRAFT.md" in markdown
    assert "manuscript/paper_doc_audit.md" in markdown
    assert readme_path.read_text(encoding="utf-8") == markdown
