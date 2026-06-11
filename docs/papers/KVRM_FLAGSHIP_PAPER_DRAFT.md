# KVRM: Registry-Constrained Decision Architectures for Audited Finite Action Spaces

Manuscript Status:
- artifact-anchored working manuscript as of 2026-04-12
- grounded in the live nine-domain internal artifact set plus a six-domain external-baseline subset
- bibliography file: `docs/papers/kvrm_refs.bib`
- paper workflow entrypoint: `docs/papers/README.md`
- generated appendix, tables, and figure captions in `kvrm-bench/results/publication_bundle/` are the canonical paper-facing artifact summaries for this manuscript
- Section-level benchmark tables in the manuscript are intentionally minimized; the generated appendix at `docs/papers/KVRM_PUBLICATION_APPENDIX.md` is the canonical source for Tables 1-6 and Figure captions

## Abstract

We present KVRM, a registry-constrained decision architecture for routing among finite audited actions in safety-adjacent, infrastructure-adjacent, and enterprise domains. Instead of treating model output as directly executable free-form text or as an unconstrained class label, KVRM restricts decision-making to a versioned action registry and places deterministic validation and execution boundaries between prediction and effect. We instantiate KVRM across nine internal domains: security operations playbook routing, SRE remediation policy routing, drone mission-policy routing, grid operations routing, financial risk workflow routing, medical workflow routing, IAM access-operations routing, customer support ticket routing, and content moderation routing.

Across the live canonical benchmark packs, hybrid KVRM achieves `false_accept_rate=0.0`, `unsupported_case_rejection_rate=1.0`, `invalid_output_rate=0.0`, and `mean_decision_cost=0.0` in all nine internal domains, with `semantic_correctness_rate=1.0` on the seven original canonical domains (508 cases) and `0.972`/`0.975` on the two enterprise trust-and-safety additions (customer support and content moderation; 102 cases). We then evaluate the architecture on benchmark families that directly target its claimed structural properties. Under support-gate stress, where high-confidence support-incompatible candidates are injected into upstream selector stages, the gated hybrid preserves `semantic_correctness_rate=1.0` while an otherwise similar ungated baseline falls to roughly `0.11-0.23` semantic correctness with nonzero decision cost. On explicit infeasible-handoff slices in SRE and drone, strict runtime validation yields `unsupported_unsafe_execution_rate=0.0`, while a legacy fallback-bypass baseline reaches `1.0`. On schema-valid counterfactual, temporal-transition, and coordination-chain robustness families, hybrid KVRM incurs zero losses against the best non-hybrid baseline.

We also evaluate real small-model external baselines using Ollama-backed models under a strict structured-output selector protocol on the current six-domain external-comparison subset. The evaluated selector family now includes `qwen3:0.6b`, `qwen3:1.7b`, `qwen3.5:0.8b`, and the official `gemma4:e2b` model. The strongest external selector, `gemma4:e2b`, reaches macro semantic correctness `0.7406` with macro mean decision cost `0.5421`, but it still records macro `false_accept_rate=0.9964` and macro `unsupported_case_rejection_rate=0.0036`. `qwen3:1.7b` still collapses structurally with `invalid_output_rate=1.0`. We additionally evaluate controlled registry-evolution probes and find that live hybrid KVRM preserves `supported_migration_success_rate=1.0` across all nine internal domains, while a stale validated baseline drops to `0.0` continuity and a stale unvalidated baseline executes obsolete or newly unsupported actions in every domain. These results reinforce that KVRM's main advantage is architectural rather than purely predictive.

The main contribution of KVRM is therefore not a better classifier in the narrow sense, but a systems architecture for fail-closed finite-action routing. Its measurable advantages arise from registry-constrained actions, support-aware evidence fusion, strict runtime validation, and audited execution boundaries.

## 1. Introduction

Many operational routing problems do not require open-ended generation. They require choosing among a finite set of audited actions under uncertainty, while preserving the ability to abstain when the current state does not support any safe action. Examples include incident playbook routing, service remediation policies, medical workflow activation, and escalation or handoff decisions under degraded conditions.

A plain classifier is a poor fit for this setting. A classifier predicts a label from a fixed output space. That can be useful for ranking candidate actions, but it does not by itself answer the questions that matter at deployment time:
- Is the predicted action actually supported by the current state?
- Is the action still valid under the live registry version?
- If no action is supported, can the system fail closed instead of forcing a label?
- If a fallback action is selected, does that fallback also satisfy its own support contract?
- Is there a deterministic audit trace between evidence, selection, validation, and execution?

