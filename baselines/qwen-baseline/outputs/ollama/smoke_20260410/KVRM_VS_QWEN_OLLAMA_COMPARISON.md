# KVRM vs Small-Model LLM Baseline

Generated: 2026-04-10T17:30:03.857595+00:00

## Scope

This report compares live hybrid KVRM against real Ollama-backed Qwen3 baselines
on the current six-domain canonical suite. The baseline is charitable: it receives
the live registry action ids and descriptions, the live feature schema, and up to two
representative supported examples per action, then must choose an action or abstain
via strict JSON output.

## Overall Summary

| Model | Macro Semantic | Macro False Accept | Macro Unsupported Rejection | Macro Invalid Output | Macro Mean Cost |
|---|---:|---:|---:|---:|---:|
| qwen3.5:0.8b | 0.6000 | 0.0000 | 0.0000 | 0.0000 | 0.4000 |
| batiai/gemma4-e2b:q4 | 0.8000 | 0.0000 | 0.0000 | 0.0000 | 0.2000 |
| KVRM hybrid | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |

## Per-Domain Results

### FINANCE

| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |
|---|---:|---:|---:|---:|---:|---:|
| KVRM hybrid | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| qwen3.5:0.8b | 0.6000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.4000 |
| batiai/gemma4-e2b:q4 | 0.8000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.2000 |

## Interpretation

- This baseline is a real small-model LLM comparison, not the old sklearn proxy.
- The baseline is still only a selector. It does not get KVRM's support gate, strict runtime validation, or deterministic executor boundary.
- `qwen3:0.6b` behaves like an over-aggressive classifier: it often executes on unsupported cases and pays heavily in false accepts and decision cost.
- `qwen3:1.7b` fails differently under the same strict structured-output protocol: it frequently emits empty-object responses, which count as invalid outputs rather than safe abstentions.
- Either way, the comparison still favors KVRM on the paper's actual claim axis: supported routing accuracy plus fail-closed open-world behavior under a live registry contract.

## Artifact Outputs

- consolidated JSON: `baselines/qwen-baseline/outputs/ollama/smoke_20260410/consolidated_comparison.json`
- combined metrics: `baselines/qwen-baseline/outputs/ollama/smoke_20260410/combined_metrics.json`
- per-run artifacts under: `baselines/qwen-baseline/outputs/ollama/smoke_20260410`
