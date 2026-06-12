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
REPO_ROOT = PAPERS_DIR.parent.parent
DRAFT = PAPERS_DIR / "KVRM_FLAGSHIP_PAPER_DRAFT.md"
BIB = PAPERS_DIR / "kvrm_refs.bib"
FIGURES_SRC = REPO_ROOT / "docs" / "figures"
FIGURES_OUT = LATEX_DIR / "figures"
CAPTIONS_MD = (
    REPO_ROOT / "kvrm-bench" / "results" / "publication_bundle" / "figure_captions.md"
)

REPO_FACING_SECTIONS = ("## Artifact References", "## Bibliography Workflow")

# figure number -> (svg filename, section heading the figure follows)
FIGURE_PLACEMENT = {
    1: ("fig1_architecture.svg", "# 3. KVRM Architecture"),
    2: ("fig2_registry_lifecycle.svg", "# 3. KVRM Architecture"),
    3: ("fig3_supported_vs_unsupported.svg", "# 3. KVRM Architecture"),
    4: ("fig4_canonical_suite.svg", "# 6. Results on the Canonical Suite"),
    5: ("fig5_support_gate_stress.svg", "# 7. Support-Gate Stress and Strict Runtime Validation"),
    6: ("fig6_fallback_feasibility.svg", "# 7. Support-Gate Stress and Strict Runtime Validation"),
    7: ("fig7_robustness_families.svg", "# 8. Counterfactual, Temporal, and Coordination Robustness"),
}


def load_captions() -> dict[int, str]:
    """Parse the generated figure_captions.md into {figure_number: caption}."""
    if not CAPTIONS_MD.is_file():
        raise SystemExit(
            f"{CAPTIONS_MD} not found — run "
            "`python3 kvrm-bench/scripts/run_publication_bundle.py` first "
            "(figure captions are generated from live artifacts, never hand-written)"
        )
    captions: dict[int, str] = {}
    current: int | None = None
    body: list[str] = []
    for line in CAPTIONS_MD.read_text().splitlines():
        heading = re.match(r"^## Figure (\d+):", line)
        if heading:
            if current is not None:
                captions[current] = " ".join(body).strip()
            current = int(heading.group(1))
            body = []
        elif current is not None and line.strip() and not line.startswith(("File:", "Source:")):
            body.append(line.strip())
    if current is not None:
        captions[current] = " ".join(body).strip()
    return captions


def convert_figures() -> dict[int, Path]:
    """Convert the paper SVG figures to PDF for LaTeX inclusion."""
    FIGURES_OUT.mkdir(exist_ok=True)
    paths: dict[int, Path] = {}
    for number, (svg_name, _) in FIGURE_PLACEMENT.items():
        svg = FIGURES_SRC / svg_name
        if not svg.is_file():
            raise SystemExit(f"missing figure source: {svg}")
        pdf = FIGURES_OUT / svg.with_suffix(".pdf").name
        if not pdf.is_file() or pdf.stat().st_mtime < svg.stat().st_mtime:
            subprocess.run(
                ["rsvg-convert", "--format", "pdf", "--output", str(pdf), str(svg)],
                check=True,
            )
        paths[number] = pdf
    return paths


def insert_figures(body: str) -> str:
    """Insert pandoc figure blocks immediately after their anchor headings."""
    captions = load_captions()
    figure_paths = convert_figures()
    by_heading: dict[str, list[int]] = {}
    for number, (_, heading) in FIGURE_PLACEMENT.items():
        by_heading.setdefault(heading, []).append(number)

    lines = body.splitlines()
    output: list[str] = []
    for line in lines:
        output.append(line)
        numbers = by_heading.get(line.strip())
        if not numbers:
            continue
        for number in sorted(numbers):
            caption = captions.get(number)
            if not caption:
                raise SystemExit(f"no generated caption for figure {number}")
            output.append("")
            output.append(
                f"![{caption}]({figure_paths[number]}){{width=100%}}"
            )
        output.append("")
    return "\n".join(output)


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
    body = insert_figures(body)

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
