# KVRM Pre-Submission Checklist

**Domain note.** The benchmark suite spans 12 domains, all in the canonical suite (682 cases). The original 7 "canonical" domains (SOC, SRE, drone, grid, finance, medical, IAM) additionally have full ceiling analysis, ambiguity-frontier, robustness-family, and registry-evolution coverage. The 5 later domains (customer_support, content_moderation, legal, cicd, insurance) participate in the canonical aggregate benchmarks; the external-baseline comparison covers an 8-domain subset (586 cases). Use "twelve domains" for canonical aggregate claims and "seven canonical domains" when citing ceiling, frontier, robustness-family, or evolution results.

---

## 1. Automated Checks

- [ ] Regenerate the publication bundle:
      `python3 kvrm-bench/scripts/run_publication_bundle.py`
- [ ] Run the full publication-readiness check (bundle + audit + tests + readiness artifact):
      `python3 kvrm-bench/scripts/run_publication_check.py`
- [ ] Confirm `all_checks_passed: true` in the JSON output.
- [ ] Run paper-doc sync tests:
      `PYTHONPATH=kvrm-core/src:kvrm-bench/src:kvrm-demos/soc-playbook-router:kvrm-demos/sre-policy-router:kvrm-demos/drone-mission-router:kvrm-demos/grid-ops-router:kvrm-demos/finance-risk-router:kvrm-demos/medical-workflow-router:kvrm-demos/iam-access-router pytest tests/kvrm_bench/test_paper_docs_sync.py -q`
- [ ] Run the paper-doc audit standalone and review warnings:
      `python3 kvrm-bench/scripts/run_paper_doc_audit.py`

## 2. Evidence Verification

- [ ] Spot-check that Tier 1 artifacts exist and are recent (not stale from a prior run):
      `ls -lt kvrm-bench/results/support_gate_stress_report.json kvrm-bench/results/fallback_feasibility_report.json kvrm-bench/results/registry_evolution_report.json kvrm-bench/results/counterfactual_boundary_report.json kvrm-bench/results/temporal_transition_report.json kvrm-bench/results/coordination_chain_report.json kvrm-bench/results/ambiguity_regret_report.json kvrm-bench/results/incident_replay_report.json`
- [ ] Verify canonical demo comparison is current:
      `ls -lt kvrm-demos/reports/demo_comparison.json`
- [ ] Confirm Tier 2 directories are populated:
      `ls kvrm-bench-results/adversarial_stress/ kvrm-bench-results/scale/ kvrm-bench-results/calibration/ kvrm-bench-results/generalization/ kvrm-bench-results/overlap_analysis/ kvrm-bench-results/shap/ kvrm-bench-results/interpretability/`
- [ ] Verify the generated appendix matches the bundle:
      `diff <(head -5 docs/papers/KVRM_PUBLICATION_APPENDIX.md) /dev/null || echo "appendix exists"`
- [ ] Confirm external baseline outputs exist:
      `ls baselines/qwen-baseline/outputs/ollama/live_canonical/consolidated_comparison.json`

## 3. Manuscript Review

- [ ] Every claim in `KVRM_EVIDENCE_MATRIX.md` marked "Supported" still has a valid artifact path.
- [ ] The one "Not yet supported" claim (production traffic validation) is not asserted in the draft.
- [ ] Figures 1-7 in `docs/figures/` exist and are referenced in the draft. Cross-check against `KVRM_FIGURE_SOURCE_MAP.md`.
- [ ] Benchmark numbers in prose match the generated appendix tables (do not hand-edit table bodies).
- [ ] The "9 domains / 7 canonical" distinction is used correctly throughout (see note at top).
- [ ] Bibliography keys in the draft match entries in `docs/papers/kvrm_refs.bib`.
- [ ] No stale claim from the scaffold survived into the draft without evidence backing.
- [ ] Limitations section honestly states: synthetic benchmarks, no shadow deployment, bounded external baselines.

## 4. Submission Mechanics

- [ ] Author names, affiliations, and ordering finalized.
- [ ] Acknowledgments and funding disclosures drafted.
- [ ] Venue formatting applied (page limits, font, margins, section numbering).
- [ ] Anonymization profile reviewed if double-blind:
      `python3 kvrm-bench/scripts/run_publication_submission_export.py --all-profiles`
- [ ] Supplementary material (appendix, code, data) packaged per venue requirements.
- [ ] Confirm submission bundle zips are fresh:
      `ls -lt kvrm-bench/results/publication_bundle/submission/review-anonymous/submission_bundle.zip kvrm-bench/results/publication_bundle/submission/working-manuscript/submission_bundle.zip`

## 5. Final Sanity

- [ ] Read the abstract aloud. Does it promise only what the evidence matrix supports?
- [ ] Read the conclusion. Does it match the evidence, not the aspirations?
- [ ] Grep the draft for dangling TODOs or placeholders: `grep -in 'TODO\|FIXME\|TBD\|XXX\|PLACEHOLDER' docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md`
- [ ] Have a second person read the abstract cold and summarize the contribution back to you.
- [ ] Confirm the paper does not overclaim superiority to "all LLM baselines" (only the evaluated Qwen/Gemma/Ollama set).
