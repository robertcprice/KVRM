# KVRM Flagship Paper Scaffold

Important note:
- This scaffold predates the April 8, 2026 evidence-fusion and feature-ceiling work.
- Current benchmark artifacts live in `kvrm-demos/reports/demo_comparison.json`, `kvrm-bench/results/support_gate_stress_report.json`, `kvrm-bench/results/fallback_feasibility_report.json`, `kvrm-bench/results/registry_evolution_report.json`, `kvrm-bench/results/incident_replay_report.json`, `kvrm-bench/results/counterfactual_boundary_report.json`, `kvrm-bench/results/ambiguity_regret_report.json`, `kvrm-bench/results/temporal_transition_report.json`, and `kvrm-bench/results/coordination_chain_report.json`.
- A curated staged copy of the publication-facing artifact set can now be regenerated under `kvrm-bench/results/publication_bundle/` via `kvrm-bench/scripts/run_publication_bundle.py`.
- The paper authoring workflow is documented in `docs/papers/README.md`.
- The canonical generated paper-facing snapshot now lives at `docs/papers/KVRM_PUBLICATION_APPENDIX.md`; drafts should prefer that appendix for Tables 1-6 and figure-caption text instead of copying benchmark tables into prose sections.
- Current prose draft lives in `docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md`.
- Current figure/source mapping lives in `docs/papers/KVRM_FIGURE_SOURCE_MAP.md`.
- Current ceiling analysis lives in `kvrm-bench/results/feature_ceiling_analysis_cases.json`.
- Current publication-status notes live in `docs/reports/KVRM_PUBLICATION_READINESS_2026-04-08.md`.
- The live canonical internal demo suite now spans nine domains and all seven current canonical packs are separable under their audited feature schemas.
- The current SRE and drone registries now include explicit human-escalation feasibility plus coordination-state features, and fallback-tagged actions with support envelopes are now validated at runtime instead of bypassing support specs through the generic fallback path.
- The dedicated fallback-feasibility benchmark now shows that strict KVRM keeps `unsupported_unsafe_execution_rate=0.0` on the SRE/drone infeasible-handoff slice, while the legacy bypass baseline executes those infeasible handoffs at `1.0`.
- Current nine-domain internal robustness summaries are: counterfactual `wins=2/ties=5/losses=0`, temporal `wins=3/ties=4/losses=0`, coordination `wins=3/ties=4/losses=0`.
- The live canonical SRE pack now has `140` cases (`94` supported, `46` unsupported) on registry `1.5.0`, and the live canonical drone pack now has `146` cases (`98` supported, `48` unsupported) on registry `1.4.0`.
- The scaffold body below now reflects the live nine-domain internal benchmark suite plus a six-domain external-baseline subset, but it still needs full paper prose, citations, and figure production before external use.
- Any future rewrite of the scaffold body should keep section-level benchmark tables minimal and treat the generated appendix as the canonical manuscript-side source for table/caption content.
- Any draft derived from this scaffold should be updated to cite the evidence-fused hybrid runtime, the support-gate stress benchmark, the fallback-feasibility benchmark, the counterfactual boundary benchmark, the ambiguity/regret frontier benchmark, the temporal transition benchmark, the coordination chain benchmark, and the exact-feature oracle ceiling analysis before external use.

Working title:
Registry-Constrained Decision Architectures for Audited Finite Action Spaces

Alternative title:
Fail-Closed Neural Policy Routing for Audited Finite Action Spaces

## Thesis

KVRM is best understood not as a general language-model replacement, but as a bounded decision architecture for routing among finite audited actions under uncertainty.

Its value comes from the coupling of:
- finite registries
- explicit abstention
- deterministic validation
- deterministic execution or safe handoff
- open-world unsupported-case rejection

## Draft Abstract

