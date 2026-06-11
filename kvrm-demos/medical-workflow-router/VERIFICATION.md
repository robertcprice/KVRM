# Medical Workflow Router Verification

Verification date: 2026-04-09

## Test command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/medical-workflow-router \
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/medical -q
```

Observed result:
- `14 passed`

## Benchmark command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/medical-workflow-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/medical-workflow-router/scripts/run_benchmark.py
```

## Canonical benchmark interpretation

Registry:
- `medical-workflow-router@1.1.0`

Evaluation set:
- total cases: `24`
- supported cases: `18`
- unsupported cases: `6`
- registry-declared input contract: `required_features` + `context_schema`

### Retrieval baseline
- semantic_correctness_rate: `0.6666666666666666`
- abstention_rate: `0.5`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.08749999999999998`

### Rule baseline
- semantic_correctness_rate: `0.4444444444444444`
- abstention_rate: `0.7083333333333334`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.14583333333333334`

### Hybrid selector
- semantic_correctness_rate: `1.0`
- false_accept_rate: `0.0`
- abstention_rate: `0.25`
- fallback_rate: `0.25`
- unsupported_case_rejection_rate: `1.0`
- OOD supported accuracy: `1.0`
- mean_decision_cost: `0.0`

## Honest reading

This demo stays publication-defensible because it is workflow routing, not diagnosis. The architecture benefit is that schema-declared support checks reject malformed triage payloads cleanly while the hybrid still recovers supported edge cases without opening a false-accept path.
