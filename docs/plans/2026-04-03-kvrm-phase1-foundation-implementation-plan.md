# KVRM Phase 1 Foundation Implementation Plan

> For Hermes: implement this plan before building any new application demo. The point of Phase 1 is to create one clean KVRM core and one shared benchmark foundation that all future demos can plug into.

Goal: build the KVRM Phase 1 foundation — a shared core package, shared schemas, shared benchmark harness, shared artifact format, and minimal toy end-to-end example — so future demos like SOC, SRE, drone, medical, and finance routing all use the same architecture.

Architecture: KVRM Phase 1 is a bounded decision runtime for finite audited action spaces. The foundation should support: registry loading, state encoding, baseline selection, calibrated confidence, abstention, deterministic validation, deterministic execution/handoff, and full audit logging. Keep this small, explicit, and testable. Do not inherit unnecessary complexity from existing subprojects.

Tech Stack: Python 3.10+, Pydantic 2, pytest, standard library JSON/hashlib/pathlib/dataclasses/typing, optional NumPy for small baseline selectors only if needed.

---

## Ground rules

1. Do not anchor implementation to old subprojects unless a piece is clearly reusable.
2. Do not use a large LLM in the runtime path for Phase 1.
3. Prefer a tiny, explicit, boring implementation over a “clever” one.
4. Every interface should be serializable to JSON for replay.
5. Every non-trivial code addition gets a test first.
6. Keep Phase 1 demo-free except for a tiny toy benchmark proving the foundation works.
7. No “formal verification” wording anywhere in Phase 1 docs.

---

## Recommended file layout

Create these new directories and files under `/Users/bobbyprice/projects/KVRM/`.

### New top-level directories
- `docs/specs/`
- `kvrm-core/`
- `kvrm-bench/`
- `tests/kvrm_core/`
- `tests/kvrm_bench/`

### New docs files
- `docs/specs/KVRM_CORE_SPEC.md`
- `docs/specs/KVRM_REGISTRY_SCHEMA.md`
- `docs/specs/KVRM_METRICS_SCHEMA.md`
- `docs/specs/KVRM_ARTIFACTS_SCHEMA.md`

### New package files for `kvrm-core/`
- `kvrm-core/pyproject.toml`
- `kvrm-core/README.md`
- `kvrm-core/src/kvrm_core/__init__.py`
- `kvrm-core/src/kvrm_core/types.py`
- `kvrm-core/src/kvrm_core/registry.py`
- `kvrm-core/src/kvrm_core/context.py`
- `kvrm-core/src/kvrm_core/selectors.py`
- `kvrm-core/src/kvrm_core/calibration.py`
- `kvrm-core/src/kvrm_core/validation.py`
- `kvrm-core/src/kvrm_core/execution.py`
- `kvrm-core/src/kvrm_core/runtime.py`
- `kvrm-core/src/kvrm_core/logging.py`
- `kvrm-core/src/kvrm_core/artifacts.py`
- `kvrm-core/examples/toy_registry.json`
- `kvrm-core/examples/toy_cases.jsonl`

### New package files for `kvrm-bench/`
- `kvrm-bench/pyproject.toml`
- `kvrm-bench/README.md`
- `kvrm-bench/src/kvrm_bench/__init__.py`
- `kvrm-bench/src/kvrm_bench/metrics.py`
- `kvrm-bench/src/kvrm_bench/datasets.py`
- `kvrm-bench/src/kvrm_bench/runner.py`
- `kvrm-bench/src/kvrm_bench/reporting.py`
- `kvrm-bench/src/kvrm_bench/replay.py`
- `kvrm-bench/src/kvrm_bench/mutations.py`
- `kvrm-bench/examples/toy_benchmark.py`

### New tests
- `tests/kvrm_core/test_registry.py`
- `tests/kvrm_core/test_calibration.py`
- `tests/kvrm_core/test_validation.py`
- `tests/kvrm_core/test_runtime.py`
- `tests/kvrm_core/test_artifacts.py`
- `tests/kvrm_bench/test_metrics.py`
- `tests/kvrm_bench/test_runner.py`
- `tests/kvrm_bench/test_replay.py`
- `tests/kvrm_bench/test_mutations.py`

---

## Phase 1 acceptance criteria

