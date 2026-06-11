# SOC Playbook Router Verification

Verification date: 2026-04-09

## Test command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/soc-playbook-router \
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/soc -q
```

Observed result:
- `10 passed`

## Benchmark command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/soc-playbook-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/soc-playbook-router/scripts/run_benchmark.py
```

## Canonical benchmark interpretation

Registry:
- `soc-playbook-router@1.1.0`

Evaluation set:
- total cases: `126`
- supported cases: `88`
- unsupported cases: `38`
- registry-declared input contract: `required_features` + `context_schema`

### Retrieval baseline
- semantic_correctness_rate: `0.2159090909090909`
- abstention_rate: `0.9285714285714286`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.19166666666666665`

### Rule baseline
- semantic_correctness_rate: `0.18181818181818182`
- abstention_rate: `0.9523809523809523`
- unsupported_case_rejection_rate: `1.0`
- mean_decision_cost: `0.19999999999999998`

### Hybrid selector
- semantic_correctness_rate: `1.0`
- false_accept_rate: `0.0`
- abstention_rate: `0.30158730158730157`
- fallback_rate: `0.38095238095238093`
- unsupported_case_rejection_rate: `1.0`
- OOD supported accuracy: `1.0`
- mean_decision_cost: `0.0`

## Honest reading

The active SOC pack is no longer just harder semantically; it is tighter structurally. The new schema-invalid cases prove that malformed or out-of-contract context is rejected by the registry boundary itself, while the hybrid still recovers every supported case in the enlarged canonical pack.
