#!/usr/bin/env python3
"""Build an arXiv-style PDF preprint from the canonical markdown draft.

The canonical source of truth is KVRM_FLAGSHIP_PAPER_DRAFT.md. This script does
NOT mutate it; it produces a cleaned, citeproc-rendered PDF in build/.

Transformations (applied to a temp copy only):
  * strip the internal "Manuscript Status:" bullet block under the title
  * strip the trailing repo-internal sections ("Artifact References",
    "Bibliography Workflow") that are not paper content
  * prepend pandoc YAML metadata (title / author / date / abstract)
  * render with pandoc --citeproc against kvrm_refs.bib

Usage: python3 docs/papers/build_preprint.py
Requires: pandoc + a LaTeX engine (xelatex/pdflatex/tectonic).
"""
from __future__ import annotations

import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRAFT = HERE / "KVRM_FLAGSHIP_PAPER_DRAFT.md"
BIB = HERE / "kvrm_refs.bib"
BUILD = HERE.parent.parent / "build"
OUT_PDF = BUILD / "KVRM_preprint.pdf"

TITLE = "KVRM: Registry-Constrained Decision Architectures for Audited Finite Action Spaces"
# TODO(author): confirm name + affiliation before public release.
AUTHOR = "Robert C. Price"
AFFILIATION = "Independent Researcher"

# Sections that are repo-internal scaffolding, not paper content.
STRIP_FROM_HEADINGS = ("## Artifact References", "## Bibliography Workflow")


def clean_markdown(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    # Drop the title line (goes into YAML metadata) and the "Manuscript Status:"
    # bullet block that follows it, up to the first content heading.
    out: list[str] = []
    i = 0
    # skip leading title
    while i < len(lines) and not lines[i].startswith("# "):
        out.append(lines[i])
        i += 1
    if i < len(lines):
        i += 1  # consume "# Title"
    # skip the status block until the first "## " section
    while i < len(lines) and not lines[i].startswith("## "):
        i += 1
    body = lines[i:]

    # extract abstract section for YAML, drop it from the flow
    text2 = "\n".join(body)
    abstract = ""
    m = re.search(r"^## Abstract\s*\n(.*?)(?=^## )", text2, flags=re.S | re.M)
    if m:
        abstract = m.group(1).strip()
        text2 = text2[: m.start()] + text2[m.end():]

    # strip trailing internal sections
    for h in STRIP_FROM_HEADINGS:
        idx = text2.find("\n" + h)
        if idx != -1:
            # find the end of the doc or next top-level boundary after this heading
            text2 = text2[:idx]
    return text2.strip() + "\n", abstract


def main() -> int:
    if not shutil.which("pandoc"):
        print("pandoc not found", file=sys.stderr)
        return 2
    BUILD.mkdir(exist_ok=True)
    body, abstract = clean_markdown(DRAFT.read_text())
    today = datetime.date.today().isoformat()

    def yaml_block(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    meta = (
        "---\n"
        f'title: "{yaml_block(TITLE)}"\n'
        f'author: "{yaml_block(AUTHOR)}, {yaml_block(AFFILIATION)}"\n'
        f"date: {today}\n"
        f'abstract: "{yaml_block(abstract)}"\n'
        "geometry: margin=1in\n"
        "fontsize: 11pt\n"
        "numbersections: true\n"
        "link-citations: true\n"
        "---\n\n"
    )
    tmp = BUILD / "_preprint_src.md"
    tmp.write_text(meta + body)

    cmd = [
        "pandoc", str(tmp),
        "--citeproc", "--bibliography", str(BIB),
        "-N", "--toc",
        "-o", str(OUT_PDF),
    ]
    # prefer xelatex, fall back to default engine selection
    if shutil.which("xelatex"):
        cmd += ["--pdf-engine", "xelatex"]
    elif shutil.which("tectonic"):
        cmd += ["--pdf-engine", "tectonic"]
    print("running:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:], file=sys.stderr)
        print(r.stderr[-3000:], file=sys.stderr)
        return r.returncode
    size = OUT_PDF.stat().st_size
    print(f"wrote {OUT_PDF} ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