Phase 1 is done only when all of these are true:

1. A registry JSON file can be parsed and validated.
2. A small set of toy cases can be run end-to-end.
3. The runtime can return either a valid action or abstain.
4. Validation failures trigger deterministic fallback or fail-closed behavior.
5. Each run emits standard artifacts:
   - `config.json`
   - `registry.json`
   - `metrics.json`
   - `per_case_results.jsonl`
   - `summary.md`
6. Replay can reconstruct outcomes from the logged artifact set.
7. Registry mutation helpers support append-only, reorder-only, and incompatible mutation cases.
8. Tests pass cleanly with one command.

Suggested verification command at the end:
- `pytest tests/kvrm_core tests/kvrm_bench -q`

---

## Task 1: Create the spec documents

**Objective:** freeze the Phase 1 architecture before writing implementation code.

**Files:**
- Create: `docs/specs/KVRM_CORE_SPEC.md`
- Create: `docs/specs/KVRM_REGISTRY_SCHEMA.md`
- Create: `docs/specs/KVRM_METRICS_SCHEMA.md`
- Create: `docs/specs/KVRM_ARTIFACTS_SCHEMA.md`

### Step 1: Write `KVRM_CORE_SPEC.md`

Include these sections exactly:
- Purpose
- Non-goals
- Canonical runtime order
- Required abstractions
- Required failure modes
- Logging requirements
- Serialization requirements
- Phase 1 exclusions

Minimum content to include:
- runtime order from registry load through execution and logging
- explicit abstain support
- explicit fallback/fail-closed support
- no LLM requirement in runtime path

### Step 2: Write `KVRM_REGISTRY_SCHEMA.md`

Include:
- JSON schema examples for action registry
- stable action IDs
- version
- digest
- parameter schemas
- append-only compatibility notes

Required example registry item:
```json
{
  "action_id": "request_human_triage",
  "name": "Request Human Triage",
  "description": "Escalate to human review when confidence is low or unsupported conditions are present.",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "reason": {"type": "string"}
    },
    "required": ["reason"]
  }
}
```

### Step 3: Write `KVRM_METRICS_SCHEMA.md`

Define each metric with semantics:
- structural_validity_rate
- semantic_correctness_rate
- abstention_rate
- fallback_rate
- invalid_output_rate
- false_accept_rate
- latency_p50_ms
- latency_p95_ms
- latency_p99_ms
- calibration_ece
- ood_accuracy_supported_only
- unsupported_case_rejection_rate

### Step 4: Write `KVRM_ARTIFACTS_SCHEMA.md`

Define the exact artifact tree:
- run directory layout
- file semantics
- required JSON keys for each artifact file

### Step 5: Verify document coherence

Run a manual checklist:
- all specs agree on field names
- no metrics appear in one spec but not others
- examples are copy-pasteable JSON

### Step 6: Commit

Suggested commit:
```bash
git add docs/specs
git commit -m "docs: add KVRM phase1 core and schema specs"
```

---

## Task 2: Scaffold the `kvrm-core` package

**Objective:** create the minimal package skeleton with clean imports and packaging.

**Files:**
- Create: `kvrm-core/pyproject.toml`
- Create: `kvrm-core/README.md`
- Create: `kvrm-core/src/kvrm_core/__init__.py`
- Create: `kvrm-core/src/kvrm_core/types.py`

### Step 1: Write failing import test

Create `tests/kvrm_core/test_registry.py` with an initial import smoke test:
```python
def test_kvrm_core_imports_cleanly():
    import kvrm_core
    assert kvrm_core is not None
```

### Step 2: Run the failing test

Run:
```bash
pytest tests/kvrm_core/test_registry.py::test_kvrm_core_imports_cleanly -q
```
Expected: fail because package does not exist yet.

### Step 3: Create `kvrm-core/pyproject.toml`

Use a clean setuptools layout with `src/`.
Required dependencies:
- `pydantic>=2`
- optionally `numpy>=1.24` only if needed later

Do not add heavy ML deps here yet.

### Step 4: Create `__init__.py`

Export the future public surface explicitly:
- Registry types
- selectors
- runtime result types

### Step 5: Create `types.py`

