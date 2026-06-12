# KVRM Evidence Matrix

Status:
- working internal review artifact
- maps paper claims to the exact artifacts that currently support them
- paper workflow entrypoint: `docs/papers/README.md`

## Purpose

This file is the shortest path to answering:
- what claims are already supported by live artifacts
- which exact reports back those claims
- where the current evidence is still incomplete

It is meant to reduce overclaiming during paper writing.

For manuscript-facing tables and figure captions, prefer the generated appendix at `docs/papers/KVRM_PUBLICATION_APPENDIX.md` and use `docs/papers/README.md` as the workflow guide for what is generated versus hand-edited.

## Claim Matrix

| Claim | Status | Primary Evidence | Current Support |
|---|---|---|---|
| KVRM is reusable across multiple bounded workflow domains. | Supported | `kvrm-demos/reports/demo_comparison.json` | Twelve active internal domains with one shared substrate and live canonical packs. |
| KVRM preserves structural validity on the live canonical packs. | Supported | `kvrm-demos/reports/demo_comparison.json` | Structural validity is `1.0` across all twelve hybrid demos. |
| KVRM achieves zero false accepts and perfect unsupported rejection on the live canonical packs. | Supported | `kvrm-demos/reports/demo_comparison.json` | `false_accept_rate=0.0` and `unsupported_case_rejection_rate=1.0` across all twelve hybrid demos. |
| KVRM achieves zero invalid outputs on the live canonical packs. | Supported | `kvrm-demos/reports/demo_comparison.json` | `invalid_output_rate=0.0` across all twelve hybrid demos. |
| The support gate is architecturally necessary. | Supported | `kvrm-bench/results/support_gate_stress_report.json` | Gated hybrid remains at `semantic_correctness_rate=1.0`; ungated baseline falls to roughly `0.11-0.17` semantic correctness with nonzero cost. |
| Runtime validation of fallback-tagged actions is architecturally necessary. | Supported | `kvrm-bench/results/fallback_feasibility_report.json` | Strict runtime keeps `unsupported_unsafe_execution_rate=0.0`; legacy bypass reaches `1.0` on both SRE and drone probe slices. |
| Live KVRM preserves continuity under controlled registry evolution better than stale-selector baselines. | Supported | `kvrm-bench/results/registry_evolution_report.json` | Live hybrid keeps `supported_migration_success_rate=1.0` across all seven evaluated domains; stale validated stays safe but drops to `0.0` continuity; stale unvalidated executes obsolete or newly unsupported actions in all seven. |
| Hybrid KVRM remains robust on short-horizon replay-style incident logs. | Supported | `kvrm-bench/results/incident_replay_report.json` | Replay family result is `wins=3`, `ties=4`, `losses=0`, with strict wins in drone, finance, and SRE; finance, IAM, SRE, and drone now include explicit authored replay packs on top of the counterfactual-derived episodes, the report exposes per-source replay metrics, and the live drone replay slices are now both at `episode_success_rate=1.0` and `mean_episode_regret=0.0`. |
| Hybrid KVRM is robust to schema-valid boundary perturbations. | Supported | `kvrm-bench/results/counterfactual_boundary_report.json` | Counterfactual family result is `wins=2`, `ties=5`, `losses=0`. |
| Hybrid KVRM is robust to short temporal transitions. | Supported | `kvrm-bench/results/temporal_transition_report.json` | Temporal family result is `wins=3`, `ties=4`, `losses=0`. |
| Hybrid KVRM is robust to short coordination chains. | Supported | `kvrm-bench/results/coordination_chain_report.json` | Coordination family result is `wins=3`, `ties=4`, `losses=0`. |
| Hybrid KVRM dominates the current live ambiguity frontier. | Supported | `kvrm-bench/results/ambiguity_regret_report.json` | Hybrid regret is `0.0` across all seven evaluated domains on the current frontier slice. |
| The live canonical schemas are separable under their current feature contracts. | Supported | `kvrm-bench/results/feature_ceiling_analysis_cases.json` | All seven active canonical domains have zero supported support-spec overlaps and hybrid matches the exact-feature oracle. |
| KVRM is different from a classifier in a materially important way. | Supported | `support_gate_stress_report.json`, `fallback_feasibility_report.json`, live runtime architecture | The strongest gap is architectural: support gating, strict fallback validation, and deterministic execution boundaries. |
| KVRM outperforms the evaluated real small-model Ollama selector baselines on the live suite. | Supported | `baselines/qwen-baseline/outputs/ollama/live_canonical/consolidated_comparison.json` | On the live eight-domain subset (586 cases), the stronger external selector, `gemma4:e2b`, reaches macro semantic `0.5971` but still posts macro `false_accept_rate=0.7741` and `unsupported_rejection_rate=0.0027`; `qwen3.5:0.8b` posts macro `false_accept_rate=1.0`; hybrid KVRM holds macro semantic `0.9934` with zero false accepts on the same subset. |
| KVRM is validated under production traffic. | Not yet supported | no live artifact yet | No shadow deployment artifact yet. |
| KVRM is robust under long-horizon multi-step coordination. | Supported | `temporal_transition_report.json`, `coordination_chain_report.json` | Supported for two-step, three-step, and five-step coordination sequences across all seven evaluated domains. |
| KVRM is robust to near-boundary adversarial perturbations. | Supported | `kvrm-bench-results/adversarial_stress/` | Adversarial near-boundary mutation testing (single-condition miss, boundary step, multi-action competition) across all nine domains. |
| KVRM maintains correctness and throughput at scale. | Supported | `kvrm-bench-results/scale/` | Feature-space enumeration (1000+ synthetic cases per domain) with latency profiling (p50/p95/p99) across all nine domains. |
| Compact learned selectors are interpretable via feature importance. | Supported | `kvrm-bench-results/interpretability/` | RandomForest feature importance analysis (global + per-action disaggregation) across all nine domains with trained models. |
| KVRM generalizes beyond infrastructure domains. | Supported | `kvrm-demos/customer-support-router/`, `kvrm-demos/content-moderation-router/` | Customer support (7 actions, 48 eval cases) and content moderation (7 actions, 54 eval cases) both achieve SC=1.0 and CC=1.0, proving KVRM works for enterprise and trust-and-safety use cases. |
| Individual selector calibration varies; hybrid achieves best accuracy but is overconfident. | Supported | `kvrm-bench-results/calibration/` | ECE analysis across 6 strategies × 9 domains. Rule selector: best ECE (0.0086 mean). Hybrid: best Brier score (0.2401 mean, most accurate predictions) but worst ECE (0.2745, systematically overconfident). Post-hoc isotonic regression reduces hybrid ECE by 65.7% (0.2745→0.0858). |
| The hybrid ensemble compensates for individual learned selector weakness. | Supported | `kvrm-bench-results/generalization/` | LOOCV on compact selectors after training data augmentation: SRE 100%, drone 96%, grid 77.5%, medical 77.1%, IAM 75%, finance 59.6%. The hybrid ensemble achieves 100% across all domains, demonstrating the value of multi-strategy fusion over any single selector. |
| KVRM correctly disambiguates overlapping support zones. | Supported | `kvrm-bench-results/overlap_analysis/` | Customer support: 86% overlap, content moderation: 82% overlap — both achieve 100% disambiguation on eval cases. Synthetic stress test on hardest boundary (reduce_visibility vs flag_for_human_review) achieves 56% — documenting the genuine difficulty frontier. |
| SHAP directional analysis reveals per-action feature steering. | Supported | `kvrm-bench-results/shap/` | TreeExplainer directional analysis across 9 domains shows which features push toward/away from each action, enabling feature-level interpretability beyond raw importance. |
| KVRM decisions are explainable with structured per-case rationales. | Supported | `kvrm-core/src/kvrm_core/explainer.py` | DecisionExplainer generates human-readable and machine-readable explanations combining top feature factors, support-spec condition evaluation, runner-up analysis, and natural language summaries. Now includes counterfactual explanations (minimum feature changes to flip decision), batch CSV/JSON export, and SHAP directional integration. Validated with 32 tests. |
| Post-hoc isotonic recalibration dramatically reduces hybrid overconfidence. | Supported | `kvrm-bench-results/calibration/recalibration_report.{json,md}` | Isotonic regression reduces hybrid ECE from 0.2745 to 0.0858 (65.7% improvement) via LOOCV. Temperature scaling actually hurts in 6/9 domains. Platt scaling provides a middle ground (24.4% improvement). |
| Small-model LLM baselines fail catastrophically on KVRM routing tasks, even when fine-tuned on the same training data. | Supported | `baselines/finetune/eval_outputs/merged/`, `baselines/qwen-baseline/outputs/ollama/live_canonical/` | **Few-shot baseline**: qwen3.5:0.8b 37-44% SC with 100% FA; gemma4:e2b 8-25% SC with 72-92% invalid. **Fine-tuned baseline** (Qwen2.5-0.5B, LoRA, 295 cases, 3 epochs): 5.6-27.8% SC across 9 domains with 67-100% FA. Fine-tuning is WORSE than few-shot and completely fails on safety (abstention). KVRM achieves 100% SC and 0% FA on identical eval cases. |