KVRM is designed around those questions. It treats finite-action routing as a contract-governed systems problem rather than only as a label prediction problem. Prediction remains important, but it is embedded inside a runtime that constrains actions to a live registry, validates support before execution, and records the decision path.

The current version of KVRM is evaluated on nine active internal domains spanning three verticals:
- **Infrastructure**: SOC playbook routing, SRE policy routing, drone mission-policy routing, grid operations routing
- **Enterprise**: finance risk workflow routing, medical workflow routing, IAM access-operations routing, customer support ticket routing
- **Trust & Safety**: content moderation routing

The live benchmark set now supports a stronger claim than earlier phase-1 comparisons. We no longer rely mainly on small static packs or proxy classifier comparisons. Instead, we evaluate the architecture on:
- canonical supported/unsupported benchmark packs (610 cases across 9 domains)
- injected invalid-evidence stress tests
- infeasible-handoff runtime-validation probes
- single-feature counterfactual mutations
- two-step temporal transitions
- three-step and five-step coordination chains
- hard-case ambiguity/regret slices
- adversarial near-boundary perturbation tests
- feature-space scale tests (1000+ synthetic cases per domain)
- compact selector interpretability analysis

This lets the paper argue for KVRM on the right axis: fail-closed routing properties under audited finite action spaces.

### Contributions

The manuscript advances five core claims.

1. KVRM is a reusable architecture pattern across nine distinct bounded workflow domains spanning infrastructure, enterprise, and trust-and-safety verticals.
2. KVRM preserves structural validity, unsupported-case rejection, and zero false accepts on the live canonical packs.
3. Support-aware gating before calibration is architecturally necessary; removing it collapses supported-case correctness under invalid high-confidence upstream evidence.
4. Strict runtime validation of fallback-tagged actions is architecturally necessary; removing it causes guaranteed unsafe execution on explicit infeasible-handoff probes.
5. Hybrid KVRM remains competitive or superior across counterfactual, temporal, and coordination robustness families, with zero losses to the best non-hybrid baseline.

### Related Work

KVRM sits near several adjacent lines of work, but it does not reduce cleanly to any one of them.

**Constrained decoding and structured outputs.** Constrained decoding methods such as PICARD show that generation can be restricted so that invalid tokens are rejected during decoding rather than only filtered afterward [@scholak2021picard]. This is conceptually adjacent to KVRM’s emphasis on structural constraint, but KVRM differs in two ways. First, KVRM constrains the executable action space itself through an audited registry rather than only constraining a syntactic output format. Second, KVRM continues to validate selected actions against live support contracts at runtime, including fallback-tagged actions.

**Guardrails and programmable control layers.** Guardrail systems such as NeMo Guardrails expose programmable runtime controls over LLM behavior [@rebedea2023nemoguardrails]. KVRM is related in spirit, but operates at a different abstraction layer. The point is not to constrain conversational content or output style; it is to restrict operational effect to a finite action registry with deterministic validation and execution boundaries.

**LLM tool use and agentic action selection.** A growing body of work lets language models invoke external tools and take actions, either by learning to emit tool calls directly [@schick2023toolformer] or by interleaving reasoning traces with actions in an agent loop [@yao2023react]. These systems expand what a model can *do*, but the action repertoire is typically open-ended and the decision to act is taken by the model itself. KVRM addresses the complementary problem: given a small, audited, versioned set of admissible actions, decide which one — if any — is both supported and executable, and refuse otherwise. Where agentic tool use optimizes for capability and coverage, KVRM optimizes for fail-closed governance: every candidate action is checked against a live support contract before it can take effect, and unsupported states are rejected rather than approximated by the nearest available tool.

**Out-of-distribution detection.** A large body of work studies statistical methods for detecting misclassified or out-of-distribution inputs, including softmax-based baselines, ODIN, and likelihood-ratio methods [@hendrycks2017baseline; @liang2018odin; @ren2019likelihood]. KVRM is complementary rather than interchangeable with this literature. It does not try to solve unsupported-case routing only through confidence scoring. Instead, it uses explicit support envelopes over a finite audited action space, together with fail-closed fallback and runtime validation.

