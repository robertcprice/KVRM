# Finance Risk Router

This demo routes transaction-risk cases into a finite audited workflow registry.

Purpose:
- demonstrate KVRM on audited financial-risk routing without free-form trading or underwriting
- keep actions bounded to approved review and control workflows
- provide a fourth domain showing that the architecture generalizes beyond infrastructure operations

Registry actions:
- approve_low_risk
- allow_with_monitoring
- enhanced_due_diligence
- require_additional_docs
- lower_limit_temporarily
- freeze_for_investigation
- escalate_compliance
- manual_review

Data files:
- `data/registry.json`
- `data/train_cases.jsonl`
- `data/cases.jsonl`

Input contract:
- registry-declared `required_features` and `context_schema` define the supported input boundary
- unsupported, malformed, or schema-invalid cases are routed to `manual_review` instead of being force-fit into a workflow

Quickstart:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/finance-risk-router \
python3 /Users/bobbyprice/projects/KVRM/kvrm-demos/finance-risk-router/scripts/run_benchmark.py
```

Tests:
```bash
python3 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/finance -q
```

This demo is intentionally workflow-level only. It does not execute payments, trading, or account changes.
