# KVRM Comprehensive Execution Plan

> For Hermes: execute this plan by treating KVRM as a bounded decision architecture for finite audited action spaces. Do not assume new examples must come from existing repo subprojects. Prefer stronger new demos over weaker legacy ones.

Goal: build the strongest possible, evidence-backed KVRM research program around finite-action registry-constrained selection, then prove it with new high-value demonstrations that are clearer, safer, and more broadly useful than some of the current repo examples.

Architecture: KVRM is the control-plane pattern, not a universal “neural everything” story. The core loop is: state/features -> finite audited registry -> selector -> calibration/abstain -> deterministic validation -> deterministic executor or safe handoff -> logging/evaluation. The research program should treat current subprojects as optional inputs, not constraints.

Tech stack: Python, PyTorch, lightweight classifiers/routers, retrieval/profile baselines, deterministic validators/executors, benchmark harnesses, JSON registry specs, calibration tooling, reproducible evaluation scripts, optional UI/demo shells.

---

## 0. Correct framing

This plan adopts the corrected framing:

- KVRM is not “neural everything.”
- KVRM is not valuable because it makes all infrastructure neural.
- KVRM is valuable when a system has a finite, audited, high-stakes action space and we want bounded learned selection with fallback, traceability, and deterministic enforcement.
- New examples do not need to inherit from current KVRM repo projects if better examples can be built cleanly from scratch.

Core one-line positioning:

KVRM is a registry-constrained decision architecture for choosing among finite audited actions under uncertainty.

---

## 1. Desired end state

At the end of this execution plan, the repo should support:

1. One clear KVRM Core reference implementation.
2. One flagship paper with honest, strong claims.
3. Three to five high-quality application demos built around the same core pattern.
4. A shared benchmark/evaluation harness used across all demos.
5. Explicit OOD, abstention, fallback, and registry-evolution testing.
6. A clean repo structure where legacy or unrelated material does not dilute the story.

---

## 2. KVRM Core specification

Every serious KVRM example must implement the same reference interface.

### 2.1 Core abstractions

1. Registry
- finite list of allowed actions
- stable action IDs
- human-readable names
- parameter schema per action
- version/digest metadata
- optional append-only compatibility rules

2. Context encoder
- converts state into structured features
- no hidden free-form prompt magic in the final benchmark path
- must be serializable for replay

3. Selector
- chooses one registry action or abstains
- can be one of:
  - rule/profile table
  - retrieval selector
  - compact classifier
  - LLM teacher for data generation only
  - hybrid runtime selector

4. Calibration layer
- confidence score
- thresholding
- abstain behavior
- optional conformal or distance-based rejection

5. Deterministic validator
- schema validation
- precondition checks
- permission/safety checks
- support-set checks

6. Deterministic executor / safe handoff
- performs the action or hands it to a human/review layer
- no silent bypass

7. Audit log
- input features
- candidate scores
- chosen action
- abstain/fallback reason
- validator decision
- execution result

### 2.2 Canonical runtime order

1. parse registry
2. encode current state
3. try exact profile hit if configured
4. try retrieval/support-bank match if configured
5. run selector if needed
6. calibrate confidence
7. abstain if below threshold
8. validate chosen action
9. on validation failure, fail closed or fallback
10. execute deterministic action or send to safe handoff
11. log the full decision trace

### 2.3 Non-negotiable metrics

Every KVRM benchmark must report:

- structural validity
- semantic correctness or task utility
- abstention rate
- fallback rate
- invalid-output rate
- false-accept rate
- latency p50/p95/p99
- calibration error
- OOD performance
- registry-evolution robustness where applicable

---

## 3. New application portfolio

These are the recommended new examples. They are chosen because they fit KVRM better than some current projects and make the architecture easier to understand.

## 3.1 Demo A: SOC incident playbook router

Objective: route an incident to one of a finite set of approved response playbooks.

Why this is strong:
- clearly finite action space
- easy to explain
- auditability matters
- fallback to human analyst is natural
- strong “critical infrastructure adjacent” story without overclaiming

Registry examples:
- isolate_host
- rotate_credentials
- collect_forensics
- escalate_p1
- block_ip_temporarily
- monitor_only
- request_human_triage
- do_nothing_validated

Inputs:
- severity
- confidence of threat detection
- asset criticality
- lateral movement indicators
- blast radius estimate
- endpoint/server/cloud identity
- recent similar incidents

Executor:
- deterministic playbook stub / workflow engine mock
- no real destructive production actions needed for benchmark

Primary baselines:
- hand-coded incident rules
- retrieval from prior labeled incidents
- compact tree/boosting classifier
- hybrid KVRM selector

Target claim:
- bounded playbook routing with strong abstention/fallback behavior under noisy incident inputs