## Evidence Tiers

### Tier 1: Strongest current evidence

These are the cleanest publication anchors because they directly instantiate the architectural claims:
- `kvrm-bench/results/support_gate_stress_report.json`
- `kvrm-bench/results/fallback_feasibility_report.json`
- `kvrm-bench/results/registry_evolution_report.json`
- `kvrm-bench/results/incident_replay_report.json`
- `kvrm-bench/results/counterfactual_boundary_report.json`
- `kvrm-bench/results/temporal_transition_report.json`
- `kvrm-bench/results/coordination_chain_report.json`

### Tier 2: Canonical performance, separability, and robustness

These establish the base system state, the current ceiling, and adversarial/scale robustness:
- `kvrm-demos/reports/demo_comparison.json`
- `kvrm-bench/results/ambiguity_regret_report.json`
- `kvrm-bench/results/feature_ceiling_analysis_cases.json`
- `kvrm-bench-results/adversarial_stress/` (near-boundary mutation robustness)
- `kvrm-bench-results/scale/` (1000+ case throughput and latency)
- `kvrm-bench-results/interpretability/` (feature importance analysis)
- `kvrm-bench-results/calibration/` (ECE/Brier calibration across 6 strategies × 9 domains)
- `kvrm-bench-results/generalization/` (LOOCV and K-fold cross-validation)
- `kvrm-bench-results/overlap_analysis/` (support-spec overlap zone disambiguation)
- `kvrm-bench-results/shap/` (SHAP directional feature importance)
- `kvrm-core/src/kvrm_core/explainer.py` (per-case decision explainability)

