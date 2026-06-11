# KVRM vs Small-Model LLM Baseline

Generated: 2026-04-13T19:19:31.556339+00:00

## Scope

This report compares live hybrid KVRM against real Ollama-backed small-model selector baselines
on the current six-domain canonical suite. Evaluated models:
`qwen3.5:0.8b, gemma4:e2b`.
The baseline is charitable: it receives
the live registry action ids and descriptions, the live feature schema, and up to two
representative supported examples per action, then must choose an action or abstain
via strict JSON output.

## Overall Summary

| Model | Macro Semantic | Macro False Accept | Macro Unsupported Rejection | Macro Invalid Output | Macro Mean Cost |
|---|---:|---:|---:|---:|---:|
| qwen3.5:0.8b | 0.5141 | 1.0000 | 0.0000 | 0.0000 | 0.6970 |
| gemma4:e2b | 0.5971 | 0.7741 | 0.0027 | 0.2049 | 0.5706 |
| KVRM hybrid | 0.9934 | 0.0000 | 1.0000 | 0.0000 | 0.0017 |

## Per-Domain Results

### SOC

| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |
|---|---:|---:|---:|---:|---:|---:|
| KVRM hybrid | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| qwen3.5:0.8b | 0.4545 | 1.0000 | 0.0000 | 0.0000 | 0.4038 | 0.7579 |
| gemma4:e2b | 0.6136 | 1.0000 | 0.0000 | 0.0000 | 0.5769 | 0.6468 |

### SRE

| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |
|---|---:|---:|---:|---:|---:|---:|
| KVRM hybrid | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| qwen3.5:0.8b | 0.6383 | 1.0000 | 0.0000 | 0.0000 | 0.6508 | 0.6536 |
| gemma4:e2b | 0.8617 | 0.9783 | 0.0217 | 0.0000 | 0.8571 | 0.4946 |

### DRONE

| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |
|---|---:|---:|---:|---:|---:|---:|
| KVRM hybrid | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| qwen3.5:0.8b | 0.3673 | 1.0000 | 0.0000 | 0.0000 | 0.3514 | 0.8356 |
| gemma4:e2b | 0.8571 | 1.0000 | 0.0000 | 0.0000 | 0.8243 | 0.5068 |

### GRID

| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |
|---|---:|---:|---:|---:|---:|---:|
| KVRM hybrid | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| qwen3.5:0.8b | 0.5000 | 1.0000 | 0.0000 | 0.0000 | 0.5000 | 0.6875 |
| gemma4:e2b | 0.6111 | 1.0000 | 0.0000 | 0.0000 | 0.6111 | 0.6042 |

### FINANCE

| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |
|---|---:|---:|---:|---:|---:|---:|
| KVRM hybrid | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| qwen3.5:0.8b | 0.6111 | 1.0000 | 0.0000 | 0.0000 | 0.6000 | 0.6042 |
| gemma4:e2b | 0.6667 | 1.0000 | 0.0000 | 0.0000 | 0.4000 | 0.5625 |

### MEDICAL

| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |
|---|---:|---:|---:|---:|---:|---:|
| KVRM hybrid | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| qwen3.5:0.8b | 0.7222 | 1.0000 | 0.0000 | 0.0000 | 0.7000 | 0.5208 |
| gemma4:e2b | 0.8333 | 1.0000 | 0.0000 | 0.0000 | 0.8000 | 0.4375 |

### CUSTOMER_SUPPORT

| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |
|---|---:|---:|---:|---:|---:|---:|
| KVRM hybrid | 0.9722 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0073 |
| qwen3.5:0.8b | 0.4444 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.7292 |
| gemma4:e2b | 0.0833 | 0.0000 | 0.0000 | 0.9167 | 0.0000 | 0.6875 |

### CONTENT_MODERATION

| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |
|---|---:|---:|---:|---:|---:|---:|
| KVRM hybrid | 0.9750 | 0.0000 | 1.0000 | 0.0000 | 0.9697 | 0.0065 |
| qwen3.5:0.8b | 0.3750 | 1.0000 | 0.0000 | 0.0000 | 0.3030 | 0.7870 |
| gemma4:e2b | 0.2500 | 0.2143 | 0.0000 | 0.7222 | 0.1212 | 0.6250 |

## Interpretation

- This baseline is a real small-model LLM comparison, not the old sklearn proxy.
- The baseline is still only a selector. It does not get KVRM's support gate, strict runtime validation, or deterministic executor boundary.
- `qwen3.5:0.8b` behaves like an over-aggressive classifier: macro semantic is `0.5141`, but it nearly always executes on unsupported cases (`false_accept_rate=1.0000`, `unsupported_rejection_rate=0.0000`), driving `mean_decision_cost=0.6970`.
- `gemma4:e2b` behaves like an over-aggressive classifier: macro semantic is `0.5971`, but it nearly always executes on unsupported cases (`false_accept_rate=0.7741`, `unsupported_rejection_rate=0.0027`), driving `mean_decision_cost=0.5706`.
- Either way, the comparison still favors KVRM on the paper's actual claim axis: supported routing accuracy plus fail-closed open-world behavior under a live registry contract.

## Artifact Outputs

- consolidated JSON: `baselines/qwen-baseline/outputs/ollama/live_canonical/consolidated_comparison.json`
- combined metrics: `baselines/qwen-baseline/outputs/ollama/live_canonical/combined_metrics.json`
- per-run artifacts under: `baselines/qwen-baseline/outputs/ollama/live_canonical`