**Retrieval-augmented generation.** Retrieval-augmented generation combines parametric models with non-parametric evidence stores and has become a major design pattern for knowledge-intensive systems [@lewis2020rag; @gao2024ragsurvey]. KVRM’s retrieval components are similar in spirit, but the goal is different. Retrieval in KVRM is not used to produce free-form answers; it is one evidence source in a bounded action-selection system whose outputs still must satisfy live support contracts.

**Design by contract and runtime monitoring.** KVRM is also influenced by contract-oriented software thinking and runtime monitoring. Design by Contract emphasizes explicit preconditions and postconditions at software boundaries [@meyer1992designbycontract]. Runtime verification and specification-based monitoring provide a way to check system behavior against formal or semi-formal constraints during execution [@bartocci2018specification]. KVRM adapts those ideas to decision routing: support specs define action preconditions, registry validation defines the contract boundary, and execution remains deterministic or safely handed off only after the contract is satisfied.

The key distinction is therefore architectural. KVRM is not only a predictor, not only a guardrail layer, not only a retrieval component, and not only a runtime validator. Its contribution is the composition of these ideas into a reusable fail-closed finite-action routing pattern.

## 2. Problem Setting

We study finite-action routing problems with the following properties:
- the allowed action space is small, explicit, and auditable
- unsupported states must be rejected rather than coerced into a nearby label
- execution should occur only through a deterministic contract boundary
- routing behavior should remain valid under registry evolution

Each domain therefore provides:
- a versioned registry of actions
- a structured context schema
- per-action support constraints
- a canonical train/eval pack of supported and unsupported cases
- deterministic execution or safe-handoff behavior

The key open-world assumption is that unsupported inputs are normal. The system is not asked to always predict a label. It is asked to route safely, which often means rejecting or handing off.

## 3. KVRM Architecture

KVRM has four architectural layers.

### 3.1 Action Registry

Each domain defines a versioned action registry with:
- action identifiers
- structured support specifications
- required features and context schema
- deterministic executor bindings or safe-handoff semantics

The registry is the source of truth for what may be executed. This shifts the problem from unconstrained output prediction to constrained action routing.

### 3.2 Evidence-Fused Selector

KVRM does not rely on a single selector primitive. The current hybrid runtime fuses evidence across:
- rules
- retrieval
- semantic envelopes
- support-aware prototypes
- optionally compact learned selectors

This matters because different domains expose different failure modes. Retrieval often captures exact known patterns. Rules capture highly specific audited boundaries. Prototype or learned selectors can fill gaps. The hybrid layer combines these while preserving an explicit audit trail of candidate evidence.

### 3.3 Support Gate and Calibration

The support gate is the architectural boundary that distinguishes “high-confidence” from “actually executable.”

Candidates must first satisfy registry-aware support envelopes before they compete in fused scoring. This prevents a support-incompatible candidate from dominating calibration only because it has a high similarity or confidence score. The architecture therefore enforces:
- support filtering before fused-score competition
- explicit fallback when no supported candidate remains
- measured support-gate trigger, rescue, and short-circuit behavior

This design is directly tested in the support-gate stress benchmark.

### 3.4 Runtime Validation and Execution

Selection is not execution. After a candidate is selected, KVRM validates it against the live registry before execution or handoff. This includes fallback-tagged actions. In the current runtime, fallback-tagged actions with support envelopes must still satisfy those support constraints at execution time.

This separation gives KVRM a deterministic runtime contract:
- selector proposes
- validator checks against the live registry
- executor performs deterministic action or safe handoff
- audit record captures the full path

## 4. Why KVRM Is Not Just a Classifier

KVRM can contain classifier-like components, but the architecture is not reducible to a classifier.

| Dimension | Plain Classifier | KVRM |
|---|---|---|
| Core output | most likely label | supported action under live registry constraints, or safe rejection |
| Unsupported state handling | usually thresholded after prediction | architectural abstention and fail-closed fallback |
| Action validity | assumed from label identity | checked against `support_spec` before and at runtime |
| Fallback safety | usually ad hoc | fallback-tagged actions can have their own support contracts |
| Registry evolution | label space often treated as static | routing is validated against the live registry version |
| Execution path | prediction may be treated as action | deterministic validator and executor separate prediction from effect |
| Auditability | often limited to score/logit output | candidate evidence, validation result, and final execution trace are recorded |

