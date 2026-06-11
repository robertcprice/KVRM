from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pytest

from kvrm_bench.publication_submission_export import (
    build_publication_submission_export,
    build_publication_submission_export_matrix,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.skipif(shutil.which("pandoc") is None or shutil.which("pdflatex") is None, reason="pandoc/TeX missing")
def test_build_publication_submission_export_writes_tex_and_pdf(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    manuscript_root = bundle_root / "manuscript"
    _write(
        manuscript_root / "KVRM_FLAGSHIP_PAPER_DRAFT.md",
        (
            "# Test Manuscript\n\n"
            "Manuscript Status:\n"
            "- artifact-anchored working manuscript as of 2026-04-12\n"
            "- bibliography file: `docs/papers/kvrm_refs.bib`\n\n"
            "## Abstract\n\n"
            "Citation [@demo2026].\n\n"
            "## Artifact References\n\n"
            "- internal artifact\n\n"
            "## Bibliography Workflow\n\n"
            "workflow note\n"
        ),
    )
    _write(
        manuscript_root / "KVRM_PUBLICATION_APPENDIX.md",
        "# Test Appendix\n\nAppendix citation [@demo2026].\n",
    )
    _write(
        manuscript_root / "kvrm_refs.bib",
        "@article{demo2026,\n  author = {Doe, Jane},\n  title = {Demo Reference},\n  journal = {Demo Journal},\n  year = {2026}\n}\n",
    )

    result = build_publication_submission_export(tmp_path, output_dir=bundle_root)

    json_path = Path(result["path"])
    markdown_path = Path(result["markdown_path"])
    readme_path = Path(result["readme_path"])
    submission_root = bundle_root / "submission"

    assert json_path.exists()
    assert markdown_path.exists()
    assert readme_path.exists()
    assert (submission_root / "paper.md").exists()
    assert (submission_root / "paper.tex").exists()
    assert (submission_root / "paper.pdf").exists()
    assert (submission_root / "appendix.md").exists()
    assert (submission_root / "appendix.tex").exists()
    assert (submission_root / "appendix.pdf").exists()
    assert (submission_root / "references.bib").exists()
    assert (submission_root / "submission_bundle.zip").exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["all_exports_succeeded"] is True
    assert payload["profile"] == "review-anonymous"
    assert payload["all_pdf_authors_blank"] is True
    assert len(payload["commands"]) == 4
    assert all(item["passed"] for item in payload["commands"])
    assert any(item["label"] == "paper.pdf" and item["exists"] for item in payload["generated_files"])
    assert any(item["label"] == "paper" and item["submission_path"].endswith("/submission/paper.md") for item in payload["source_files"])
    assert payload["bundle_zip_path"].endswith("/submission/submission_bundle.zip")
    assert any((item.get("pdf_metadata") or {}).get("Author", "") == "" for item in payload["generated_files"] if item["label"] == "paper.pdf")

    paper_source = (submission_root / "paper.md").read_text(encoding="utf-8")
    assert paper_source.startswith('---\ntitle: "Test Manuscript"\nauthor: ""\ndate: ""\n---\n\n')
    assert "Manuscript Status:" not in paper_source
    assert "## Artifact References" not in paper_source
    assert "## Bibliography Workflow" not in paper_source
    assert "# Abstract" in paper_source
    assert "Citation [@demo2026]." in paper_source
    assert "# Test Manuscript" not in paper_source

    with zipfile.ZipFile(submission_root / "submission_bundle.zip") as archive:
        names = set(archive.namelist())
    assert {"paper.md", "paper.pdf", "appendix.pdf", "references.bib"}.issubset(names)

    paper_tex = (submission_root / "paper.tex").read_text(encoding="utf-8")
    assert "\\title{Test Manuscript}" in paper_tex
    assert "\\maketitle" in paper_tex
    assert "\\section{Abstract}" in paper_tex

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# KVRM Submission Export" in markdown
    assert "Profile: `review-anonymous`" in markdown
    assert "paper.pdf" in markdown
    assert "appendix.pdf" in markdown
    assert "use a real title block" in markdown
    assert "The anonymous review profile strips repo-only workflow sections" in markdown
    assert "Submission bundle zip" in markdown
    assert readme_path.read_text(encoding="utf-8") == markdown


@pytest.mark.skipif(shutil.which("pandoc") is None or shutil.which("pdflatex") is None, reason="pandoc/TeX missing")
def test_build_publication_submission_export_matrix_writes_profile_index(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    manuscript_root = bundle_root / "manuscript"
    _write(
        manuscript_root / "KVRM_FLAGSHIP_PAPER_DRAFT.md",
        (
            "# Test Manuscript\n\n"
            "Manuscript Status:\n"
            "- artifact-anchored working manuscript as of 2026-04-12\n"
            "- bibliography file: `docs/papers/kvrm_refs.bib`\n\n"
            "## Abstract\n\n"
            "Citation [@demo2026].\n"
        ),
    )
    _write(
        manuscript_root / "KVRM_PUBLICATION_APPENDIX.md",
        "# Test Appendix\n\nAppendix citation [@demo2026].\n",
    )
    _write(
        manuscript_root / "kvrm_refs.bib",
        "@article{demo2026,\n  author = {Doe, Jane},\n  title = {Demo Reference},\n  journal = {Demo Journal},\n  year = {2026}\n}\n",
    )

    result = build_publication_submission_export_matrix(tmp_path, output_dir=bundle_root)

    submission_root = bundle_root / "submission"
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    assert payload["profile_count"] == 2
    assert payload["all_exports_succeeded"] is True
    assert payload["all_pdf_authors_blank"] is True
    assert {item["profile"] for item in payload["profiles"]} == {"review-anonymous", "working-manuscript"}
    assert (submission_root / "review-anonymous" / "paper.pdf").exists()
    assert (submission_root / "working-manuscript" / "paper.pdf").exists()

    review_source = (submission_root / "review-anonymous" / "paper.md").read_text(encoding="utf-8")
    working_source = (submission_root / "working-manuscript" / "paper.md").read_text(encoding="utf-8")
    assert "Manuscript Status:" not in review_source
    assert "Manuscript Status:" in working_source

    markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
    assert "# KVRM Submission Export Matrix" in markdown
    assert "review-anonymous/README.md" in markdown
    assert "working-manuscript/README.md" in markdown
