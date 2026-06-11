# KVRM Flagship Benchmark Report

Date: 2026-04-03
Status: active working report — now includes classifier baseline comparison

## Executive Summary

KVRM is a bounded-action architecture for safety-critical AI routing. This report
presents the first head-to-head comparison between KVRM's hybrid routing runtime
and strong classifier baselines (sklearn Random Forest / Gradient Boosting as
upper-bound proxies for fine-tuned 0.5-0.8B language models).

Key findings:
1. KVRM achieves 100% unsupported-case rejection across all domains. The classifier achieves 0% (direct/constrained) or 25-75% (thresholded JSON).
2. KVRM achieves 0% false-accept rate. The classifier false-accepts 25-100% of unsupported inputs.
3. Under incompatible registry mutation, the classifier produces 19-44% stale labels. KVRM produces 0% by construction.
4. On supported-case accuracy, the classifier matches or slightly trails KVRM depending on domain.

The structural advantage is measurable and consistent across all three domains.

---

## KVRM Suite Results (Hybrid Router)

### SRE Policy Router
- Supported cases: 12 | Unsupported: 4
- Semantic correctness: 1.000
- OOD supported accuracy: 1.000
- Unsupported rejection: 1.000
- False accept rate: 0.000
- Structural validity: 1.000

### SOC Playbook Router
- Supported cases: 12 | Unsupported: 4
- Semantic correctness: 0.917
- OOD supported accuracy: 0.857
- Unsupported rejection: 1.000
- False accept rate: 0.000
- Structural validity: 1.000

### Drone Mission Router
- Supported cases: 12 | Unsupported: 4
- Semantic correctness: 0.917
- OOD supported accuracy: 0.833
- Unsupported rejection: 1.000
- False accept rate: 0.000
- Structural validity: 1.000

---

## Classifier Baseline Results

Baseline: sklearn Random Forest / Gradient Boosting (upper-bound proxy
for a fine-tuned 0.5-0.8B language model on these small datasets).

Three variants tested per the comparison protocol:
- A) Direct label: predict one action label, no rejection
- B) JSON action: predict label + confidence, reject below threshold (0.60)
- C) Constrained: forced-choice from label set, no rejection

### SRE Domain

| Metric                  | KVRM Hybrid | RF Direct | GBM JSON | RF Constrained |
|-------------------------|-------------|-------------|-----------|------------------|
| Semantic Correctness    | 1.000       | 1.000       | 1.000     | 1.000            |
| Structural Validity     | 1.000       | 1.000       | 1.000     | 1.000            |
| False Accept Rate       | 0.000       | 1.000       | 1.000     | 1.000            |
| Unsupported Rejection   | 1.000       | 0.000       | 0.000     | 0.000            |
| OOD Accuracy (supp.)    | 1.000       | 1.000       | 1.000     | 1.000            |

SRE is the "easy domain" — both KVRM and the baseline nail supported accuracy.
But the baseline false-accepts 100% of unsupported cases across all variants.
Even the thresholded JSON variant fails to reject because the classifier is
overconfident on OOD inputs it has never seen.

### SOC Domain

| Metric                  | KVRM Hybrid | RF Direct | GBM JSON | RF Constrained |
|-------------------------|-------------|-------------|-----------|------------------|
| Semantic Correctness    | 0.917       | 0.750       | 0.667     | 0.750            |
| Structural Validity     | 1.000       | 1.000       | 1.000     | 1.000            |
| False Accept Rate       | 0.000       | 1.000       | 0.750     | 1.000            |
| Unsupported Rejection   | 1.000       | 0.000       | 0.250     | 0.000            |
| OOD Accuracy (supp.)    | 0.857       | N/A         | N/A       | N/A              |

KVRM outperforms on both accuracy AND safety. The baseline not only misclassifies
more supported cases, it also false-accepts most unsupported inputs. The JSON
variant rejects 25% of unsupported inputs — better, but nowhere near 100%.

### Drone Domain

