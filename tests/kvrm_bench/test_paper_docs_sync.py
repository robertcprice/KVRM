from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_flagship_draft_uses_generated_appendix_as_canonical_table_source() -> None:
    draft_path = REPO_ROOT / "docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md"
    draft = draft_path.read_text(encoding="utf-8")

    assert "docs/papers/README.md" in draft
    assert "docs/papers/KVRM_PUBLICATION_APPENDIX.md" in draft
    assert "docs/papers/kvrm_refs.bib" in draft
    assert "artifact-anchored working manuscript" in draft
    assert "Appendix Table 1" in draft
    assert "Appendix Table 2" in draft
    assert "Appendix Table 3" in draft
    assert "Appendix Table 5" in draft
    assert "Appendix Table 6" in draft
    assert "[@scholak2021picard]" in draft
    assert "[@rebedea2023nemoguardrails]" in draft
    assert "[@hendrycks2017baseline; @liang2018odin; @ren2019likelihood]" in draft
    assert "[@lewis2020rag; @gao2024ragsurvey]" in draft
    assert "[@meyer1992designbycontract]" in draft
    assert "[@bartocci2018specification]" in draft
    assert "draft for internal revision" not in draft
    assert "prose-first draft; final citations and venue formatting still pending" not in draft
    assert "This draft supports five core claims." not in draft
    assert "Primary artifacts for this draft:" not in draft
    assert "## References (Working)" not in draft

    # The manuscript should not carry duplicated benchmark tables once the appendix is canonical.
    assert "| Domain  | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | Mean Cost |" not in draft
    assert "| Domain | Gated Semantic | Ungated Semantic | Gated Cost | Ungated Cost | Gated Rescue |" not in draft
    assert (
        "| Domain | Cases | Live Continuity | Stale Validated Continuity | "
        "Stale Unvalidated Obsolete Execution | Live Tight Reject | "
        "Stale Unvalidated Tight False Accept |"
    ) not in draft
    assert "| Benchmark Family | Win / Tie / Loss vs Best Non-Hybrid | Strict Hybrid-Win Domains |" not in draft


def test_scaffold_and_figure_map_reference_generated_appendix_workflow() -> None:
    scaffold = (REPO_ROOT / "docs/papers/KVRM_FLAGSHIP_PAPER_SCAFFOLD.md").read_text(encoding="utf-8")
    figure_map = (REPO_ROOT / "docs/papers/KVRM_FIGURE_SOURCE_MAP.md").read_text(encoding="utf-8")
    evidence_matrix = (REPO_ROOT / "docs/papers/KVRM_EVIDENCE_MATRIX.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "docs/papers/README.md").read_text(encoding="utf-8")
    bench_readme = (REPO_ROOT / "kvrm-bench/README.md").read_text(encoding="utf-8")

    assert "docs/papers/README.md" in scaffold
    assert "docs/papers/KVRM_PUBLICATION_APPENDIX.md" in scaffold
    assert "Tables 1-6" in scaffold
    assert "Appendix Table 1" in scaffold
    assert "Appendix Table 2" in scaffold
    assert "Appendix Table 3" in scaffold
    assert "Appendix Table 6" in scaffold
    assert "| Domain  | Total | Supported | Unsupported | Hybrid Semantic | False Accept | Unsupported Rejection | Invalid Output | Mean Cost |" not in scaffold
    assert "| Benchmark Slice | Gated Hybrid | Ungated/Post-hoc Baseline |" not in scaffold
    assert "| Domain | Cases | Strict Unsupported Unsafe Execution | Legacy Unsupported Unsafe Execution | Strict Mean Feasibility Cost | Legacy Mean Feasibility Cost |" not in scaffold
    assert "| Benchmark family | Win / Tie / Loss vs best non-hybrid | Strict hybrid-win domains |" not in scaffold
    assert "docs/papers/KVRM_PUBLICATION_APPENDIX.md" in figure_map
    assert "generated appendix/caption outputs" in figure_map
    assert "docs/papers/README.md" in evidence_matrix
    assert "docs/papers/KVRM_PUBLICATION_APPENDIX.md" in evidence_matrix
    assert "docs/papers/KVRM_PUBLICATION_APPENDIX.md" in readme
    assert "do not hand-edit the generated appendix" in readme
    assert "The flagship draft should reference Appendix Tables/Figures" in readme
    assert "docs/papers/kvrm_refs.bib" in readme
    assert "[@scholak2021picard]" in readme
    assert "kvrm-bench/results/publication_bundle/manuscript/README.md" in readme
    assert "kvrm-bench/results/publication_bundle/submission/README.md" in readme
    assert "kvrm-bench/results/publication_bundle/submission/review-anonymous/README.md" in readme
    assert "kvrm-bench/results/publication_bundle/submission/working-manuscript/README.md" in readme
    assert "python3 kvrm-bench/scripts/run_publication_submission_export.py" in readme
    assert "kvrm-bench/results/publication_bundle/submission/review-anonymous/submission_bundle.zip" in readme
    assert "kvrm-bench/results/publication_bundle/submission/working-manuscript/submission_bundle.zip" in readme
    assert "kvrm-bench/results/publication_bundle/publication_portal.md" in readme
    assert "kvrm-bench/results/publication_bundle/README.md" in readme
    assert "kvrm-bench/results/publication_bundle/publication_check.md" in readme
    assert "python3 kvrm-bench/scripts/run_paper_doc_audit.py" in readme
    assert "python3 kvrm-bench/scripts/run_publication_check.py" in readme
    assert "kvrm-bench/results/publication_bundle/manuscript/manifest.json" in bench_readme
    assert "kvrm-bench/results/publication_bundle/manuscript/README.md" in bench_readme
    assert "kvrm-bench/results/publication_bundle/submission/manifest.json" in bench_readme
    assert "kvrm-bench/results/publication_bundle/submission/review-anonymous/paper.pdf" in bench_readme
    assert "kvrm-bench/results/publication_bundle/submission/review-anonymous/submission_bundle.zip" in bench_readme
    assert "kvrm-bench/results/publication_bundle/submission/working-manuscript/paper.pdf" in bench_readme
    assert "kvrm-bench/results/publication_bundle/submission/working-manuscript/submission_bundle.zip" in bench_readme
    assert "python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_publication_submission_export.py" in bench_readme
    assert "kvrm-bench/results/publication_bundle/publication_check.json" in bench_readme
    assert "kvrm-bench/results/publication_bundle/publication_check.md" in bench_readme


def test_checked_in_publication_appendix_contains_current_core_sections() -> None:
    appendix = (REPO_ROOT / "docs/papers/KVRM_PUBLICATION_APPENDIX.md").read_text(encoding="utf-8")

    assert "# KVRM Publication Appendix" in appendix
    assert "## Headline Claims" in appendix
    assert "### Table 1. Canonical Seven-Domain Hybrid KVRM Results" in appendix
    assert "### Table 5. Evaluated Small-Model Ollama Baseline Comparison" in appendix
    assert "### Figure 7: Replay, counterfactual, temporal, and coordination robustness summary" in appendix
