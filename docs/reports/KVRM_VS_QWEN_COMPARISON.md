# KVRM vs Classifier Baseline: Comparison Report

Generated: 2026-04-03

## Executive Summary

This report compares the KVRM bounded-action architecture against
strong sklearn classifier baselines (Random Forest / Gradient Boosting,
used as upper-bound proxies for fine-tuned 0.5-0.8B language models)
across three domains: SRE, SOC, and Drone mission routing.

The sklearn classifiers are intentionally strong — random forests and
gradient boosting with enough capacity to memorize the small training
sets. This represents an upper-bound estimate of what a fine-tuned
small LM could achieve on these datasets.

---

## SRE Domain

| Metric | KVRM Hybrid | RF Direct | GBM JSON | RF Constrained |
|--------|-------------|-------------|-----------|------------------|
| Semantic Correctness | 1.000 | 1.000 | 1.000 | 1.000 |
| Structural Validity | 1.000 | 1.000 | 1.000 | 1.000 |
| False Accept Rate | 0.000 | 1.000 | 1.000 | 1.000 |
| Unsupported Rejection | 1.000 | 0.000 | 0.000 | 0.000 |
| OOD Accuracy (supported) | 1.000 | 1.000 | 1.000 | 1.000 |
| Abstention Rate | 0.250 | 0.000 | 0.000 | 0.000 |
| Fallback Rate | 0.250 | 0.000 | 0.000 | 0.000 |

## SOC Domain

| Metric | KVRM Hybrid | RF Direct | GBM JSON | RF Constrained |
|--------|-------------|-------------|-----------|------------------|
| Semantic Correctness | 0.917 | 0.750 | 0.667 | 0.750 |
| Structural Validity | 1.000 | 1.000 | 1.000 | 1.000 |
| False Accept Rate | 0.000 | 1.000 | 0.750 | 1.000 |
| Unsupported Rejection | 1.000 | 0.000 | 0.250 | 0.000 |
| OOD Accuracy (supported) | 0.857 | 0.714 | 0.571 | 0.714 |
| Abstention Rate | 0.250 | 0.000 | 0.250 | 0.000 |
| Fallback Rate | 0.250 | 0.000 | 0.250 | 0.000 |

## DRONE Domain

| Metric | KVRM Hybrid | RF Direct | GBM JSON | RF Constrained |
|--------|-------------|-------------|-----------|------------------|
| Semantic Correctness | 0.917 | 0.833 | 0.833 | 0.833 |
| Structural Validity | 1.000 | 1.000 | 1.000 | 1.000 |
| False Accept Rate | 0.000 | 1.000 | 0.250 | 1.000 |
| Unsupported Rejection | 1.000 | 0.000 | 0.750 | 0.000 |
| OOD Accuracy (supported) | 0.833 | 0.667 | 0.667 | 0.667 |
| Abstention Rate | 0.250 | 0.000 | 0.250 | 0.000 |
| Fallback Rate | 0.250 | 0.000 | 0.250 | 0.000 |

## Registry Evolution Tests

These tests train the baseline on the original registry, then mutate
the registry and check whether predictions remain structurally valid.

KVRM validates every prediction against the live registry at runtime,
so it handles all mutations by construction (stale label rate = 0%).

| Domain | Variant | Mutation | Stale Label Rate | Structural Validity |
|--------|---------|----------|-----------------|-------------------|
| drone | constrained | append | 0.000 | 1.000 |
| drone | constrained | incompatible | 0.188 | 0.812 |
| drone | constrained | reorder | 0.000 | 1.000 |
| drone | direct_label | append | 0.000 | 1.000 |
| drone | direct_label | incompatible | 0.188 | 0.812 |
| drone | direct_label | reorder | 0.000 | 1.000 |
| drone | json_action | append | 0.000 | 1.000 |
| drone | json_action | incompatible | 0.188 | 0.812 |
| drone | json_action | reorder | 0.000 | 1.000 |
| soc | constrained | append | 0.000 | 1.000 |
| soc | constrained | incompatible | 0.312 | 0.688 |
| soc | constrained | reorder | 0.000 | 1.000 |
| soc | direct_label | append | 0.000 | 1.000 |
| soc | direct_label | incompatible | 0.312 | 0.688 |
| soc | direct_label | reorder | 0.000 | 1.000 |
| soc | json_action | append | 0.000 | 1.000 |
| soc | json_action | incompatible | 0.312 | 0.688 |
| soc | json_action | reorder | 0.000 | 1.000 |
| sre | constrained | append | 0.000 | 1.000 |
| sre | constrained | incompatible | 0.375 | 0.625 |
| sre | constrained | reorder | 0.000 | 1.000 |
| sre | direct_label | append | 0.000 | 1.000 |
| sre | direct_label | incompatible | 0.375 | 0.625 |
| sre | direct_label | reorder | 0.000 | 1.000 |
| sre | json_action | append | 0.000 | 1.000 |
| sre | json_action | incompatible | 0.438 | 0.562 |
| sre | json_action | reorder | 0.000 | 1.000 |

## Analysis: Where KVRM Wins

### 1. Unsupported Case Rejection
KVRM achieves 100% unsupported-case rejection across all domains
because abstention is a first-class runtime behavior, not a post-hoc
threshold on model confidence.

The direct-label and constrained baselines have 0% rejection rate
— they always output a label, even for cases outside the supported
action space. This is the false-accept problem.

### 2. Registry Evolution Robustness
When the registry changes (actions added, removed, renamed), the
baseline model continues emitting labels from its training set.
Under incompatible mutations, this produces structurally invalid
predictions — stale labels that no longer exist in the registry.

KVRM never emits a label outside the current registry by construction.

### 3. Deterministic Validation Boundary
Every KVRM prediction passes through a validator that checks:
- action_id exists in registry
- parameters match the action's schema
- no execution without validation

No baseline variant provides this. Even constrained decoding only
limits the label set — it does not validate parameters or enforce
the executor boundary.

## Analysis: Where Classifier Baseline Wins

### 1. Simplicity
A single fine-tuned model is simpler to deploy than the full KVRM
runtime (registry + selector + validator + executor + calibrator).

### 2. Possible Raw Accuracy
On some domains, the baseline may match or exceed KVRM on
supported-case accuracy, especially when the selector's rule/retrieval
cascade has gaps.

## Bottom Line

The comparison confirms the architectural thesis: KVRM's value is not in
classification accuracy (where a fine-tuned classifier can compete) but in
the systems-architecture properties that a classifier alone cannot
provide:

1. **Fail-closed abstention** on unsupported inputs
2. **Registry-validated execution** preventing stale labels
3. **Deterministic validator/executor boundary** ensuring auditability
4. **Registry evolution robustness** without retraining

These are deployment-critical properties for safety-sensitive domains
(SOC, SRE, autonomous systems) that no amount of fine-tuning provides.
