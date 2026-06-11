# SRE Policy Router Verification

Verification date: 2026-04-09

## Test command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/sre-policy-router \
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/sre -q
```

Observed result:
- `13 passed`

## Benchmark command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/sre-policy-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/sre-policy-router/scripts/run_benchmark.py
```

## Canonical benchmark interpretation

Registry:
- `sre-policy-router@1.2.0`

Evaluation set:
- total cases: `126`
- supported cases: `88`
- unsupported cases: `38`
- registry-declared input contract: `required_features` + `context_schema`

### Retrieval baseline
- semantic_correctness_rate: `0.3068181818181818`
- abstention_rate: `0.8412698412698413`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.16944444444444443`

### Rule baseline
- semantic_correctness_rate: `0.10227272727272728`
- abstention_rate: `1.0`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.21944444444444444`

### Hybrid selector
- semantic_correctness_rate: `1.0`
- false_accept_rate: `0.0`
- abstention_rate: `0.30158730158730157`
- fallback_rate: `0.373015873015873`
- unsupported_case_rejection_rate: `1.0`
- OOD supported accuracy: `1.0`
- mean_decision_cost: `0.0`

## Honest reading

The SRE router now has the cleanest technical story in the repo: explicit registry schema, explicit support predicates per action, and a larger pack that includes missing-field, out-of-range, and unknown-feature violations. The hybrid still holds perfect supported accuracy and zero false accepts on that stricter benchmark.