## 3.2 Demo B: Drone mission-policy router

Objective: choose a finite approved mission policy mode, not continuous control.

Why this is strong:
- easy real-world relevance
- discrete policies are natural
- safe fallback modes are obvious
- good way to demonstrate KVRM in autonomous systems honestly

Registry examples:
- continue_mission
- return_to_home
- hold_position
- switch_to_low_observable_path
- conserve_battery_mode
- climb_for_signal_recovery
- descend_for_safety
- manual_handoff

Inputs:
- battery level
- comms quality
- GPS quality
- wind severity bucket
- obstacle density bucket
- threat level bucket
- mission urgency bucket
- payload criticality

Executor:
- simulator-level deterministic mission-state transition
- no raw motor control

Primary baselines:
- expert rules
- retrieval from prior mission states
- compact classifier
- hybrid KVRM selector

Target claim:
- policy-level autonomous routing with fail-safe abstention and deterministic safety enforcement

## 3.3 Demo C: Medical workflow triage router

Objective: choose a safe clinical workflow route, never diagnosis or treatment autonomy.

Why this is strong:
- important domain
- finite routing paths are realistic
- reviewer handoff is natural
- demonstrates safe use in medicine without irresponsible claims

Registry examples:
- routine_review
- urgent_clinician_review
- sepsis_screen_pathway
- stroke_alert_pathway
- imaging_protocol_a
- imaging_protocol_b
- lab_panel_priority_order
- escalate_supervisor_review

Inputs:
- vitals-derived features
- symptom buckets
- age bracket
- prior risk markers
- acuity score bucket
- clinician note flags converted into structured features

Executor:
- deterministic workflow dispatch only
- no prescription/treatment generation

Primary baselines:
- triage rules
- clinical-score-based routing
- retrieval baseline
- compact classifier
- hybrid KVRM selector

Target claim:
- safe workflow routing with explicit abstention to clinician review under uncertainty

## 3.4 Demo D: Financial risk workflow router

Objective: choose among approved review and control workflows, not free-form trading.

Why this is strong:
- finance cares about auditability
- finite policy actions are natural
- easy to demonstrate bounded decisions

Registry examples:
- approve_low_risk
- enhanced_due_diligence
- manual_review
- freeze_for_investigation
- escalate_compliance
- require_additional_docs
- lower_limit_temporarily
- reject_unsupported_case

Inputs:
- transaction amount bucket
- jurisdiction risk bucket
- anomaly score bucket
- account history summary features
- KYC completeness state
- velocity indicators

Executor:
- deterministic review queue / control action mock

Primary baselines:
- threshold rules
- retrieval
- compact classifier
- hybrid KVRM selector

Target claim:
- audited finite-action risk routing with lower false-accept behavior under ambiguity

## 3.5 Demo E: Infrastructure incident / service-recovery policy router

Objective: choose one approved remediation workflow in ops/SRE contexts.

Why this is strong:
- likely the cleanest enterprise demo
- finite action spaces are natural
- deterministic execution and rollback are natural

Registry examples:
- restart_service
- failover_region
- scale_out
- drain_node
- rollback_deploy
- enable_readonly_mode
- page_human_operator
- gather_more_telemetry

Inputs:
- latency bucket
- error-rate bucket
- deployment recency
- dependency health summary
- region health flags
- saturation indicators

Executor:
- deterministic environment simulator or mock orchestrator

Target claim:
- safer remediation-policy routing than free-form agent output

---

## 4. Portfolio selection decision

Build these in order:

1. SOC incident playbook router
2. Infrastructure incident/service-recovery router
3. Drone mission-policy router
4. Medical workflow triage router
5. Financial risk workflow router

Why this order:
- easiest to benchmark honestly
- strongest fit to audited finite action spaces
- least regulatory / ethical confusion early on
- produces clearer “critical infrastructure adjacent” evidence faster

---

## 5. Shared benchmark framework

Create one shared benchmark framework before building all five demos independently.

### 5.1 Required shared directories

Recommended new structure:

- `kvrm-core/`
  - registry/
  - selector/
  - calibration/
  - validation/
  - execution/
  - logging/
  - metrics/
- `kvrm-bench/`
  - datasets/
  - scenarios/
  - runners/
  - reports/
  - plots/
- `kvrm-demos/`
  - soc-playbook-router/
  - sre-policy-router/
  - drone-mission-router/
  - medical-workflow-router/
  - finance-risk-router/

If you do not want new top-level dirs, create the same logical structure under an active root package, but keep the separation.

### 5.2 Benchmark runner requirements

The benchmark runner must support:
- deterministic seeds
- train/val/test split control
- OOD split control
- registry mutation scenarios
- replay logs
- paired baseline comparisons
- confidence threshold sweeps
- artifact export

