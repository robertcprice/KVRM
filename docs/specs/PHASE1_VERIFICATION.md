# Phase 1 Verification

Verification date: 2026-04-03

## Completed outputs
- KVRM core spec documents created under `docs/specs/`
- `kvrm-core` package scaffolded and implemented
- `kvrm-bench` package scaffolded and implemented
- top-level tests added under `tests/kvrm_core/` and `tests/kvrm_bench/`
- toy benchmark run completed successfully

## Test command
```bash
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/tests/kvrm_core /Users/bobbyprice/projects/KVRM/tests/kvrm_bench -q
```

Observed result:
- `23 passed`

## Toy benchmark command
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/examples/toy_benchmark.py
```

Observed highlights:
- structural validity rate: `1.0`
- semantic correctness rate: `1.0` on supported toy cases
- abstention rate: `0.25`
- fallback rate: `0.25`
- unsupported case rejection rate: `1.0`

## Artifact directory
- `kvrm-bench/outputs/toy_run/`

Files present:
- `config.json`
- `registry.json`
- `metrics.json`
- `per_case_results.jsonl`
- `summary.md`

## Notes
This verifies the Phase 1 substrate only. It does not yet validate domain-specific claims. The next phase should build stronger fresh demos on top of this foundation.