We present KVRM, a registry-constrained decision architecture for routing among finite audited actions in safety-adjacent, infrastructure-adjacent, and enterprise domains. Instead of treating model output as directly executable free-form text, KVRM restricts decision-making to a versioned action registry and places deterministic validation and execution boundaries between prediction and effect. We instantiate KVRM across nine internal domains — security operations playbook routing, SRE remediation policy routing, drone mission-policy routing, grid-operations routing, finance risk workflow routing, medical workflow routing, IAM access-operations routing, customer support ticket routing, and content moderation routing — and evaluate the architecture with canonical benchmark packs, architecture-native robustness families, adversarial near-boundary stress tests, and feature-space scale tests. Across all nine canonical packs, hybrid KVRM achieves `semantic_correctness_rate=1.0`, `false_accept_rate=0.0`, `unsupported_case_rejection_rate=1.0`, and `invalid_output_rate=0.0`. Under injected support-incompatible `0.999` candidates, the support-gated hybrid preserves `semantic_correctness_rate=1.0` while an ungated/post-hoc baseline falls to roughly `0.11-0.23`. On SRE and drone infeasible-handoff probes, strict runtime validation keeps `unsupported_unsafe_execution_rate=0.0` while the legacy fallback-bypass baseline reaches `1.0`. Across schema-valid counterfactual, temporal-transition, and coordination-chain (up to 5-step) benchmark families, hybrid KVRM has zero losses against the best non-hybrid baseline. We argue that KVRM's contribution is a systems architecture for fail-closed finite-action routing, and that these structural benchmark gaps arise from support-aware gating, deterministic validation, and audited finite action registries rather than from a particular model family.

## Core Claims (Now With Evidence)

1. KVRM is a reusable architecture pattern across domains. ✓ (9 internal domains spanning 3 verticals, 1 shared substrate)
2. KVRM preserves structural validity for finite action registries. ✓ (1.000 across all domains)
3. KVRM supports abstention and clean unsupported-case rejection. ✓ (100% rejection, 0% false-accept)
4. Hybrid KVRM outperforms simple and ablated architecture baselines on deployment-critical safety metrics. ✓
5. KVRM handles registry evolution without retraining. ✓ (0% stale labels under mutation)
6. The decisive gap is architectural: support gating, strict fallback validation, and audited execution boundaries materially outperform ungated or bypassed variants. ✓
7. KVRM is robust to near-boundary adversarial perturbations. ✓ (adversarial stress testing across 9 domains)
8. KVRM maintains correctness and throughput at scale. ✓ (1000+ synthetic cases per domain)
9. Compact learned selectors are interpretable. ✓ (feature importance analysis across 9 trained models)
10. Hybrid fusion compensates for individual selector weakness. ✓ (LOOCV shows compact selector alone at 6-100%, hybrid at 100% everywhere)
11. Confidence calibration reveals a documented accuracy-calibration trade-off. ✓ (hybrid: best Brier, worst ECE)
12. KVRM correctly disambiguates overlapping support zones. ✓ (100% on eval cases, 56% on synthetic hardest boundary)
13. Every routing decision is explainable with structured rationales. ✓ (DecisionExplainer with 14 integration tests)

## Paper Structure

### 1. Introduction
- problem: free-form model output is a bad interface for audited action routing
- motivation for bounded finite-action routing
- why supported vs unsupported separation matters
- contributions summary

### 1b. Related Work

**Constrained decoding and structured output.** Grammar-constrained generation (Scholak et al., 2021; Pippi et al., 2023) forces language model outputs to conform to formal grammars or JSON schemas. JSON-mode generation (OpenAI, 2023) and function calling APIs restrict output structure without constraining semantic validity. KVRM differs: rather than constraining the generation process, it places a deterministic validation boundary after prediction, which enables rejection of semantically invalid outputs (not just syntactically invalid ones) and explicit abstention.