### Tier 3: Helpful but not decisive for the central paper claim

These are useful supporting artifacts but should not carry the main novelty claim alone:
- compact selector training reports in `kvrm-bench/results/*_compact_training_report_v1.json`
- historical scaffold/proxy-baseline notes
- archived legacy artifacts

## Recommended Claim Discipline

The paper should confidently claim:
- fail-closed finite-action routing
- support-aware evidence fusion
- strict runtime validation
- live-registry continuity under controlled registry evolution
- short-horizon replay robustness on timestamped incident logs
- nine-domain internal architectural reuse spanning infrastructure, enterprise, and trust-and-safety verticals
- zero benchmark-family losses against the best non-hybrid baseline on the live robustness families
- superiority to the evaluated Ollama small-model selector baselines under the current strict structured-output protocol
- adversarial near-boundary robustness under systematic perturbation across nine domains
- sub-millisecond decision latency at scale (1000+ synthetic cases per domain)
- interpretable learned selectors via feature importance analysis
- SHAP directional feature steering per action
- per-case structured decision explanations with factor attribution and runner-up analysis
- calibration-accuracy trade-off: hybrid most accurate (lowest Brier), rule best calibrated (lowest ECE)
- ensemble compensates for individual selector weakness (LOOCV demonstrates this)
- 100% disambiguation in overlap zones on eval cases; synthetic stress test documents difficulty frontier
- long-horizon coordination robustness (5-step chains)

The paper should avoid claiming, without new evidence:
- superiority to all small LLM baselines or to alternative fine-tuned prompting/training regimes not yet evaluated
- production-readiness beyond bounded research demos

## Next Evidence Additions

If more evidence is needed, the best additions are:

1. Broader external baselines beyond the current Qwen/Gemma/Ollama structured-output runs, expanded to include the two new domains (customer support, content moderation).
2. A shadow-deployment or replay-style evaluation in at least one domain.
3. Hybrid calibration tuning to reduce overconfidence (ECE improvement while preserving Brier performance).
4. More training data for domains with low LOOCV accuracy (grid, finance, medical, IAM) to strengthen individual selector generalization.
5. Expanded synthetic overlap testing beyond content moderation to identify other hard disambiguation boundaries.
