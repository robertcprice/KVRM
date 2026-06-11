# SRE Policy Router

This demo routes infrastructure incidents into a finite audited remediation-policy registry.

Purpose:
- demonstrate KVRM on infrastructure and service recovery workflows
- keep actions bounded and deterministic
- provide a second strong demo adjacent to critical infrastructure operations

Registry actions:
- restart_service
- failover_region
- scale_out
- drain_node
- rollback_deploy
- enable_readonly_mode
- gather_more_telemetry
- page_human_operator

Data files:
- `data/registry.json`
- `data/train_cases.jsonl`
- `data/cases.jsonl`

Current benchmark setup:
- retrieval baseline
- rule baseline
- hybrid selector: retrieval -> high-confidence rule -> compact prototype selector -> abstain/fallback

Current benchmark outcome:
- retrieval and rule each reach `0.75` semantic correctness
- hybrid reaches `1.0` semantic correctness on this scenario pack
- all three preserve structural validity
- hybrid keeps unsupported-case rejection at `1.0`
- hybrid reduces abstention/fallback from `0.4` to `0.2`

Quickstart:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/sre-policy-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/sre-policy-router/scripts/run_benchmark.py
```

Tests:
```bash
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/sre -q
```

Outputs:
- `outputs/sre_policy_router_retrieval/`
- `outputs/sre_policy_router_rule/`
- `outputs/sre_policy_router_hybrid/`

This demo is intentionally policy-level only. It does not execute real infrastructure changes.
