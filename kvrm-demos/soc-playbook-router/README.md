# SOC Playbook Router

This is the first real KVRM demo built on Phase 1.

Purpose:
- route security incidents into a finite audited response-playbook registry
- demonstrate abstention, fallback, and deterministic execution
- provide a clearer KVRM use case than legacy inherited projects

Registry actions:
- isolate_host
- rotate_credentials
- collect_forensics
- escalate_p1
- block_ip_temporarily
- monitor_only
- request_human_triage
- do_nothing_validated

Data files:
- `data/registry.json` - audited action registry
- `data/train_cases.jsonl` - support-bank training examples
- `data/cases.jsonl` - evaluation cases including supported OOD and unsupported cases

Current benchmark setup:
- retrieval baseline
- rule baseline
- hybrid selector: retrieval -> high-confidence rule -> compact prototype selector -> abstain/fallback

Current benchmark outcome:
- retrieval and rule each reach `0.625` semantic correctness
- hybrid reaches `1.0` semantic correctness on this scenario pack
- all three preserve structural validity
- hybrid keeps unsupported-case rejection at `1.0`
- hybrid reduces abstention/fallback from `0.5` to `0.2`

Quickstart:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/soc-playbook-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/soc-playbook-router/scripts/run_benchmark.py
```

Tests:
```bash
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/soc -q
```

Outputs:
- `outputs/soc_playbook_router_retrieval/`
- `outputs/soc_playbook_router_rule/`
- `outputs/soc_playbook_router_hybrid/`

This demo is intentionally policy-level only. It does not execute real destructive security actions.