### 5.3 Metrics artifact schema

Each run must emit:
- `config.json`
- `registry.json`
- `metrics.json`
- `per_case_results.jsonl`
- `summary.md`
- optional plots

---

## 6. Data strategy

### 6.1 Data sources by maturity stage

Stage 1: synthetic but policy-grounded
- build structured simulators for each domain
- generate edge cases and boundary conditions
- use explicit domain policies to label baseline-safe behavior

Stage 2: retrieval bank and support-set curation
- collect canonical scenario bank
- mine hard negatives
- create OOD holdouts deliberately

Stage 3: human-reviewed scenario packs
- review registry actions and labels
- refine ambiguous cases
- document unsupported cases explicitly

### 6.2 Hard rule

Do not train only on one hand-coded policy and then claim “intelligence.”

Every benchmark should include:
- benchmark oracle or utility definition
- multiple baselines
- explicit unsupported cases
- clear distinction between in-distribution and OOD performance

---

## 7. Model strategy

### 7.1 Preferred runtime models

Preferred order for runtime:
- exact profile table
- retrieval selector
- tiny calibrated classifier
- hybrid selector combining the above

LLMs should mainly be used for:
- teacher data generation
- scenario augmentation
- parsing messy natural-language cases into structured features for separate study

### 7.2 Runtime selector target sizes

Aim for selectors that are small enough to be believable in real deployment:
- tree/boosted model
- small MLP
- compact transformer only if clearly justified

### 7.3 Required confidence methods

Implement at least one from each class:
- probabilistic calibration: temperature scaling
- support-distance rejection: nearest-support distance
- explicit abstain class or threshold policy

Optional:
- conformal prediction
- ensemble uncertainty

---

## 8. Evaluation matrix

Every demo must be evaluated across this matrix.

### 8.1 Baseline set

Minimum baselines:
- hand rules
- retrieval
- compact classifier
- KVRM selector
- hybrid KVRM

### 8.2 Test set types

- in-distribution clean
- in-distribution noisy
- edge/boundary cases
- unsupported/OOD cases
- registry evolution cases
- adversarial malformed cases where applicable

### 8.3 Questions each benchmark must answer

1. Does KVRM preserve structural validity?
2. Does KVRM know when to abstain?
3. Does KVRM beat naive rules or retrieval anywhere meaningful?
4. Does hybrid KVRM outperform pure KVRM?
5. What happens under registry drift?
6. What happens under OOD cases?
7. Are bad valid decisions reduced compared to unconstrained generation or weak heuristics?

---

## 9. Research deliverables

## 9.1 Flagship paper

Working title:
Registry-Constrained Decision Architectures for Audited Finite Action Spaces

Paper structure:
1. problem statement
2. KVRM Core architecture
3. registry safety and fail-closed semantics
4. calibration and abstention
5. shared benchmark suite
6. portfolio demos
7. OOD and registry-evolution robustness
8. limitations and non-goals

## 9.2 Demo bundle

Must include:
- one launcher
- one demo index
- copy-paste run commands
- one report per demo
- one comparison table across all demos

## 9.3 Figure set

Required figures:
- architecture block diagram
- runtime decision flow
- abstention/fallback flowchart
- per-demo registry diagram
- accuracy vs abstention tradeoff plots
- OOD robustness plots
- registry-evolution behavior plot

---

## 10. Repo restructuring work

This part governs what should remain active versus archived.

### 10.1 Active KVRM root should contain
- KVRM core implementations
- active benchmark framework
- active demos
- current paper/docs/plans
- only subprojects that still contribute directly to the KVRM research story

### 10.2 Archive or move out if not actively supporting KVRM core
- legacy whitepapers and fragmented drafts
- branding/ideation folders
- historical memories/scratch notes
- unrelated research programs
- dead build directories
- one-off scripts not used in active experiments

### 10.3 Decision rule for keeping old projects in active root

Keep only if the project does one of these:
- serves as the flagship benchmark surface
- implements shared KVRM core logic
- is one of the chosen portfolio demos
- directly contributes to the current paper/evaluation story

Otherwise:
- move it to `/projects/` as its own project, or
- move it to `archive/`

---

## 11. Execution phases

## Phase 1: Core spec and benchmark foundation

Objective: create the shared KVRM foundation before building more demos.

Tasks:
1. Write `KVRM Core Spec` document.
2. Define registry JSON schema.
3. Define metrics/report schema.
4. Implement minimal shared benchmark runner.
5. Implement baseline interfaces.
6. Implement calibration and abstain interface.
7. Implement deterministic validator interface.
8. Add artifact export and replay logging.

