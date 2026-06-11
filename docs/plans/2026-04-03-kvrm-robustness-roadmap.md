# KVRM Robustness Research Roadmap

> For Hermes: use subagent-driven-development if executing this plan task-by-task.

Goal: turn KVRM from a broad but uneven research umbrella into a robust, defensible research program centered on bounded neural decision-making for audited finite action spaces.

Architecture: narrow the core claim to registry-constrained neural selection with deterministic validation, abstention, fallback, and audited execution. Treat application domains as adapters over the same core pattern rather than separate grand theories. Optimize for truthfulness, reproducibility, OOD robustness, and deployment realism before expanding scope.

Tech stack: Python, PyTorch/Transformers, lightweight classifiers, retrieval/profile baselines, deterministic validators/executors, benchmark harnesses, per-domain adapters.

---

## Executive thesis

The strongest version of KVRM is not “neural OS” or “LLM controls critical infrastructure.”

The strongest version is:

1. finite audited action registry
2. compact selector over that registry
3. calibrated uncertainty / abstain option
4. deterministic validation and preconditions
5. deterministic execution or safe human-reviewed handoff
6. shadow-mode evidence before autonomy

That is the center of the roadmap.

---

## North-star research claims to earn

These are the claims worth proving over the next phases.

1. Structural validity claim
- For finite registries, KVRM can guarantee output membership in the audited action set.

2. Safe deployment claim
- KVRM can fail closed, abstain, and route to safe fallback when confidence is low or inputs are out-of-support.

3. Competitive utility claim
- On selected finite-action tasks, KVRM or hybrid KVRM beats or complements rule/profile/retrieval baselines on regret, correctness, or robustness.

4. Registry evolution claim
- KVRM can remain safe under append-only registry evolution, key reordering, and compatibility drift.

5. Cross-domain claim
- The same architecture transfers across GPU optimization, opcode/IR routing, SOC incident playbooks, and mission-policy routing.

---

## Claims to stop making until proven

Do not lead with these until the evidence exists.

- “Formally verified neural CPU”
- “Critical infrastructure ready”
- “Everything is neural”
- “Universal speedups”
- “Non-hallucinogenic” in the broad LLM sense
- “Neural scheduler beats classical schedulers”

Replace with:

- “registry-constrained neural selection”
- “deterministic validation and fallback”
- “structural validity by construction for finite registries”
- “semantic correctness remains empirical”
- “hardware- and workload-qualified efficiency”

---

## Priority architecture changes

### Phase 0: unify the real KVRM core

Objective: define one canonical architecture used across all serious experiments.

Canonical runtime:
1. feature extraction
2. exact profile hit if available
3. retrieval / nearest-support lookup
4. compact neural selector over registry
5. calibration + abstain check
6. deterministic precondition validation
7. deterministic executor or safe fallback
8. monitoring + logging

Deliverables:
- `kvrm-core/` design doc or equivalent shared spec across subprojects
- shared registry contract format
- shared abstention interface
- shared metrics schema

Success criteria:
- every active KVRM subproject can be expressed in the same runtime pattern
- no active project bypasses validator/fallback semantics

### Phase 1: replace overpowered models with compact calibrated selectors

Objective: stop using general LLMs where a small model is better.

Tasks:
- benchmark compact MLP / classifier heads against current LLM selectors for finite-action tasks
- distill teacher LLM behavior into compact selectors where possible
- add calibration: temperature scaling, ECE, Brier score
- add explicit abstain class or confidence-threshold rejection

Success criteria:
- materially lower latency
- equal or better semantic accuracy on held-out finite-action tasks
- calibrated confidence is measurable and useful

### Phase 2: registry contracts as a first-class research contribution

Objective: make registry evolution and safety a headline contribution.

Tasks:
- enforce digest/version locking between registry and model artifacts
- support append-only migrations
- support stable key IDs across reordering
- add compatibility checker and migration report tooling
- benchmark breakage behavior under registry drift

Success criteria:
- incompatible registry/model pair fails closed
- append-only compatible changes preserve operation
- papers can report robustness under registry evolution

---

## Core evaluation agenda

### Benchmark family A: supported in-distribution finite-action selection

Metrics:
- structural validity
- semantic correctness
- regret vs oracle
- latency p50/p95/p99
- fallback rate
- abstention rate
- calibration error

Baselines required every time:
- hand rule / heuristic
- profile table
- nearest-neighbor retrieval
- small classifier
- grammar-constrained generation if relevant
- current KVRM selector
- hybrid KVRM