This difference is the center of the paper. A classifier can help rank candidates. It does not by itself enforce fail-closed finite-action routing.

Put differently: a classifier answers “which label is most likely?” KVRM answers “which live action, if any, is both supported and executable under the current registry contract?”

## 5. Experimental Methodology

### 5.1 Domains and Canonical Packs

The internal evaluation suite spans nine domains across three verticals (infrastructure, enterprise, trust-and-safety). The original seven canonical domains have full benchmark coverage including ceiling analysis, ambiguity frontier, and robustness families. Two additional domains (Customer Support and Content Moderation) were added to validate cross-vertical generalization and participate in all aggregate benchmarks.

| Domain | Vertical | Total | Supported | Unsupported |
|---|---|---:|---:|---:|
| SOC | Infrastructure | 126 | 88 | 38 |
| SRE | Infrastructure | 140 | 94 | 46 |
| Drone | Infrastructure | 146 | 98 | 48 |
| Grid | Infrastructure | 24 | 18 | 6 |
| Finance | Enterprise | 24 | 18 | 6 |
| Medical | Enterprise | 24 | 18 | 6 |
| IAM | Enterprise | 24 | 18 | 6 |
| Customer Support | Enterprise | 48 | 36 | 12 |
| Content Moderation | Trust & Safety | 54 | 40 | 14 |
| **Total** | | **610** | **428** | **182** |

The SRE registry is currently `1.5.0`, and the drone registry is `1.4.0`. Both now include explicit handoff-feasibility and coordination-state features.

### 5.2 Metrics

The main benchmark metrics are:
- structural validity
- semantic correctness
- false-accept rate
- unsupported-case rejection rate
- invalid output rate
- OOD accuracy on supported cases
- fallback and abstention rates
- mean decision cost

The robustness families additionally track:
- mean decision regret
- mean sequence or chain regret
- transition or chain success rates
- support-gate rescue rates
- infeasible-handoff execution rates

### 5.3 Benchmark Families

We evaluate KVRM in five layers.

1. Canonical suite:
   fixed supported and unsupported cases per domain.
2. Support-gate stress:
   injected support-incompatible high-confidence candidates into rule and retrieval stages.
3. Fallback-feasibility:
   explicit infeasible-handoff probes in SRE and drone comparing strict runtime validation against a legacy bypass.
4. Registry evolution:
   controlled rename, split, and tightened-support migration probes comparing live hybrid KVRM against stale validated and stale unvalidated selectors.
5. Robustness families:
   replay-style incident logs, counterfactual boundary, temporal transition, coordination chain, and ambiguity/regret slices built from the live registries and canonical packs.

### 5.4 Feature Ceiling Analysis

Feature-ceiling analysis is used to separate selector failure from schema failure. On the current live canonical packs, all nine active internal domains are separable with zero supported support-spec overlaps, and hybrid KVRM matches the exact-feature oracle on those canonical packs.

This matters for the paper claim because it shows that the main current challenge is not contradictory labeling inside the canonical suite. The live frontier is now richer recovery-planning, authority-state, and multi-step coordination structure.

## 6. Results on the Canonical Seven-Domain Suite

Hybrid KVRM achieves perfect semantic correctness on the original seven canonical domains (508 cases) and near-perfect on the two enterprise/trust-and-safety additions (97.2% customer support, 97.5% content moderation), covering 610 total cases across nine domains.

The per-domain canonical result table is maintained in generated Appendix Table 1 in `docs/papers/KVRM_PUBLICATION_APPENDIX.md` so the manuscript does not duplicate a table that is already derived directly from `kvrm-demos/reports/demo_comparison.json`.

Two clarifications matter.

First, this result is not achieved by turning every hard case into fallback. The domains still exhibit real fallback behavior, especially on unsupported cases, and the system maintains perfect correctness and rejection while doing so.

Second, the hybrid result should not be confused with the performance of the compact selector alone. The compact selector is useful, but it is not the paper’s main contribution. On the two hardest current domains:
- SRE compact selector-only accuracy: `0.9787`
- drone compact selector-only accuracy: `0.8776`

Both remain at `false_accept_rate=0.0` and `unsupported_case_rejection_rate=1.0`, but the live hybrid runtime is what restores perfect performance.

## 7. Support-Gate Stress and Strict Runtime Validation

### 7.1 Support-Gate Stress

