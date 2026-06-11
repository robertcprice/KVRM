# Medical Workflow Router

This demo routes structured triage cases into finite audited clinical workflow pathways.

Purpose:
- demonstrate KVRM in a medical-adjacent setting without diagnosis or treatment autonomy
- keep decisions bounded to workflow routing and clinician/supervisor handoff
- expand the demo portfolio into a high-value regulated domain

Registry actions:
- routine_review
- urgent_clinician_review
- sepsis_screen_pathway
- stroke_alert_pathway
- cardiac_chest_pain_pathway
- respiratory_support_pathway
- lab_panel_priority_order
- escalate_supervisor_review

Data files:
- `data/registry.json`
- `data/train_cases.jsonl`
- `data/cases.jsonl`

Input contract:
- registry-declared `required_features` and `context_schema` define the supported triage input boundary
- unsupported, malformed, or schema-invalid cases are routed to `escalate_supervisor_review` instead of being interpreted as a valid clinical workflow case

Quickstart:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/medical-workflow-router \
python3 /Users/bobbyprice/projects/KVRM/kvrm-demos/medical-workflow-router/scripts/run_benchmark.py
```

Tests:
```bash
python3 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/medical -q
```

This demo is intentionally workflow-level only. It does not diagnose, prescribe, or recommend treatment.