### Benchmark family B: OOD and support-boundary behavior

Stressors:
- unseen workload shapes
- unseen syntax variants
- registry expansion
- registry reorder
- unsupported action requests
- adversarial or malformed inputs

Metrics:
- invalid output rate
- false-accept rate
- abstention precision/recall
- fallback success rate
- semantic accuracy on supported subset

### Benchmark family C: shadow-mode deployment realism

Pattern:
- KVRM suggests action
- deterministic controller or human-approved policy executes action
- log disagreements and outcomes

Metrics:
- disagreement rate
- regret vs trusted policy
- safe override rate
- unsupported-input detection rate
- cost of abstention

---

## Immediate project ranking

### Tier 1: push hard now

1. `kvrm-gpu`
- currently the most mature and truth-aware line
- strongest existing evidence and framing
- best place to establish the canonical hybrid KVRM architecture

2. `kvrm-llm-compiler`
- useful as opcode / IR / canonicalization testbed
- strong fit for finite audited action spaces
- should be reframed away from “formal verification” toward “reference-checked bounded decoding”

### Tier 2: keep, but reframe before expanding

3. `kvrm-os`
- valuable as bounded action-routing testbed
- not yet evidence-backed as an improved scheduler
- should pivot from “LLM scheduler beats OS schedulers” to “safe policy-selection architecture with shadow-mode evaluation”

### Tier 3: archive / separate from core story

4. `conscious`
- separate research program; not part of the defensible KVRM core story

5. `linguigenesis`
- separate research program; keep if useful, but outside the KVRM robustness narrative

6. legacy whitepaper / memory / branding artifacts
- keep as archive material, not active research surface

---

## Application roadmap

These are the best domains to demonstrate KVRM honestly.

### Application 1: GPU control-plane selection

Why:
- already strongest evidence
- finite action space
- measurable regret vs oracle
- clear latency story

Deliverable:
- hybrid selector using profile + retrieval + compact neural selector + abstain

Target paper:
- “Registry-Constrained Neural Selection for Audited GPU Control Planes”

### Application 2: Opcode / IR / compiler canonicalization

Why:
- finite audited output space
- deterministic reference execution available
- easy to benchmark syntax variation and OOD robustness

Deliverable:
- canonical opcode/IR routing benchmark with reference-checked execution and abstain fallback

Target paper:
- “Bounded Neural Canonicalization for Verified Instruction and IR Interfaces”

### Application 3: SOC / incident response playbook routing

Why:
- strongest “critical infrastructure adjacent” use case without overclaiming
- discrete approved playbooks
- easy fallback to analyst review
- audit trail matters

Deliverable:
- incident state -> approved playbook routing
- shadow-mode eval against analyst or rules baseline

Target paper:
- “Fail-Closed Neural Playbook Selection for Security Operations”

### Application 4: Drone mission-policy routing

Why:
- shows real-world relevance without pretending to control motors directly
- finite safe policy presets are natural
- fallback can be return-home / hover / manual handoff

Deliverable:
- mission state -> approved policy mode
- geofence, battery, comms, threat context inputs
- hard fallback on uncertainty

Target paper:
- “Audited Mission-Policy Selection for Autonomous Aerial Systems”

### Application 5: Medical workflow routing

Only after the above are strong.

Good scope:
- triage workflow class
- escalation class
- protocol selection bucket

Bad scope:
- autonomous diagnosis
- prescribing
- treatment control

Deliverable:
- routing into clinician-reviewed pathways only

---

## Concrete experiments to run next

### Experiment set 1: hybrid KVRM on GPU tile selection

Objective: show hybrid KVRM is better than pure neural or pure heuristic approaches.

Tasks:
1. define shared feature schema for workload state
2. implement exact profile-hit path
3. implement retrieval support-bank path
4. implement compact selector path
5. add abstain threshold
6. compare all baselines and the hybrid model
7. rerun on CPU, MPS, CUDA

Success criteria:
- hybrid wins on robustness-adjusted utility, not necessarily every raw accuracy metric
- abstention reduces bad valid decisions
- latency remains far below constrained generation baselines

### Experiment set 2: registry-evolution stress suite

Objective: make registry safety a signature contribution.

Tasks:
1. create append-only registry mutations
2. create reorder-only mutations
3. create incompatible mutations
4. measure selector behavior before and after mutation
5. validate fail-closed semantics and compatibility detection