Define core Pydantic or dataclass models for:
- `ActionSpec`
- `RegistrySpec`
- `DecisionInput`
- `DecisionCandidate`
- `DecisionResult`
- `ValidationResult`
- `ExecutionResult`
- `AuditRecord`

### Step 6: Re-run the import test

Run:
```bash
pytest tests/kvrm_core/test_registry.py::test_kvrm_core_imports_cleanly -q
```
Expected: pass.

### Step 7: Commit

Suggested commit:
```bash
git add kvrm-core tests/kvrm_core/test_registry.py
git commit -m "feat: scaffold kvrm-core package"
```

---

## Task 3: Implement registry loading and digesting

**Objective:** make the registry concrete, validated, and hashable.

**Files:**
- Create: `kvrm-core/src/kvrm_core/registry.py`
- Modify: `kvrm-core/src/kvrm_core/types.py`
- Modify: `tests/kvrm_core/test_registry.py`
- Create: `kvrm-core/examples/toy_registry.json`

### Step 1: Write failing tests

Add these tests:
- registry loads from JSON
- action IDs are unique
- digest is stable for identical registry content
- reorder-only change can be detected separately from append-only change

Example test names:
```python
def test_registry_loads_from_json(tmp_path): ...
def test_registry_rejects_duplicate_action_ids(tmp_path): ...
def test_registry_digest_is_stable(tmp_path): ...
```

### Step 2: Run tests to confirm failure

Run:
```bash
pytest tests/kvrm_core/test_registry.py -q
```

### Step 3: Implement `registry.py`

Required functions/classes:
- `load_registry(path) -> RegistrySpec`
- `compute_registry_digest(registry) -> str`
- `validate_registry(registry) -> None`
- `canonical_registry_payload(registry) -> dict`

Use deterministic JSON serialization for digesting.

### Step 4: Create `toy_registry.json`

Use 5–8 toy actions, including one explicit abstain/handoff action.
Suggested actions:
- `allow_low_risk`
- `throttle_temporarily`
- `block_request`
- `collect_more_context`
- `request_human_review`

### Step 5: Re-run tests

Run:
```bash
pytest tests/kvrm_core/test_registry.py -q
```
Expected: all registry tests pass.

### Step 6: Commit

Suggested commit:
```bash
git add kvrm-core/src/kvrm_core/registry.py kvrm-core/examples/toy_registry.json tests/kvrm_core/test_registry.py
git commit -m "feat: add validated registry loading and digests"
```

---

## Task 4: Implement selection interfaces and minimal baselines

**Objective:** define selectors without binding to a specific domain.

**Files:**
- Create: `kvrm-core/src/kvrm_core/selectors.py`
- Modify: `kvrm-core/src/kvrm_core/types.py`
- Create: `kvrm-core/src/kvrm_core/context.py`
- Create: `kvrm-core/examples/toy_cases.jsonl`
- Create: `tests/kvrm_core/test_runtime.py`

### Step 1: Write failing tests for selector protocol

Tests should cover:
- rule selector returns a valid action
- retrieval selector returns nearest support action when exact match exists
- selector can return abstain

Example test names:
```python
def test_rule_selector_returns_known_action(): ...
def test_retrieval_selector_returns_supported_action(): ...
def test_selector_can_abstain(): ...
```

### Step 2: Implement selector protocol

In `selectors.py`, define:
- `BaseSelector`
- `RuleSelector`
- `RetrievalSelector`
- `ConstantAbstainSelector`

Do not implement ML-heavy selectors yet.

### Step 3: Implement simple context serialization

In `context.py`, define utilities to:
- normalize feature dicts
- ensure JSON-serializable order
- create a stable feature key for retrieval matching

### Step 4: Create `toy_cases.jsonl`

Add a tiny benchmark set with structured features and gold actions.
Each case should include:
- case_id
- input_features
- expected_action_id
- supported boolean

### Step 5: Re-run tests

Run:
```bash
pytest tests/kvrm_core/test_runtime.py -q
```

### Step 6: Commit

Suggested commit:
```bash
git add kvrm-core/src/kvrm_core/selectors.py kvrm-core/src/kvrm_core/context.py kvrm-core/examples/toy_cases.jsonl tests/kvrm_core/test_runtime.py
git commit -m "feat: add selector interfaces and toy baseline selectors"
```

