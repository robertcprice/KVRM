# Grid Ops Router

This demo routes structured electric-grid operating states into a finite audited workflow registry.

Goals:
- demonstrate KVRM on another critical-infrastructure-adjacent domain
- keep the action set bounded, reviewable, and deterministic
- show that schema-tight support gating generalizes beyond SOC, SRE, and drone policy routing

Finite action set:
- `continue_monitoring`
- `isolate_faulted_feeder`
- `transfer_load`
- `dispatch_field_crew`
- `shed_noncritical_load`
- `prepare_blackstart`
- `defer_switching_due_weather`
- `escalate_grid_supervisor`

Run benchmark:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/grid-ops-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/grid-ops-router/scripts/run_benchmark.py
```

Run tests:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/grid-ops-router \
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/grid -q
```

This demo is intentionally workflow-level only. It does not issue real switching commands or operate grid equipment.