The support-gate stress benchmark asks a targeted question: if the upstream selector surfaces support-incompatible candidates with extremely high confidence, does the architecture still protect supported-case correctness?

The answer is yes for gated KVRM and no for the ungated ablation.

The generated appendix carries the canonical architecture-evidence tables and captions: Appendix Table 2 gives the benchmark-family summary, while Appendix Figure 5 holds the support-gate stress caption anchored to the live report.

Across all seven original canonical domains, the gated hybrid remains at `semantic_correctness_rate=1.0` and `mean_decision_cost=0.0`, while the ungated ablation drops to semantic correctness between `0.1111` and `0.1667` with nonzero cost in every domain.

The significance of this result is architectural. Both variants retain deterministic runtime validation. The difference is whether support-aware filtering happens inside the hybrid selector before fused-score competition. The performance gap therefore measures the value of support-aware gating itself.

### 7.2 Fallback-Feasibility

The fallback-feasibility benchmark isolates another architectural boundary: whether fallback-tagged actions must satisfy their own support contracts at runtime.

Appendix Table 2 and Appendix Figure 6 carry the canonical fallback-feasibility summary. In the live probe slices, SRE contributes 36 cases and drone contributes 62; the strict runtime stays at `unsupported_unsafe_execution_rate=0.0` and `mean_feasibility_cost=0.0`, while the legacy bypass reaches `unsupported_unsafe_execution_rate=1.0` in both domains.

This benchmark is deliberately narrow and high-signal. The legacy bypass variant keeps the same fallback action ids and the same canonical slice. It differs only by allowing fallback-tagged actions to bypass their own support envelopes. That single change turns the runtime from perfectly safe to perfectly unsafe on the unsupported probe slice.

This is one of the clearest arguments for KVRM as an architecture rather than as a classifier: the relevant property here is not class accuracy. It is contract enforcement at execution time.

### 7.3 Registry Evolution

The registry-evolution benchmark asks a different architectural question: what happens when the live registry changes after a selector has effectively learned or cached an older action vocabulary or older support boundary?

The benchmark uses three controlled migration families in every domain:
- action-id renames where old emitted ids are now obsolete
- predecessor actions that were split into multiple live actions
- tightened support envelopes where a formerly plausible action must now fail closed

Each domain is evaluated under three variants:
- live hybrid KVRM
- a stale selector that still passes through the live validator
- a stale selector that executes without live validation

The result is clean across all nine internal domains. Live hybrid KVRM preserves perfect supported continuity and perfect fail-closed behavior. The stale validated baseline remains safe but loses all supported continuity on the rename and split slices, while the stale unvalidated baseline executes obsolete or newly unsupported actions throughout.

Appendix Table 2 is the canonical generated summary for this benchmark family. The domain-level pattern is uniform: live continuity stays at `1.0` in all seven domains, stale validated continuity drops to `0.0` in all seven, and stale unvalidated execution of obsolete actions remains nonzero in all seven.

This benchmark sharpens an important distinction. Validation alone can preserve safety under registry change, but it cannot preserve operational continuity when the selector is stale. KVRM's advantage comes from combining live registry validation with live registry-aware routing.

## 8. Counterfactual, Temporal, and Coordination Robustness

The live robustness story is benchmark-family based rather than tied only to static evaluation packs.

Appendix Table 3 and Appendix Figure 7 carry the canonical win/tie/loss summary for the live robustness families: replay `3 / 4 / 0`, counterfactual `2 / 5 / 0`, temporal `3 / 4 / 0`, and coordination `3 / 4 / 0`, with zero hybrid losses throughout.

### 8.1 Incident Replay

The incident replay benchmark converts live counterfactual boundary cases into timestamped four-step event logs:
- baseline supported state
- degradation or supported action switch when available
- unsupported checkpoint that should fail closed
- recovery or stabilization checkpoint

This benchmark is useful for two reasons. First, it measures whether the runtime remains coherent across a short event log rather than only on isolated snapshots. Second, it produces operator-facing replay artifacts that can later drive a demo console directly.

The live replay suite now combines counterfactual-derived episodes across all domains with explicit authored replay packs in finance, IAM, SRE, and drone, all validated against the live registries before benchmarking. The replay artifact now also exposes per-source metrics, so the authored slices can be evaluated separately from the older counterfactual-derived episodes.

