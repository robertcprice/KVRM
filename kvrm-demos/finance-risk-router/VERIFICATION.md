# Finance Risk Router Verification

Verification date: 2026-04-09

## Test command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/finance-risk-router \
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/finance -q
```

Observed result:
- `9 passed`

## Benchmark command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/finance-risk-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/finance-risk-router/scripts/run_benchmark.py
```

## Canonical benchmark interpretation

Registry:
- `finance-risk-router@1.1.0`

Evaluation set:
- total cases: `24`
- supported cases: `18`
- unsupported cases: `6`
- registry-declared input contract: `required_features` + `context_schema`

### Retrieval baseline
- semantic_correctness_rate: `0.7222222222222222`
- abstention_rate: `0.5`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.07291666666666667`

### Rule baseline
- semantic_correctness_rate: `0.5555555555555556`
- abstention_rate: `0.6666666666666666`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.11666666666666665`

### Hybrid selector
- semantic_correctness_rate: `1.0`
- false_accept_rate: `0.0`
- abstention_rate: `0.25`
- fallback_rate: `0.25`
- unsupported_case_rejection_rate: `1.0`
- OOD supported accuracy: `1.0`
- mean_decision_cost: `0.0`

## Honest reading

This domain is only strong when the action boundary is explicit. The key improvement here was not a larger model but tightening a real overlap between `enhanced_due_diligence` and `manual_review` in the registry so ambiguous high-jurisdiction medium-anomaly cases resolve to the safe audited fallback path instead of a more aggressive workflow.
