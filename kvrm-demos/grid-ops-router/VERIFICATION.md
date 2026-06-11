# Grid Ops Router Verification

Verification date: 2026-04-09

## Test command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/grid-ops-router \
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/grid -q
```

Observed result:
- `6 passed`

## Benchmark command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/grid-ops-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/grid-ops-router/scripts/run_benchmark.py
```

## Canonical benchmark interpretation

Registry:
- `grid-ops-router@1.0.0`

Evaluation set:
- total cases: `24`
- supported cases: `18`
- unsupported cases: `6`
- registry-declared input contract: `required_features` + `context_schema`

### Retrieval baseline
- semantic_correctness_rate: `0.1111111111111111`
- abstention_rate: `1.0`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.2333333333333333`

### Rule baseline
- semantic_correctness_rate: `0.1111111111111111`
- abstention_rate: `1.0`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.2333333333333333`

### Hybrid selector
- semantic_correctness_rate: `1.0`
- false_accept_rate: `0.0`
- abstention_rate: `0.25`
- fallback_rate: `0.3333333333333333`
- unsupported_case_rejection_rate: `1.0`
- OOD supported accuracy: `1.0`
- mean_decision_cost: `0.0`

## Honest reading

This domain extends the KVRM story into grid-operations workflow routing without pretending to automate control-room actions. The key technical point is the same as the stronger SOC and SRE demos: finite audited actions plus registry-declared support boundaries let the hybrid recover supported edge cases while rejecting malformed or inconsistent operating context cleanly.