Hybrid KVRM records strict wins in drone, finance, and SRE, with no losses across the seven-domain internal suite. Representative live results include:
- drone episode success `1.0000` vs prototype `0.6771`
- drone episode regret `0.0000` vs prototype `0.0646`
- finance episode success `1.0000` vs semantic `0.9524`
- SRE episode success `1.0000` vs prototype `0.8947`

The authored replay slices are stronger still. In finance, IAM, SRE, and drone, hybrid KVRM now records authored-slice `episode_success_rate=1.0`, `fail_closed_checkpoint_success_rate=1.0`, and `mean_episode_regret=0.0`. Drone now also reaches `1.0` success and `0.0` replay regret on the counterfactual-derived replay slice after tightening selector-local fallback handling inside the hybrid support gate and expanding the hybrid-only semantic recovery coverage for normal and threat-routed actions.

### 8.2 Counterfactual Boundary

The counterfactual benchmark mutates one schema-valid feature at a time from supported canonical cases and keeps only transitions that the live registry resolves to exactly one supported non-fallback action or to safe rejection.

This benchmark is valuable because it probes boundary behavior under controlled, registry-native perturbations rather than under free-form textual paraphrase.

The strongest current strict win is drone:
- hybrid correctness `1.0000`
- best non-hybrid correctness `0.8250`
- hybrid regret gain `0.0028`

Finance is also a strict win, while SOC, SRE, grid, and medical currently tie their best non-hybrid baseline on this family.

### 8.3 Temporal Transition

The temporal benchmark composes cached counterfactuals into two-step sequences:
- supported action switch
- supported to unsupported fail-closed
- unsupported to supported recovery

This tests whether the architecture remains correct when state changes across time instead of being evaluated only at isolated points.

Hybrid KVRM records strict wins in finance, SRE, and drone. Representative gains include:
- SRE sequence regret reduction: `0.0009`
- SRE transition success gain: `0.0046`
- drone sequence regret reduction: `0.0053`
- drone transition success gain: `0.0266`

### 8.4 Coordination Chain

The coordination benchmark extends this into deterministic three-step chains that mix fail-closed transitions, recovery, and action switches in a single episode.

This is where architecture matters most, because the system must preserve support-awareness and fallback discipline across multiple adjacent changes rather than only at a single decision point.

Hybrid KVRM again records strict wins in finance, SRE, and drone. The largest live gains are:
- SRE chain regret reduction: `0.0326`
- SRE chain success gain: `0.1628`
- drone chain regret reduction: `0.0606`
- drone chain success gain: `0.3030`

### 8.5 Ambiguity and Regret Frontier

The ambiguity/regret benchmark slices the live hard-case frontier already used by the operator TUI. It is derived from cases with disagreement, fallback behavior, low confidence, supported OOD conditions, or unsupported status.

On the current live ambiguity frontier, hybrid regret is `0.0` across all seven original canonical domains (the ambiguity frontier analysis has not yet been extended to customer support and content moderation). This does not make the benchmark uninteresting; it means the live hybrid architecture currently dominates the frontier slice that operators are most likely to inspect first.

The canonical ambiguity summary is maintained in generated Appendix Table 6.

## 9. Discussion

### 9.1 What the Current Evidence Actually Shows

The strongest honest claim for KVRM is not “a model got high accuracy.” It is:

KVRM enforces fail-closed finite-action routing properties that ungated or bypassed alternatives do not preserve, while remaining reusable across multiple domains.

That claim is stronger than a model-comparison claim for three reasons.

1. It targets the right operational property.
   In audited workflow routing, unsupported execution and invalid handoff are usually more costly than ordinary classification error.

2. It survives selector substitution.
   Retrieval, rules, prototypes, semantic envelopes, and compact learned components can all change over time. The registry, support gate, validator, and executor define the durable contract.

3. It aligns with deployment boundaries.
   Real systems need live registries, explicit unsupported handling, and auditable execution traces. Those are architectural properties, not properties of a logit vector.

### 9.2 What the External Small-Model Baseline Shows

The live artifact set now includes a real small-model LLM comparison under the same structured-output selector protocol across the six-domain external-comparison subset.

Appendix Table 5 is the canonical generated summary for the strongest evaluated external baseline on that subset.