---

## Task 5: Implement calibration and abstention

**Objective:** make confidence meaningful from day one.

**Files:**
- Create: `kvrm-core/src/kvrm_core/calibration.py`
- Create: `tests/kvrm_core/test_calibration.py`
- Modify: `kvrm-core/src/kvrm_core/types.py`

### Step 1: Write failing tests

Required tests:
- confidence threshold causes abstention below threshold
- pass-through above threshold
- support-distance or simple confidence utility returns deterministic values

Example:
```python
def test_threshold_calibrator_abstains_below_threshold(): ...
def test_threshold_calibrator_keeps_action_above_threshold(): ...
```

### Step 2: Implement simple calibration layer

Add:
- `ThresholdCalibrator`
- `DistanceRejector` or a simple support-distance helper
- `apply_abstention_policy(candidates, threshold)`

Keep this intentionally simple for Phase 1.

### Step 3: Re-run tests

Run:
```bash
pytest tests/kvrm_core/test_calibration.py -q
```

### Step 4: Commit

Suggested commit:
```bash
git add kvrm-core/src/kvrm_core/calibration.py tests/kvrm_core/test_calibration.py
git commit -m "feat: add calibration and abstention primitives"
```

---

## Task 6: Implement deterministic validation and execution interfaces

**Objective:** enforce that selected actions are checked before execution.

**Files:**
- Create: `kvrm-core/src/kvrm_core/validation.py`
- Create: `kvrm-core/src/kvrm_core/execution.py`
- Create: `tests/kvrm_core/test_validation.py`

### Step 1: Write failing tests

Required tests:
- unsupported action is rejected
- schema-invalid parameters are rejected
- precondition failure triggers fail-closed or fallback
- valid action executes through deterministic executor

### Step 2: Implement validator

Required components:
- action existence check
- parameter key validation
- optional per-action precondition callback support
- explicit reason codes for rejection

### Step 3: Implement executor interface

Required components:
- `BaseExecutor`
- `DictionaryExecutor` or small deterministic toy executor
- explicit execution status enum

### Step 4: Re-run tests

Run:
```bash
pytest tests/kvrm_core/test_validation.py -q
```

### Step 5: Commit

Suggested commit:
```bash
git add kvrm-core/src/kvrm_core/validation.py kvrm-core/src/kvrm_core/execution.py tests/kvrm_core/test_validation.py
git commit -m "feat: add deterministic validation and execution interfaces"
```

---

## Task 7: Implement runtime orchestration and audit logging

**Objective:** connect registry, selector, calibration, validation, and execution in one runtime.

**Files:**
- Create: `kvrm-core/src/kvrm_core/runtime.py`
- Create: `kvrm-core/src/kvrm_core/logging.py`
- Modify: `tests/kvrm_core/test_runtime.py`

### Step 1: Write failing runtime tests

Required tests:
- runtime returns executed result for valid high-confidence case
- runtime abstains on low-confidence case
- runtime falls back or fails closed on validation failure
- runtime writes an audit record with all expected fields

### Step 2: Implement `runtime.py`

Required public class:
- `KVRMRuntime`

Required method:
- `decide_and_execute(input_case) -> DecisionResult`

Runtime must perform the canonical order:
- registry
- selector
- calibration
- abstain
- validate
- execute/fallback
- audit log

### Step 3: Implement `logging.py`

Add:
- JSONL audit record serializer
- helpers for converting runtime outputs to dicts

### Step 4: Re-run runtime tests

Run:
```bash
pytest tests/kvrm_core/test_runtime.py -q
```

### Step 5: Commit

Suggested commit:
```bash
git add kvrm-core/src/kvrm_core/runtime.py kvrm-core/src/kvrm_core/logging.py tests/kvrm_core/test_runtime.py
git commit -m "feat: add KVRM runtime orchestration and audit logging"
```

---

## Task 8: Implement artifact writing

**Objective:** standardize run outputs before creating benchmark logic.

**Files:**
- Create: `kvrm-core/src/kvrm_core/artifacts.py`
- Create: `tests/kvrm_core/test_artifacts.py`

### Step 1: Write failing tests

Required tests:
- artifact directory is created
- required files are written
- metrics/config/registry payloads are valid JSON
- per-case results are JSONL