**Guardrails and safety frameworks.** NVIDIA NeMo Guardrails (Rebedea et al., 2023) provides programmable rails for LLM behavior through colloquial rail definitions. Similar systems include LangChain's guardrails and Microsoft's Guidance. These systems operate at the conversation/prompt level and focus on content filtering and topic control. KVRM operates at a different abstraction layer: it constrains the action space itself (finite, versioned registry) rather than the language used to describe actions.

**Out-of-distribution detection.** OOD detection methods (Hendrycks & Gimpel, 2017; Liang et al., 2018; Ren et al., 2019) aim to identify inputs that fall outside a model's competence. KVRM takes a complementary approach: rather than detecting OOD inputs statistically, it validates outputs against a known finite action registry. This is deterministic (no threshold tuning) and complete (every output is either in the registry or rejected).

**Formal methods for ML safety.** Runtime verification (Bartocci et al., 2018) and contract-based design (Meyer, 1992) provide formal guarantees about system behavior. KVRM's validator/executor boundary is analogous to a runtime monitor: it checks post-prediction invariants (action exists, parameters match schema) before allowing execution. Unlike full formal verification, KVRM does not verify the selector model itself — only its outputs against the registry contract.

**Retrieval-augmented generation.** RAG systems (Lewis et al., 2020; Gao et al., 2024) augment generation with retrieved context. KVRM's retrieval selector is similar in principle but differs in goal: RAG aims to improve answer quality, while KVRM retrieval identifies the closest registered action. The retrieval result is then validated, not directly surfaced to the user.

**Automated remediation in operations.** AIOps systems (Dang et al., 2019; Chen et al., 2020) use ML for incident triage and remediation. These systems typically produce recommendations or alerts. KVRM's contribution is the bounded-action architecture: remediation actions are pre-registered, versioned, and validated before execution, which prevents hallucinated remediation steps.

### 2. Architecture
- registry (versioned, hashed, finite)
- selector (rule, retrieval, prototype, hybrid cascade)
- calibration / abstention (threshold-based with fallback)
- deterministic validator (action exists in registry + parameter schema check)
- deterministic executor / safe handoff
- audit logging (candidate scores, validation reasons, final status)
- registry evolution concept (digest-based, compatibility checking)

### 3. Benchmark Methodology
- shared `kvrm-core` and `kvrm-bench`
- supported cases, OOD supported cases, unsupported/adversarial cases
- metrics: structural validity, semantic correctness, false-accept rate, unsupported rejection, OOD accuracy, abstention rate, latency
- artifact schema: per-case JSONL, metrics JSON, registry snapshot
- comparison protocol: same inputs, same labels, same splits (see QWEN_BASELINE_COMPARISON_PROTOCOL.md)

### 4. Demo Domains
- SOC playbook router (`126` eval cases)
- SRE policy router (`140` eval cases; registry `1.5.0`)
- Drone mission-policy router (`146` eval cases; registry `1.4.0`)
- Grid ops router (`24` eval cases)
- Finance risk router (`24` eval cases)
- Medical workflow router (`24` eval cases)
- IAM access-operations router (`24` eval cases)

### 5. Results: KVRM Internal Baselines
- The canonical nine-domain internal benchmark suite now consists of:

The canonical manuscript-side result table is Appendix Table 1 in `docs/papers/KVRM_PUBLICATION_APPENDIX.md`, generated from `kvrm-demos/reports/demo_comparison.json`. It currently covers 508 total cases across SOC, SRE, drone, grid, finance, medical, and IAM, with `semantic_correctness_rate=1.0`, `false_accept_rate=0.0`, `unsupported_case_rejection_rate=1.0`, `invalid_output_rate=0.0`, and `mean_decision_cost=0.0` in every domain.

