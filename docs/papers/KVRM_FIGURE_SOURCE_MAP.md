# KVRM Figure Source Map

Status:
- working note for paper production
- maps figure names to concrete source artifacts and generator inputs

## Purpose

The current paper draft references a newer figure set than the historical classifier-era SVGs already present under `docs/figures/`.

This file makes the figure pipeline explicit:
- which figures already exist and can still be used
- which figures should be generated from the live seven-domain internal artifacts plus the six-domain external-baseline subset
- which JSON fields should be treated as the source of truth
- where the generated manuscript-facing caption snapshot now lives (`docs/papers/KVRM_PUBLICATION_APPENDIX.md`)

## Figure Plan

### Figure 1

- File: `docs/figures/fig1_architecture.svg`
- Title: `KVRM core runtime architecture`
- Status: existing and still usable
- Source: conceptual diagram from `kvrm-core` runtime structure

### Figure 2

- File: `docs/figures/fig2_registry_lifecycle.svg`
- Title: `Registry lifecycle`
- Status: existing and still usable
- Source: conceptual registry/version/hash/validation flow

### Figure 3

- File: `docs/figures/fig3_supported_vs_unsupported.svg`
- Title: `Supported vs unsupported routing flow`
- Status: existing and still usable
- Source: conceptual fail-closed routing flow

### Figure 4

- File: `docs/figures/fig4_canonical_suite.svg`
- Title: `Seven-domain canonical benchmark summary`
- Status: generate from live artifacts
- Primary source:
  - `kvrm-demos/reports/demo_comparison.json`
- Required fields per domain:
  - `total_cases`
  - `supported_cases`
  - `unsupported_cases`
  - `semantic_correctness_rate`
  - `false_accept_rate`
  - `unsupported_case_rejection_rate`
  - `invalid_output_rate`
  - `mean_decision_cost`
- Domains:
  - `soc_hybrid`
  - `sre_hybrid`
  - `drone_hybrid`
  - `grid_hybrid`
  - `finance_hybrid`
  - `medical_hybrid`
  - `iam_hybrid`

### Figure 5

- File: `docs/figures/fig5_support_gate_stress.svg`
- Title: `Gated vs ungated support-gate stress`
- Status: generate from live artifacts
- Primary source:
  - `kvrm-bench/results/support_gate_stress_report.json`
- Required fields per domain:
  - `domains.<domain>.gated.metrics.semantic_correctness_rate`
  - `domains.<domain>.ungated.metrics.semantic_correctness_rate`
  - `domains.<domain>.gated.metrics.mean_decision_cost`
  - `domains.<domain>.ungated.metrics.mean_decision_cost`
  - `domains.<domain>.comparison.supported_support_gate_rescue_gain`

### Figure 6

- File: `docs/figures/fig6_fallback_feasibility.svg`
- Title: `Strict runtime vs legacy fallback-bypass`
- Status: generate from live artifacts
- Primary source:
  - `kvrm-bench/results/fallback_feasibility_report.json`
- Required fields:
  - `domains.sre.variants.strict.feasibility_metrics.unsupported_unsafe_execution_rate`
  - `domains.sre.variants.legacy_bypass.feasibility_metrics.unsupported_unsafe_execution_rate`
  - `domains.drone.variants.strict.feasibility_metrics.unsupported_unsafe_execution_rate`
  - `domains.drone.variants.legacy_bypass.feasibility_metrics.unsupported_unsafe_execution_rate`
  - `domains.sre.generated_case_count`
  - `domains.drone.generated_case_count`
  - `domains.sre.variants.strict.feasibility_metrics.mean_feasibility_cost`
  - `domains.sre.variants.legacy_bypass.feasibility_metrics.mean_feasibility_cost`
  - `domains.drone.variants.strict.feasibility_metrics.mean_feasibility_cost`
  - `domains.drone.variants.legacy_bypass.feasibility_metrics.mean_feasibility_cost`

### Figure 7

- File: `docs/figures/fig7_robustness_families.svg`
- Title: `Counterfactual, temporal, and coordination robustness summary`
- Status: generate from live artifacts
- Primary sources:
  - `kvrm-bench/results/counterfactual_boundary_report.json`
  - `kvrm-bench/results/temporal_transition_report.json`
  - `kvrm-bench/results/coordination_chain_report.json`
- Required fields:
  - `summary.hybrid_win_count`
  - `summary.hybrid_tie_count`
  - `summary.hybrid_loss_count`
  - representative gains from `domains.sre.comparison` and `domains.drone.comparison`

## Historical Figures

These older SVGs are still present but are not the preferred figures for the current draft:
- `docs/figures/fig4_per_domain_accuracy.svg`
- `docs/figures/fig5_false_accept_rate.svg`
- `docs/figures/fig6_registry_evolution.svg`
- `docs/figures/fig7_architecture_comparison.svg`

They reflect the earlier three-domain proxy-baseline phase rather than the live seven-domain internal artifact set.

## Generation Note

`docs/figures/generate_figures.py` now generates the current draft figure names directly from the live JSON artifacts:
- `fig4_canonical_suite.svg`
- `fig5_support_gate_stress.svg`
- `fig6_fallback_feasibility.svg`
- `fig7_robustness_families.svg`

The publication bundle now also derives manuscript-ready figure caption text from the live summary:
- `kvrm-bench/results/publication_bundle/figure_captions.md`

That generated caption set is also synced into the paper folder through:
- `docs/papers/KVRM_PUBLICATION_APPENDIX.md`

The draft paper should prefer the generated appendix/caption outputs above rather than hand-maintaining figure-caption prose in multiple docs.

Historical figure files remain on disk for provenance, but the draft paper should prefer the current figure set above.