### Step 2: Implement artifact writer

Required function:
- `write_run_artifacts(output_dir, config, registry, metrics, cases, summary_markdown)`

Must write:
- `config.json`
- `registry.json`
- `metrics.json`
- `per_case_results.jsonl`
- `summary.md`

### Step 3: Re-run tests

Run:
```bash
pytest tests/kvrm_core/test_artifacts.py -q
```

### Step 4: Commit

Suggested commit:
```bash
git add kvrm-core/src/kvrm_core/artifacts.py tests/kvrm_core/test_artifacts.py
git commit -m "feat: add standard KVRM artifact writer"
```

---

## Task 9: Scaffold the `kvrm-bench` package

**Objective:** create one shared benchmark harness package.

**Files:**
- Create: `kvrm-bench/pyproject.toml`
- Create: `kvrm-bench/README.md`
- Create: `kvrm-bench/src/kvrm_bench/__init__.py`
- Create: `kvrm-bench/src/kvrm_bench/metrics.py`
- Create: `tests/kvrm_bench/test_metrics.py`

### Step 1: Write failing import and metrics tests

Required tests:
- package imports cleanly
- metric aggregation on a small sample set is correct

### Step 2: Implement `metrics.py`

Add functions to compute:
- structural validity rate
- correctness rate
- abstention rate
- fallback rate
- invalid output rate
- false accept rate
- latency percentiles

Keep calibration ECE as a simple placeholder utility if no probabilities are available yet.

### Step 3: Re-run tests

Run:
```bash
pytest tests/kvrm_bench/test_metrics.py -q
```

### Step 4: Commit

Suggested commit:
```bash
git add kvrm-bench tests/kvrm_bench/test_metrics.py
git commit -m "feat: scaffold benchmark package and metrics aggregation"
```

---

## Task 10: Implement dataset loading and benchmark runner

**Objective:** make toy benchmark runs reproducible.

**Files:**
- Create: `kvrm-bench/src/kvrm_bench/datasets.py`
- Create: `kvrm-bench/src/kvrm_bench/runner.py`
- Create: `tests/kvrm_bench/test_runner.py`
- Create: `kvrm-bench/examples/toy_benchmark.py`

### Step 1: Write failing tests

Required tests:
- dataset loader reads toy JSONL cases
- benchmark runner processes all cases
- runner emits aggregated metrics and per-case results

### Step 2: Implement dataset loader

Support:
- JSONL reading
- deterministic ordering
- optional supported/OOD flags per case

### Step 3: Implement runner

Required class:
- `BenchmarkRunner`

Required behavior:
- load registry
- load cases
- run runtime over all cases
- collect metrics
- hand results to artifact writer

### Step 4: Implement `toy_benchmark.py`

Copy-paste command should be:
```bash
python kvrm-bench/examples/toy_benchmark.py
```

It should generate a small run directory under a local `outputs/` folder.

### Step 5: Re-run tests

Run:
```bash
pytest tests/kvrm_bench/test_runner.py -q
```

### Step 6: Commit

Suggested commit:
```bash
git add kvrm-bench/src/kvrm_bench/datasets.py kvrm-bench/src/kvrm_bench/runner.py kvrm-bench/examples/toy_benchmark.py tests/kvrm_bench/test_runner.py
git commit -m "feat: add benchmark runner and toy benchmark"
```

---

## Task 11: Implement reporting and replay

**Objective:** make benchmark runs inspectable and reproducible.

**Files:**
- Create: `kvrm-bench/src/kvrm_bench/reporting.py`
- Create: `kvrm-bench/src/kvrm_bench/replay.py`
- Create: `tests/kvrm_bench/test_replay.py`

### Step 1: Write failing tests

Required tests:
- summary markdown is generated
- replay loads a prior run and reconstructs case counts/metrics

### Step 2: Implement reporting

Add:
- markdown summary builder
- compact comparison table formatter

### Step 3: Implement replay

Add:
- loader for `config.json`, `registry.json`, `metrics.json`, and `per_case_results.jsonl`
- integrity checks for missing files

### Step 4: Re-run tests

Run:
```bash
pytest tests/kvrm_bench/test_replay.py -q
```

### Step 5: Commit

