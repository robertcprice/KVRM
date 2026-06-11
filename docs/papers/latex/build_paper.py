#!/usr/bin/env python3
"""Build the arXiv-facing LaTeX/PDF from the markdown flagship draft.

Pipeline:
  1. Preprocess KVRM_FLAGSHIP_PAPER_DRAFT.md:
     - strip the repo-facing "Manuscript Status" block
     - lift the Abstract section into pandoc metadata (renders \\begin{abstract})
     - drop the repo-facing "Artifact References" and "Bibliography Workflow"
       tail sections
  2. pandoc -> paper.tex (citeproc against kvrm_refs.bib)
  3. tectonic -> paper.pdf

Usage: python3 docs/papers/latex/build_paper.py [--no-pdf]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PAPERS_DIR = Path(__file__).resolve().parent.parent
LATEX_DIR = Path(__file__).resolve().parent
DRAFT = PAPERS_DIR / "KVRM_FLAGSHIP_PAPER_DRAFT.md"
BIB = PAPERS_DIR / "kvrm_refs.bib"

REPO_FACING_SECTIONS = ("## Artifact References", "## Bibliography Workflow")


def preprocess(text: str) -> tuple[str, str, str]:
    """Return (title, abstract, body_markdown)."""
    title_match = re.match(r"^# (.+)$", text, flags=re.MULTILINE)
    if not title_match:
        raise SystemExit("draft has no top-level title")
    title = title_match.group(1).strip()

    abstract_match = re.search(
        r"^## Abstract\n(.*?)(?=^## )", text, flags=re.MULTILINE | re.DOTALL
    )
    if not abstract_match:
        raise SystemExit("draft has no '## Abstract' section")
    abstract = abstract_match.group(1).strip()

    body = text[abstract_match.end():]
    for marker in REPO_FACING_SECTIONS:
        idx = body.find(marker)
        if idx != -1:
            body = body[:idx]

    # Demote "## 5. Experimental Methodology" -> "# Experimental Methodology"
    # so pandoc emits \section{}; keep pandoc numbering off and reuse the
    # draft's manual numbers for stable cross-references in prose.
    body = re.sub(r"^## ", "# ", body, flags=re.MULTILINE)
    body = re.sub(r"^### ", "## ", body, flags=re.MULTILINE)
    return title, abstract, body.strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-pdf", action="store_true", help="stop after paper.tex")
    args = parser.parse_args()

    title, abstract, body = preprocess(DRAFT.read_text())

    metadata = {
        "title": title,
        "abstract": abstract,
        "author": ["Robert Price"],
        "date": r"\today",
        "documentclass": "article",
        "fontsize": "11pt",
        "geometry": "margin=1in",
        "link-citations": True,
        "colorlinks": True,
        "linkcolor": "blue",
        "urlcolor": "blue",
        "citecolor": "blue",
    }

    body_md = LATEX_DIR / "_paper_body.md"
    meta_json = LATEX_DIR / "_paper_meta.json"
    body_md.write_text(body)
    meta_json.write_text(json.dumps(metadata))

    tex_out = LATEX_DIR / "paper.tex"
    subprocess.run(
        [
            "pandoc",
            str(body_md),
            "--metadata-file", str(meta_json),
            "--from", "markdown",
            "--to", "latex",
            "--standalone",
            "--citeproc",
            "--bibliography", str(BIB),
            "--output", str(tex_out),
        ],
        check=True,
    )
    print(f"wrote {tex_out}")

    if not args.no_pdf:
        subprocess.run(
            ["tectonic", "--keep-logs", str(tex_out)],
            check=True,
            cwd=LATEX_DIR,
        )
        print(f"wrote {LATEX_DIR / 'paper.pdf'}")

    body_md.unlink()
    meta_json.unlink()


if __name__ == "__main__":
    main()
    sys.exit(0)
