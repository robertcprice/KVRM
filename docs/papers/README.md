# Paper Workflow

This directory mixes hand-edited paper documents with generated publication artifacts. The key rule is simple:

- edit the draft, scaffold, evidence notes, and figure-source map by hand
- do not hand-edit the generated appendix
- do not duplicate benchmark tables in multiple manuscript docs when the generated appendix already carries them

## Canonical Generated Artifact

The canonical manuscript-facing generated snapshot is:

- `docs/papers/KVRM_PUBLICATION_APPENDIX.md`

It is refreshed from live benchmark artifacts by:

```bash
python3 kvrm-bench/scripts/run_publication_bundle.py
```

That command also regenerates the bundle-side copies under:

- `kvrm-bench/results/publication_bundle/publication_summary.md`
- `kvrm-bench/results/publication_bundle/paper_tables.md`
- `kvrm-bench/results/publication_bundle/figure_captions.md`
- `kvrm-bench/results/publication_bundle/paper_appendix.md`
- `kvrm-bench/results/publication_bundle/paper_doc_audit.md`
- `kvrm-bench/results/publication_bundle/publication_portal.md`
- `kvrm-bench/results/publication_bundle/README.md`
- `kvrm-bench/results/publication_bundle/manuscript/README.md`
- `kvrm-bench/results/publication_bundle/submission/README.md`

If you only want to audit manuscript-doc alignment without rebuilding the full bundle, use:

```bash
python3 kvrm-bench/scripts/run_paper_doc_audit.py
```

If you want a single publication-readiness command that refreshes the bundle, reruns the paper-doc audit, runs the publication-critical test suite, and records a readiness artifact, use:

```bash
python3 kvrm-bench/scripts/run_publication_check.py
```

That readiness pass writes:

- `kvrm-bench/results/publication_bundle/publication_check.md`

If you want a direct venue-export step from the manuscript packet, use:

```bash
python3 kvrm-bench/scripts/run_publication_submission_export.py
```

The bundle refresh writes a submission index plus both profile subdirectories:

- `kvrm-bench/results/publication_bundle/submission/README.md`
- `kvrm-bench/results/publication_bundle/submission/review-anonymous/README.md`
- `kvrm-bench/results/publication_bundle/submission/review-anonymous/paper.pdf`
- `kvrm-bench/results/publication_bundle/submission/review-anonymous/submission_bundle.zip`
- `kvrm-bench/results/publication_bundle/submission/working-manuscript/README.md`
- `kvrm-bench/results/publication_bundle/submission/working-manuscript/paper.pdf`
- `kvrm-bench/results/publication_bundle/submission/working-manuscript/submission_bundle.zip`

Profiles:

- `review-anonymous` is the default and strips repo-only workflow sections from the exported paper source before rendering.
- `working-manuscript` keeps the full manuscript text but still emits normalized `paper.*` / `appendix.*` submission filenames.

For a one-off direct export, `run_publication_submission_export.py` still writes the selected profile into `submission/` by default. Use `--all-profiles` when you want the same side-by-side layout that the full bundle emits.

## Hand-Edited Documents

These are the main paper-authoring docs:

- `docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md`
- `docs/papers/KVRM_FLAGSHIP_PAPER_SCAFFOLD.md`
- `docs/papers/KVRM_EVIDENCE_MATRIX.md`
- `docs/papers/KVRM_FIGURE_SOURCE_MAP.md`
- `docs/papers/kvrm_refs.bib`

## Editing Rules

- The flagship draft should reference Appendix Tables/Figures instead of copying large benchmark tables inline.
- The scaffold should stay aligned with the same appendix-backed workflow, even if it remains rougher than the draft.
- Literature references in the flagship draft should use bibliography keys from `docs/papers/kvrm_refs.bib` such as `[@scholak2021picard]` instead of a second hand-maintained references list.
- Figure-caption text should be treated as generated content derived from the bundle, not rewritten independently in multiple docs.
- If benchmark numbers change, regenerate the publication bundle first, then update prose around the generated appendix rather than manually patching table bodies.

## Verification

Paper-doc sync is checked by:

```bash
PYTHONPATH=kvrm-core/src:kvrm-bench/src:kvrm-demos/soc-playbook-router:kvrm-demos/sre-policy-router:kvrm-demos/drone-mission-router:kvrm-demos/grid-ops-router:kvrm-demos/finance-risk-router:kvrm-demos/medical-workflow-router:kvrm-demos/iam-access-router pytest tests/kvrm_bench/test_paper_docs_sync.py -q
```

The generated audit artifact is:

```bash
python3 kvrm-bench/scripts/run_paper_doc_audit.py
```

The one-command publication readiness artifact is:

```bash
python3 kvrm-bench/scripts/run_publication_check.py
```

## LaTeX / PDF Build

Generate the submission-facing LaTeX and PDF from the markdown draft:

```bash
python3 docs/papers/latex/build_paper.py        # writes paper.tex + paper.pdf
python3 docs/papers/latex/build_paper.py --no-pdf  # paper.tex only
```

Requires `pandoc` and `tectonic` (both available via Homebrew). The build
strips the repo-facing "Manuscript Status", "Artifact References", and
"Bibliography Workflow" sections and lifts the Abstract into a proper
`\begin{abstract}` block. Citations resolve against `kvrm_refs.bib` via
citeproc. Outputs are gitignored; the markdown draft remains the source of
truth.