Suggested commit:
```bash
git add kvrm-bench/src/kvrm_bench/reporting.py kvrm-bench/src/kvrm_bench/replay.py tests/kvrm_bench/test_replay.py
git commit -m "feat: add benchmark reporting and replay"
```

---

## Task 12: Implement registry mutation helpers

**Objective:** make registry-evolution testing part of the foundation, not an afterthought.

**Files:**
- Create: `kvrm-bench/src/kvrm_bench/mutations.py`
- Create: `tests/kvrm_bench/test_mutations.py`

### Step 1: Write failing tests

Required tests:
- append-only mutation adds new action while preserving old IDs
- reorder-only mutation changes order but not identity
- incompatible mutation changes semantics or IDs and is flagged

### Step 2: Implement mutation helpers

Required functions:
- `append_action(registry, action)`
- `reorder_actions(registry, order)`
- `make_incompatible_mutation(registry, ...)`
- `classify_registry_compatibility(old, new)`

### Step 3: Re-run tests

Run:
```bash
pytest tests/kvrm_bench/test_mutations.py -q
```

### Step 4: Commit

Suggested commit:
```bash
git add kvrm-bench/src/kvrm_bench/mutations.py tests/kvrm_bench/test_mutations.py
git commit -m "feat: add registry mutation and compatibility helpers"
```

---

## Task 13: End-to-end Phase 1 verification

**Objective:** prove the foundation works as one coherent system.

**Files:**
- Modify: `kvrm-core/README.md`
- Modify: `kvrm-bench/README.md`
- Optionally create: `docs/specs/PHASE1_VERIFICATION.md`

### Step 1: Run the full test suite

Run:
```bash
pytest tests/kvrm_core tests/kvrm_bench -q
```
Expected: all passing.

### Step 2: Run the toy benchmark

Run:
```bash
python kvrm-bench/examples/toy_benchmark.py
```
Expected:
- a run directory is created
- required artifact files exist
- summary markdown is readable

### Step 3: Replay the run

Run a replay helper command or small Python one-liner to load the run directory.
Expected:
- replay succeeds without manual patching

### Step 4: Update READMEs

`kvrm-core/README.md` should include:
- what KVRM Core is
- what it is not
- quickstart
- artifact examples

`kvrm-bench/README.md` should include:
- how to run the toy benchmark
- expected artifact tree
- how future demos should plug in

### Step 5: Commit

Suggested commit:
```bash
git add kvrm-core/README.md kvrm-bench/README.md tests docs/specs
git commit -m "docs: finalize phase1 verification and quickstart"
```

---

## Recommended implementation notes

### Note 1: Package naming

Use underscores for import packages:
- `kvrm_core`
- `kvrm_bench`

Use hyphens only for directory/project names:
- `kvrm-core`
- `kvrm-bench`

### Note 2: Avoid premature multi-repo coupling

Do not wire this foundation into `kvrm-gpu`, `kvrm-os`, or `kvrm-llm-compiler` during Phase 1.
Phase 1 should finish first as a clean, demo-agnostic kernel.

### Note 3: Avoid inherited packaging debt

Several current subprojects have packaging rough edges. Do not copy their path hacks, broad dependency lists, or malformed metadata patterns.

### Note 4: Keep toy benchmark small

The toy benchmark exists only to prove the foundation works. It should be tiny, deterministic, and fast.

---

## Suggested order of execution

Implement in exactly this order:

1. Specs
2. `kvrm-core` scaffold
3. Registry
4. Selectors/context
5. Calibration
6. Validation/execution
7. Runtime/logging
8. Artifacts
9. `kvrm-bench` scaffold
10. Metrics
11. Dataset/runner
12. Reporting/replay
13. Mutations
14. Final verification

---

## What comes immediately after Phase 1

Only after this plan is complete should Phase 2 begin:

1. Build `soc-playbook-router` on top of `kvrm_core` and `kvrm_bench`
2. Build `sre-policy-router` on top of the same stack
3. Add compact learned selectors where they actually beat rules/retrieval or improve abstention behavior

---

## Bottom line

Phase 1 is successful if it gives you one boring, rigorous, reusable KVRM substrate.

That substrate should make all future demos easier, more honest, and much stronger.
If Phase 1 gets flashy, it has already gone off the rails.