Exit criteria:
- all future demos can plug into the same harness
- one small toy registry benchmark runs end-to-end

## Phase 2: Build Demo A and Demo B

Objective: ship the two clearest demos first.

Tasks:
1. Build SOC incident simulator and registry.
2. Build SOC baselines.
3. Build SOC hybrid KVRM selector.
4. Build SOC OOD and unsupported-case sets.
5. Build SRE incident simulator and registry.
6. Build SRE baselines.
7. Build SRE hybrid KVRM selector.
8. Run full benchmark matrix.

Exit criteria:
- two demos produce publication-quality metrics and logs
- at least one demonstrates clear benefit of bounded routing and abstention

## Phase 3: Build Drone demo

Objective: prove KVRM can generalize to autonomy-related policy routing safely.

Tasks:
1. define drone mission-state feature schema
2. define approved policy registry
3. implement deterministic mission-state executor
4. create failure and degradation scenarios
5. benchmark hybrid KVRM versus expert rules and retrieval

Exit criteria:
- safe-policy routing story is clear
- no temptation to oversell raw flight control

## Phase 4: Build Medical and Finance demos

Objective: broaden domain relevance after the architecture is already credible.

Tasks:
1. define workflow routing registries
2. build structured simulators or curated scenario packs
3. implement validator/handoff semantics
4. benchmark under abstention-heavy settings

Exit criteria:
- demos show workflow routing value without unsafe claims

## Phase 5: Flagship synthesis

Objective: turn the whole thing into one coherent research package.

Tasks:
1. write comparison matrix across all demos
2. produce final figures
3. write flagship paper draft
4. compress docs into one newcomer funnel
5. create one demo launcher

Exit criteria:
- one paper
- one benchmark framework
- one demo bundle
- one coherent repo narrative

---

## 12. Detailed task breakdown for immediate implementation

### Task 1: Create KVRM Core Spec

Objective: freeze the architecture so future demos stay coherent.

Files:
- Create: `docs/specs/KVRM_CORE_SPEC.md`
- Create: `docs/specs/KVRM_REGISTRY_SCHEMA.md`
- Create: `docs/specs/KVRM_METRICS_SCHEMA.md`

Verification:
- each spec has a concrete JSON example
- each spec names supported and unsupported patterns

### Task 2: Create shared benchmark package

Objective: avoid rebuilding benchmark logic five times.

Files:
- Create package for runners, metrics, artifacts, replay
- Add minimal tests for artifact integrity and runner behavior

Verification:
- one toy benchmark runs end-to-end and writes all required artifacts

### Task 3: Create Demo A from scratch

Objective: create the best first KVRM example.

Files:
- registry spec
- scenario generator
- deterministic executor
- baseline implementations
- hybrid KVRM selector
- benchmark config
- README

Verification:
- clean run command
- result artifacts
- comparative report

### Task 4: Create Demo B from scratch

Same pattern as Task 3.

### Task 5: Add calibration and abstention sweep tooling

Objective: ensure all claims include uncertainty handling.

Verification:
- threshold sweep produces plots and summary tables

### Task 6: Add registry-evolution suite

Objective: prove safety under action-space changes.

Verification:
- append-only, reorder, and incompatible mutations all produce expected behaviors

### Task 7: Add OOD suite

Objective: test support-boundary behavior, not just clean-set accuracy.

Verification:
- unsupported cases trigger abstention/fallback at acceptable rates

### Task 8: Draft flagship paper skeleton and figure placeholders

Objective: keep implementation aligned with the final story.

Verification:
- all demos map cleanly to paper sections

---

## 13. Anti-goals

Do not spend time on these before the core portfolio is strong:

- raw continuous control demos
- unconstrained language generation demos
- huge LLM-first implementations for tiny action spaces
- proving “neural operating system” narratives
- broad safety claims without abstention/fallback data
- building five unrelated demo codebases with no shared benchmark layer

---

## 14. Immediate order of execution

Do this next, in order:

1. Write the KVRM Core spec.
2. Create the shared benchmark framework.
3. Build the SOC playbook router demo from scratch.
4. Build the SRE policy router demo from scratch.
5. Add calibration/abstention sweeps.
6. Add registry-evolution tests.
7. Build the drone mission-policy demo.
8. Only then extend to medical and finance workflow routing.
9. Collapse the entire project into one flagship paper + one demo launcher.

---

## 15. Bottom line

The best version of KVRM is not constrained by the current repo lineup.

If stronger examples exist, build them.

The winning move is:
- one clean core architecture
- a shared benchmark stack
- a small number of extremely strong finite-action demos
- honest uncertainty and fallback handling
- one coherent story

That will make KVRM much stronger than trying to defend weaker inherited examples.