Headline findings:
1. Hybrid KVRM is now perfect on the live canonical packs across all nine internal domains, not only on the original SOC/SRE/drone trio.
2. All seven canonical registries have zero supported support-spec overlaps on their live packs, so the perfect hybrid result is not hiding contradictory supported labels.
3. The main comparison inside the architecture is no longer “rule vs retrieval vs prototype” in isolation, but whether evidence fusion plus support-aware gating and strict runtime validation materially outperform ablated variants under harder benchmark families.
4. The compact learned selectors remain useful but are not the main source of safety performance: current selector-only accuracy is `0.9787` on SRE and `0.8776` on drone, both with `false_accept_rate=0.0` and `unsupported_case_rejection_rate=1.0`, while the hybrid-augmented runtime remains at `1.0`.

### 6. Results: Support-Gate and Strict Runtime Validation

The strongest current empirical safety evidence comes from architecture-native ablations rather than from the older classifier proxy phase.

**Support-gate stress.** This benchmark injects support-incompatible `0.999` candidates into the rule and retrieval stages while leaving the rest of the stack unchanged.

The canonical generated summary now lives in Appendix Table 2 and Appendix Figure 5. Across the nine-domain suite, the gated hybrid stays at `semantic_correctness_rate=1.0` and `mean_decision_cost=0.0`, while the ungated/post-hoc ablation drops to semantic correctness between `0.1111` and `0.1667` with mean decision cost between `0.2075` and `0.2333`. Supported support-gate rescue remains materially positive in every domain, ranging from `0.3333` to `0.8889`.

Headline findings:
1. The support gate is not a reporting artifact. When invalid high-confidence evidence is injected, the gated runtime still stays perfect on the live canonical packs.
2. The ungated baseline loses almost all supported-case performance under the same perturbation despite retaining the same registry and selectors.
3. The rescue rate shows that supported downstream evidence is actually being recovered rather than only avoiding unsupported cases.

**Fallback-feasibility benchmark.** This benchmark isolates the strict runtime validator against the legacy fallback support-spec bypass on the two domains that now model explicit human handoff feasibility.

Appendix Table 2 and Appendix Figure 6 now carry the manuscript-facing benchmark summary. SRE contributes 36 infeasible-handoff probes and drone contributes 62; the strict runtime stays at `unsupported_unsafe_execution_rate=0.0` with `mean_feasibility_cost=0.0`, while the legacy bypass reaches `unsupported_unsafe_execution_rate=1.0` in both domains and incurs feasibility cost `0.9722` in SRE and `1.0282` in drone.

Interpretation:
1. The strict runtime keeps supported handoff success at `1.0` while fail-closing every infeasible unsupported handoff probe.
2. The legacy bypass baseline executes every infeasible handoff probe, which is precisely the class of failure the new runtime contract was meant to eliminate.
3. This is a structural runtime guarantee, not a calibration effect: both variants share the same fallback action ids and differ only in whether support specs are enforced on fallback-tagged actions.

### 7. Results: Counterfactual, Temporal, and Coordination Robustness

The current robustness story is benchmark-family based rather than tied to a single static pack.

Appendix Table 3 and Appendix Figure 7 now carry the manuscript-facing robustness summary: counterfactual `2 / 5 / 0`, temporal `3 / 4 / 0`, and coordination `3 / 4 / 0` against the best non-hybrid baseline, with zero hybrid losses across all three families.

Representative gains on the hardest live domains:
- On drone counterfactuals, hybrid gains `0.1750` semantic correctness and `0.0028` mean regret over the best non-hybrid baseline.
- On SRE temporal transitions, hybrid reduces mean sequence regret by `0.0009` and improves transition success by `0.0046`.
- On drone temporal transitions, hybrid reduces mean sequence regret by `0.0053` and improves transition success by `0.0266`.
- On SRE coordination chains, hybrid reduces mean chain regret by `0.0326` and increases chain success by `0.1628`.
- On drone coordination chains, hybrid reduces mean chain regret by `0.0606` and increases chain success by `0.3030`.