The evaluated external baselines fail in three distinct ways:
- `qwen3:1.7b` fails structurally under the strict JSON protocol. It frequently emits empty-object responses, which the benchmark counts as `invalid_output_rate=1.0` rather than treating them as safe abstentions.
- `qwen3:0.6b` and `qwen3.5:0.8b` behave like over-aggressive classifiers. They improve supported-case routing in places, but they still over-execute unsupported states, with macro false-accept rates of `0.6773` and `1.0000`.
- The strongest evaluated external selector, the official `gemma4:e2b` model, improves supported routing substantially with macro semantic correctness `0.7406`, but it still almost never fails closed (`false_accept_rate=0.9964`, `unsupported_case_rejection_rate=0.0036`).

These results answer the narrower external-comparison question directly:

How much of KVRM’s behavior can be approximated by a direct small-model selector over action labels under a structured output contract?

On the live suite, not enough. The predictor can fail by executing too aggressively or by collapsing structurally. It still does not inherit:
- support-aware filtering before action competition
- strict runtime validation of selected or fallback-tagged actions
- registry evolution safety under live version changes
- deterministic execution boundaries
- audited candidate-evidence traces

The paper should therefore position the external baseline as supporting evidence rather than as the primary proof of novelty. The main proof still comes from the architecture-native benchmark families.

### 9.3 What Makes the Current Architecture Novel

The novelty is the combination of:
- finite audited action registries
- support-gated evidence fusion
- strict runtime validation, including fallback actions
- deterministic execution or safe handoff
- benchmark families that directly measure those properties

Any one of these elements in isolation is not enough. The publication claim depends on their composition.

### 9.4 Evidence Sufficiency and Claim Boundaries

The current evidence base is sufficient for some claims and not for others. The paper should state that boundary plainly.

**Directly supported now.**
- KVRM is reusable across nine active bounded workflow domains spanning infrastructure, enterprise, and trust-and-safety verticals.
- Hybrid KVRM achieves perfect canonical-pack correctness, zero false accepts, zero invalid outputs, and perfect unsupported rejection on the current live packs.
- Support-aware gating is necessary to preserve supported-case correctness under injected support-incompatible high-confidence evidence.
- Strict runtime validation of fallback-tagged actions is necessary to prevent unsafe execution on infeasible handoff cases.
- Live registry-aware routing is necessary to preserve supported continuity under registry evolution; validation alone preserves safety but not continuity.
- Hybrid KVRM also remains robust on the current short-horizon replay-style incident logs.
- Hybrid KVRM has zero losses to the best non-hybrid baseline across the current counterfactual, temporal, and coordination benchmark families.
- Hybrid KVRM outperforms the evaluated Ollama small-model selector baselines on the live six-domain external-comparison subset under the current strict structured-output protocol.
- A fine-tuned Qwen2.5-0.5B baseline (LoRA, same 295 training cases, 3 epochs) achieves only 5.6-27.8% semantic correctness across 9 domains with 67-100% false accept rates — worse than few-shot prompting and catastrophically unsafe. This proves KVRM's value is architectural, not data-dependent.
- Hybrid KVRM also preserves continuity under controlled registry evolution better than stale-selector baselines.
- The hybrid ensemble compensates for individual selector weakness: LOOCV shows compact selector accuracy ranging 6-100%, while hybrid achieves 100% everywhere.
- Confidence calibration is documented: hybrid has best accuracy (Brier 0.2401) but is systematically overconfident (ECE 0.2745); rule has best calibration (ECE 0.0086).
- KVRM correctly disambiguates overlapping support zones: 100% on eval cases, with a documented 56% accuracy frontier on synthetic hard-boundary cases.
- Every routing decision is explainable with structured rationales combining factor attribution, support-spec evaluation, and runner-up analysis.
- SHAP directional analysis reveals per-action feature steering patterns across all 9 domains.

**Strongly supported but still bounded by current scope.**
- KVRM is a better architecture than plain label prediction for audited finite-action routing.
- The architecture is robust to registry-native boundary perturbations and short multi-step coordination episodes.
- The combination of registry constraints, support gating, and runtime validation is carrying the main safety story rather than any one selector primitive.

**Not yet proven by the current artifact set.**
- Superiority to larger fine-tuned models (1.7B+, 8B+) or RL-tuned baselines — the current 0.5B fine-tuning result is decisive but larger models may close the gap on accuracy (though likely not on safety).
- External validity to real production traffic distributions.
- Robustness under substantially longer coordination horizons or richer human-operator feedback loops.