Success criteria:
- append-only mutation is safely handled or explicitly migrated
- reorder mutation does not silently corrupt action semantics
- incompatible mutation refuses execution

### Experiment set 3: llm-compiler reframing benchmark

Objective: prove bounded canonicalization is useful without overstating “verification.”

Tasks:
1. define canonical output registry for opcode or IR class routing
2. create syntax variation corpus
3. add malformed/adversarial corpus
4. compare small selector, retrieval, LLM, and hybrid KVRM
5. evaluate against reference interpreter / compiler stage checks

Success criteria:
- high structural validity
- strong syntax normalization behavior
- meaningful abstain/fallback performance on malformed inputs

### Experiment set 4: kvrm-os shadow-mode benchmark

Objective: stop claiming scheduler superiority until actually measured.

Tasks:
1. repair benchmark metrics so completion/turnaround are real
2. define deterministic classical scheduler baselines
3. run KVRM in proposal-only shadow mode
4. measure disagreement, regret, and fallback behavior
5. only then test bounded autonomous execution on non-critical workloads

Success criteria:
- benchmark outputs are believable
- model decisions are comparable to baselines
- fallback and abstention are measurable

---

## Repository reorganization plan

### Keep in active root
- `kvrm-gpu/`
- `kvrm-llm-compiler/`
- `kvrm-os/`
- `kvrm-compiler/`
- `kvrm-ecosystem/`
- `kvrm-rate-limiter/`
- `kvrm-spnc/`
- `kvrm-vector/` only if it remains part of the active KVRM story
- `docs/plans/`

### Move out of active root into `/Users/bobbyprice/projects/`
- `conscious/`
- `linguigenesis/`

### Move into `archive/`
- `white paper/`
- `logos-kvrm-files/`
- `memory/`
- `pytorch-build/`
- orphaned one-off root scripts that are not active entrypoints

### Rehome
- move `docs/RATE_LIMITER_KVRM.md` into `kvrm-rate-limiter/docs/`

---

## Paper and presentation strategy

### Flagship paper

Title direction:
- “Registry-Constrained Neural Selection for Audited Finite Action Spaces”

Sections:
1. motivation: open-ended generation is unsafe for audited control interfaces
2. architecture: registry, selector, calibration, validator, executor, fallback
3. theory-lite guarantees: structural validity and fail-closed semantics
4. empirical suite: GPU, opcode/IR, SOC playbooks, mission-policy routing
5. registry evolution and OOD robustness
6. limitations and bad-fit cases

### Follow-up vertical papers
- GPU control planes
- compiler/opcode canonicalization
- SOC routing
- mission-policy routing

---

## 30-day execution order

### Week 1
- finalize active-scope positioning
- clean root folder
- define canonical KVRM core interfaces
- repair repo docs and remove overclaiming language

### Week 2
- implement hybrid runtime in `kvrm-gpu`
- add calibration and abstention
- standardize metrics schema

### Week 3
- add registry-evolution benchmark suite
- reframe `kvrm-llm-compiler` as bounded canonicalization
- repair `kvrm-os` benchmark harness

### Week 4
- build one new vertical demo: SOC playbook routing or drone mission-policy routing
- draft flagship paper outline and figure set

---

## Hard rules going forward

1. No critical-infrastructure claims without shadow-mode evidence.
2. No “formal verification” language without proof artifacts.
3. Every benchmark must include non-neural baselines.
4. Every selector must report abstention/fallback behavior.
5. Every application demo must use deterministic execution or human-reviewed handoff.
6. Every subproject must declare whether it is active-core, domain-adapter, or archived.

---

## Immediate next implementation tasks

1. Create a small canonical `KVRM Core Spec` doc in root docs.
2. Clean the root so only active KVRM subprojects remain.
3. Implement hybrid profile/retrieval/compact-selector runtime in `kvrm-gpu`.
4. Add calibration and abstention metrics to all active benchmarks.
5. Repair `kvrm-os` benchmark realism before making any scheduler-performance claims.
6. Reframe `kvrm-llm-compiler` claims around bounded canonicalization and reference checking.

---

## Bottom line

If you want KVRM to become robust, the move is not to make it more grandiose.

The move is to make it narrower, sharper, safer, and more reproducible:
- bounded outputs
- hybrid selection
- abstention
- deterministic validation
- shadow-mode evidence
- clean domain-specific demos

That version can become a serious research program.