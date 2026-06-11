# Drone Mission Router Verification

Verification date: 2026-04-09

## Test command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/drone-mission-router \
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/drone -q
```

Observed result:
- `11 passed`

## Benchmark command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/drone-mission-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/drone-mission-router/scripts/run_benchmark.py
```

## Canonical benchmark interpretation

Registry:
- `drone-mission-router@1.2.0`

Evaluation set:
- total cases: `135`
- supported cases: `94`
- unsupported cases: `41`
- registry-declared input contract: `required_features` + `context_schema`
- supported overlap count: `0`

### Retrieval baseline
- semantic_correctness_rate: `0.20212765957446807`
- abstention_rate: `0.9333333333333333`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.19444444444444445`

### Rule baseline
- semantic_correctness_rate: `0.18085106382978725`
- abstention_rate: `0.9481481481481482`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.19962962962962963`

### Hybrid selector
- semantic_correctness_rate: `1.0`
- false_accept_rate: `0.0`
- abstention_rate: `0.08148148148148149`
- fallback_rate: `0.37777777777777777`
- unsupported_case_rejection_rate: `1.0`
- OOD supported accuracy: `1.0`
- mean_decision_cost: `0.0`

### Compact training report
- train cases: `21`
- selector_only semantic_correctness_rate: `0.7446808510638298`
- hybrid_augmented semantic_correctness_rate: `1.0`
- false_accept_rate: `0.0`
- unsupported_case_rejection_rate: `1.0`

## Honest reading

The drone router was previously the easiest place for support drift to hide. Tightening the registry with explicit route-energy and recovery-affordance features collapses the old battery and recovery overlaps without degrading supported performance: the hybrid stays perfect on the enlarged pack, the compact selector improves materially, and malformed mission context is still rejected cleanly.