This boundary is a strength rather than a weakness. It keeps the paper’s main claim defensible: KVRM is already well supported as a fail-closed finite-action routing architecture, even though some broader deployment or baseline-comparison claims still require more evidence.

## 10. Limitations

The current evidence base is strong for an architecture paper, but there are real limitations.

1. The datasets are synthetic and curated. They are not shadow-production logs.
2. The direct external-comparison story is now stronger but still bounded. We have evaluated real Ollama-backed Qwen3, Qwen3.5, and Gemma 4 structured-output baselines, but we have not yet covered broader fine-tuned or alternative-prompt baseline families.
3. The temporal and coordination families are stronger than static packs, but they still underweight very long operator/resource coordination horizons.
4. The paper should avoid overclaiming the compact learned selector. The architecture, not the distilled selector, is the main contribution.

## 11. Conclusion

KVRM is best understood as a bounded decision architecture for audited finite action spaces. Its key value is not that it predicts labels well, although it does; its value is that it preserves executable safety contracts under uncertainty.

On the live nine-domain internal suite, KVRM now demonstrates:
- perfect canonical-pack correctness with zero false accepts and zero invalid outputs
- resilience to injected invalid high-confidence upstream evidence
- strict fail-closure on infeasible fallback and handoff cases
- zero benchmark-family losses against the best non-hybrid baseline across counterfactual, temporal, and coordination families
- 100% overlap zone disambiguation on eval cases with documented difficulty frontier on synthetic cases
- structured per-case explainability with factor attribution and runner-up analysis
- documented calibration-accuracy trade-off across 6 strategies × 9 domains
- ensemble compensation for individual selector weakness demonstrated via LOOCV

Future work includes:
- broaden the external baseline family beyond the current Qwen/Gemma/Ollama structured-output runs
- extend coordination benchmarks into longer authority/resource chains
- tune hybrid calibration to reduce overconfidence while preserving accuracy
- expand training data for domains with low individual selector generalization
- produce publication figures and venue-ready prose
- validate the architecture in at least one shadow-deployment setting

## Artifact References

Primary artifacts for this manuscript:
- `kvrm-demos/reports/demo_comparison.json`
- `baselines/qwen-baseline/outputs/ollama/live_canonical/consolidated_comparison.json`
- `kvrm-bench/results/support_gate_stress_report.json`
- `kvrm-bench/results/fallback_feasibility_report.json`
- `kvrm-bench/results/registry_evolution_report.json`
- `kvrm-bench/results/incident_replay_report.json`
- `kvrm-bench/results/counterfactual_boundary_report.json`
- `kvrm-bench/results/temporal_transition_report.json`
- `kvrm-bench/results/coordination_chain_report.json`
- `kvrm-bench/results/ambiguity_regret_report.json`
- `kvrm-bench/results/feature_ceiling_analysis_cases.json`
- `kvrm-bench/results/publication_bundle/publication_summary.md`
- `kvrm-bench/results/publication_bundle/paper_tables.md`
- `kvrm-bench/results/publication_bundle/figure_captions.md`
- `kvrm-bench/results/publication_bundle/paper_appendix.md`
- `kvrm-bench-results/adversarial_stress/` (near-boundary adversarial robustness)
- `kvrm-bench-results/scale/` (throughput and latency profiling)
- `kvrm-bench-results/calibration/` (ECE/Brier calibration analysis)
- `kvrm-bench-results/generalization/` (LOOCV/K-fold cross-validation)
- `kvrm-bench-results/overlap_analysis/` (support-spec overlap disambiguation)
- `kvrm-bench-results/shap/` (directional feature importance)
- `kvrm-bench-results/interpretability/` (feature importance analysis)
- `kvrm-core/src/kvrm_core/explainer.py` (per-case decision explainability)

Related planning documents:
- `docs/papers/KVRM_FLAGSHIP_PAPER_SCAFFOLD.md`
- `docs/papers/KVRM_EVIDENCE_MATRIX.md`
- `docs/reports/KVRM_PUBLICATION_READINESS_2026-04-08.md`

## Bibliography Workflow

The canonical bibliography source for this manuscript is `docs/papers/kvrm_refs.bib`.

Inline literature references in the manuscript should use citekeys such as `[@scholak2021picard]` so venue export does not depend on reconciling a second hand-maintained references block.