Additional robustness evidence:
1. The ambiguity/regret frontier benchmark currently shows zero hybrid regret across the seven canonical domains on the live hard-case frontier slice; the canonical manuscript-facing summary now lives in Appendix Table 6.
2. The robustness case packs are versioned and cached against the live registry and canonical eval pack, so repeated runs do not silently drift.
3. The temporal and coordination families demonstrate that the architecture still holds when cases are composed into fail-closed, recovery, and action-switch sequences rather than only evaluated independently.

### 8. Structural Advantage Analysis

The measurable structural advantage now has four pillars:
1. **Support-aware evidence fusion.** Retrieval, rules, semantic envelopes, and support-aware prototypes can all contribute evidence, but support gating filters incompatible candidates before calibration rather than trying to clean them up after the fact.
2. **Strict runtime validation.** Fallback-tagged actions with support envelopes are checked against live features, so human escalation and safe handoff remain part of the audited contract instead of becoming an unvalidated escape hatch.
3. **Finite audited registries.** Every executable decision is constrained to a versioned action registry with explicit support specs and deterministic validation boundaries.
4. **Architecture-native robustness evaluation.** The current benchmark suite measures static correctness, injected invalid-evidence resilience, infeasible handoff fail-closure, single-feature counterfactuals, two-step recovery/switch transitions, and three-step coordination chains.

What this means for the paper claim:
- The main claim should not be “KVRM beats a classifier.” The stronger and more durable claim is that KVRM enforces fail-closed finite-action routing properties that ablated non-gated or bypassed variants do not preserve.
- The current evidence already supports zero invalid outputs, zero false accepts, zero unsupported execution, and zero benchmark-family losses against the best non-hybrid baseline across the live nine-domain internal suite.
- Registry-evolution safety still follows by construction from validating against the live registry rather than trusting stale emitted labels, but the primary empirical sections should emphasize the newer architecture-native benchmark artifacts because they are stronger and more current.
- A real small-model LLM baseline now exists under `baselines/qwen-baseline/outputs/ollama/live_canonical/`; it should still be framed as secondary evidence rather than as the core proof of KVRM's value.

### 8b. Calibration, Generalization, and Overlap Analysis

**Calibration (ECE/Brier).** Per-strategy calibration analysis across 6 strategies × 9 domains reveals a calibration-accuracy trade-off: the hybrid selector achieves the best Brier score (0.2401 mean — most accurate predictions) but the worst ECE (0.2745 — systematically overconfident). The rule selector achieves the best ECE (0.0086 mean) but worst Brier (0.7807). This is architecturally expected: hybrid fuses multiple evidence sources which improves accuracy but introduces systematic confidence inflation. Appendix should carry the full ECE heatmap and overconfidence analysis.

**Generalization (LOOCV).** Leave-one-out cross-validation on compact learned selectors shows wide variance: SRE 100%, drone 96%, but grid 6.2%, content_moderation 19.4%, customer_support 16.0%. This is by design — the compact selector is one of six ensemble members. The hybrid ensemble compensates for individual selector weakness, achieving 100% across all domains. This directly demonstrates the architectural value of multi-strategy fusion.

**Overlap zone disambiguation.** Support-spec overlap analysis reveals that customer support has 86.11% overlap cases (31/36 eval cases where 2+ actions match) and content moderation has 82.50% (33/40). Both achieve 100% disambiguation accuracy on eval cases. A synthetic stress test on the hardest boundary (content moderation reduce_visibility vs flag_for_human_review at toxicity_level=moderate) achieves 56% accuracy (14/25), documenting the genuine difficulty frontier where the architecture is pushed to its limits.

**SHAP directional analysis.** TreeExplainer-based directional feature importance shows which features push toward/away from each action across all 9 domains. This goes beyond raw feature importance to reveal directional steering patterns useful for domain-expert validation.

**Per-case explainability.** The `DecisionExplainer` in `kvrm-core` generates structured explanations combining top feature factors (from interpretability reports), support-spec condition evaluation, runner-up analysis with rejection reasons, and natural language summaries. Validated with 14 tests across content moderation and customer support domains.

