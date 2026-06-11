# IAM Access Router

This demo routes identity and privileged-access requests into a finite audited IAM workflow registry.

Purpose:
- demonstrate KVRM on bounded identity-access operations instead of another infrastructure-only domain
- make fail-closed behavior concrete for approval, review, break-glass, denial, and manual-admin escalation paths
- show why registry-constrained routing is not the same thing as plain access-request classification

Registry actions:
- `auto_approve_standard_access`
- `require_manager_approval`
- `require_security_review`
- `grant_timeboxed_privileged_access`
- `grant_break_glass_access`
- `deny_request`
- `escalate_identity_admin`

Data files:
- `data/registry.json`
- `data/train_cases.jsonl`
- `data/cases.jsonl`

Input contract:
- the registry declares `required_features` and `context_schema`
- unsupported, malformed, or semantically inconsistent requests fail closed to `escalate_identity_admin`
- critical emergency access is only supportable under the explicit break-glass envelope; it is not inferred from generic urgency signals

Quickstart:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/iam-access-router \
python3 /Users/bobbyprice/projects/KVRM/kvrm-demos/iam-access-router/scripts/run_benchmark.py
```

Tests:
```bash
python3 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/iam -q
```

This demo is intentionally workflow-level only. It does not provision credentials or change live IAM systems.
