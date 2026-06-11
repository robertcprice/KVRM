# Small-Model Ollama Baseline Comparison Protocol

Purpose: define a fair and rigorous comparison between KVRM and real small-model Ollama baselines.

## Goal

Test whether KVRM offers a meaningful advantage over a small language model selector on finite audited action-routing tasks.

Primary baseline family:
- evaluated live Ollama small models:
  - `qwen3:0.6b`
  - `qwen3:1.7b`
  - `qwen3.5:0.8b`
  - `gemma4:e2b`

Do not use a deliberately weak baseline.
The baseline should be given a serious, best-effort implementation.

## Tasks to benchmark

Use the live six-domain canonical suite:
1. SOC playbook router
2. SRE policy router
3. drone mission-policy router
4. grid operations router
5. finance risk workflow router
6. medical workflow router

## Data splits

For each domain, keep separate:
- train set
- validation set
- in-distribution test set
- supported OOD set
- unsupported/adversarial set

The same cases must be used for KVRM and Qwen.

## Baseline variants

Evaluate at least these Qwen variants:

### Live external-comparison variant
Input:
- live structured context
- live registry action ids and descriptions
- live feature schema
- up to two representative supported examples per action

Output:
- strict JSON with `decision`, `action_id`, `confidence`, `reason`

Important note:
This is a selector-only baseline. Even with structured output, it still does not inherit KVRM’s support gate, strict runtime validation, or deterministic validator/executor boundary.

Implementation note:
- reasoning-capable models are run through the Ollama `chat` API with thinking disabled so the benchmark measures selector quality rather than hidden-thought token burn or empty-answer failure modes

## Prompting protocol

- no leakage of unsupported evaluation examples into the few-shot context
- keep prompt format identical across domains where possible
- allow abstention explicitly
- require exact action ids or `null`

## Metrics to compare

### Closed-set metrics
- supported-case semantic correctness
- OOD supported accuracy
- latency

### Open-world metrics
- unsupported-case rejection rate
- false-accept rate on unsupported cases
- invalid-output rate

### Deployment / architecture metrics
- invalid-output behavior under strict structured output
- failure-mode clarity
- compatibility with deterministic validation

## Required fairness constraints

1. Same input information for KVRM and the external baseline.
2. Same registry labels.
3. Same evaluation cases.
4. Same supported vs unsupported definitions.
5. No hidden hand-label corrections for Qwen at eval time.

## Expected comparison outcomes

### KVRM may win on
- structural validity
- unsupported-case rejection
- deterministic execution boundary
- registry evolution handling
- fail-closed behavior
- auditability

### Qwen may win on
- direct semantic flexibility on some supported OOD cases
- one-model simplicity
- possibly raw supported-case accuracy in some tasks

That is acceptable.
KVRM does not need to win every metric to justify itself.

## What counts as a strong KVRM result

Any one of these would matter:

1. materially lower false-accept rate on unsupported cases
2. substantially better registry-evolution robustness
3. cleaner fail-closed behavior under malformed or unknown inputs
4. comparable supported accuracy with much better open-world behavior
5. stronger auditability and deterministic control-plane separation

## Artifact outputs

The live comparison artifacts now live under:
- `baselines/qwen-baseline/outputs/ollama/live_canonical/`
- `baselines/qwen-baseline/outputs/ollama/live_canonical/KVRM_VS_QWEN_OLLAMA_COMPARISON.md`
- `baselines/qwen-baseline/outputs/ollama/live_canonical/consolidated_comparison.json`

## Output artifacts required

For each model/domain pair, write:
- eval config
- metrics.json
- per_case_results.jsonl
- summary.md
- raw-response-carrying per-case outputs for error analysis

## Bottom line

The benchmark should not be designed to make the external baselines look bad.
It should be designed to answer the real question:

When finite audited action routing matters, is KVRM a better deployment architecture than simply prompting or fine-tuning a small language model selector?