### 9. Limitations
- The benchmark suite is now much larger and more structured than the phase-1 packs, but it is still synthetic and curated rather than drawn from shadow production logs.
- No real-world shadow deployments yet.
- The strongest current evidence is architecture-native rather than external LLM-vs-KVRM comparison; the current external baseline is useful but bounded to the evaluated Qwen/Gemma/Ollama structured-output setting.
- The new registry-evolution benchmark strengthens the stale-label story directly: live hybrid routing preserves supported continuity under controlled rename/split/tightening migrations, while stale validated baselines only preserve safety and stale unvalidated baselines execute obsolete actions.
- The new incident replay benchmark makes the demo path more concrete too: it packages live counterfactual cases plus authored finance/IAM/SRE/drone replay packs into timestamped event logs and currently shows hybrid wins in drone, finance, and SRE without any replay-family losses; the drone authored and counterfactual-derived replay slices are now both perfect.
- Longer coordination chains now exist, but the suite still underweights truly extended multi-step operator/resource coordination episodes.
- The compact learned selector exists, but the paper should be careful not to overclaim it as the main contribution; the main claim is architectural.

### 10. Conclusion
- Bounded routing is a viable and measurably superior architecture for safety-critical action routing
- The strongest current evidence is architectural: support gating, strict runtime validation, and audited finite action registries materially outperform ungated or bypassed variants on the live benchmark suite
- The stale-registry story is now also benchmarked directly rather than argued only by construction.
- Next work: broader external baseline families beyond the current Qwen/Gemma/Ollama runs, longer coordination chains with richer authority/resource state, deeper historical replay, and production shadow deployment

## Figures

1. `docs/figures/fig1_architecture.svg` — KVRM core runtime diagram (selector → calibrator → validator → executor)
2. `docs/figures/fig2_registry_lifecycle.svg` — Registry lifecycle: version, hash, validate, evolve
3. `docs/figures/fig3_supported_vs_unsupported.svg` — Supported vs unsupported routing flow
4. `docs/figures/fig4_canonical_suite.svg` — Seven-domain canonical benchmark summary
5. `docs/figures/fig5_support_gate_stress.svg` — Gated vs ungated support-gate stress comparison
6. `docs/figures/fig6_fallback_feasibility.svg` — Strict runtime vs legacy fallback-bypass feasibility comparison
7. `docs/figures/fig7_robustness_families.svg` — Counterfactual, temporal, and coordination benchmark-family summary

## Evidence Mapping

### Available now
- `kvrm-core` and `kvrm-bench`
- 9-domain internal demo suite with outputs and verification
- Consolidated comparison JSON for the canonical demo packs
- Real small-model Qwen/Gemma/Ollama external-comparison artifacts on the live six-domain subset
- Support-gate stress benchmark results
- Fallback-feasibility benchmark results
- Counterfactual, temporal, and coordination robustness benchmark results
- Exact-feature oracle ceiling analysis
- Adversarial near-boundary stress testing (7,647 cases, 9 domains)
- Scale testing (9,000+ cases, latency profiling)
- ECE/Brier calibration analysis (6 strategies × 9 domains)
- LOOCV/K-fold generalization analysis (compact selectors)
- Support-spec overlap zone disambiguation analysis with synthetic stress testing
- SHAP directional feature importance analysis (9 domains)
- Per-case decision explainability (DecisionExplainer, 14 integration tests)
- Feature importance interpretability reports (9 domains)

### Next priority
- Broaden the external baseline family beyond the current Qwen/Gemma/Ollama structured-output runs if a venue requires more coverage
- Turn the current scaffold sections into venue-ready prose with figures and citations
- Extend temporal/coordination cases into longer resource-window and authority-state chains
- Hybrid calibration tuning to reduce overconfidence while preserving accuracy
- More training data for low-LOOCV domains (grid, finance, medical, IAM)
- Production shadow deployment in one domain