| Metric                  | KVRM Hybrid | RF Direct | GBM JSON | RF Constrained |
|-------------------------|-------------|-------------|-----------|------------------|
| Semantic Correctness    | 0.917       | 0.833       | 0.833     | 0.833            |
| Structural Validity     | 1.000       | 1.000       | 1.000     | 1.000            |
| False Accept Rate       | 0.000       | 1.000       | 0.250     | 1.000            |
| Unsupported Rejection   | 1.000       | 0.000       | 0.750     | 0.000            |
| OOD Accuracy (supp.)    | 0.833       | N/A         | N/A       | N/A              |

Same pattern: KVRM wins on accuracy and wins decisively on rejection/safety.
The JSON variant's thresholding helps on drone (75% rejection) but still
misses 25% of unsupported cases.

---

## Registry Evolution Tests

What happens when the action registry changes after training?

KVRM validates every prediction against the live registry at runtime.
Stale label rate: 0% by construction, for any mutation.

### Baseline under incompatible registry mutation (rename first 2 actions)

| Domain | Direct Label | JSON Action | Constrained |
|--------|-------------|-------------|-------------|
| SRE    | 37.5% stale | 43.8% stale | 37.5% stale |
| SOC    | 31.3% stale | 31.3% stale | 31.3% stale |
| Drone  | 18.8% stale | 18.8% stale | 18.8% stale |

Under append-only and reorder mutations, the baseline survives (the old labels
still exist). But under incompatible mutation — actions renamed or removed —
the baseline silently emits labels that no longer exist in the registry.

This is a deployment-critical failure mode. In SOC/SRE/drone contexts,
executing a non-existent action could mean triggering the wrong remediation,
the wrong isolation procedure, or the wrong flight maneuver.

KVRM never emits a stale label by construction.

---

## What This Proves

### KVRM's structural advantage is measurable, not hypothetical

1. **False-accept rate**: KVRM 0% vs baseline 25-100% depending on variant/domain
2. **Unsupported rejection**: KVRM 100% vs baseline 0-75%
3. **Registry evolution**: KVRM 0% stale labels vs baseline 19-44% under incompatible mutation
4. **Supported accuracy**: KVRM matches or exceeds the baseline (not behind)

### Where the baseline matches KVRM

- On supported-case accuracy in simple domains (SRE), the baseline ties KVRM
- A single model is simpler to deploy than the full KVRM runtime
- For purely closed-set classification with no safety requirements, a fine-tuned LM suffices

### Where the baseline fails

- Cannot reject unsupported inputs without ad-hoc confidence thresholding
- Even with thresholding, rejection is unreliable (0-75% vs KVRM's 100%)
- Cannot handle registry evolution without retraining
- No validator/executor boundary — model output goes directly to execution
- No audit trail with candidate scores, validation reasons, fallback decisions

---

## Bottom Line

The question was: "Why not just fine-tune a small classifier model?"

The answer: because fine-tuning gives you a classifier, not a deployment-grade
bounded-action runtime. The classifier may match KVRM on the easy metric
(supported-case accuracy on clean inputs) while failing on every metric that
matters for safety-critical deployment:
- unsupported rejection
- false-accept rate
- registry evolution robustness
- fail-closed behavior
- auditability

KVRM's value is the systems architecture, not the selector model.

---

## Artifacts

- KVRM demo comparison: `kvrm-demos/reports/demo_comparison.json`
- Baseline outputs: `baselines/qwen-baseline/outputs/{sre,soc,drone}/`
- Registry evolution results: `baselines/qwen-baseline/outputs/registry_evolution/`
- Full comparison report: `docs/reports/KVRM_VS_QWEN_COMPARISON.md`
- Consolidated JSON: `baselines/qwen-baseline/outputs/consolidated_comparison.json`
- Comparison protocol: `docs/specs/QWEN_BASELINE_COMPARISON_PROTOCOL.md`
- Architecture analysis: `docs/strategy/KVRM_ARCHITECTURE_MOAT.md`
