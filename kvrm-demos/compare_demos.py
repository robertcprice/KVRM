from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = {
    'soc_hybrid': ROOT / 'soc-playbook-router' / 'outputs' / 'soc_playbook_router_hybrid' / 'metrics.json',
    'sre_hybrid': ROOT / 'sre-policy-router' / 'outputs' / 'sre_policy_router_hybrid' / 'metrics.json',
    'drone_hybrid': ROOT / 'drone-mission-router' / 'outputs' / 'drone_mission_router_hybrid' / 'metrics.json',
    'grid_hybrid': ROOT / 'grid-ops-router' / 'outputs' / 'grid_ops_router_hybrid' / 'metrics.json',
    'finance_hybrid': ROOT / 'finance-risk-router' / 'outputs' / 'finance_risk_router_hybrid' / 'metrics.json',
    'medical_hybrid': ROOT / 'medical-workflow-router' / 'outputs' / 'medical_workflow_router_hybrid' / 'metrics.json',
    'iam_hybrid': ROOT / 'iam-access-router' / 'outputs' / 'iam_access_router_hybrid' / 'metrics.json',
    'customer_support_hybrid': ROOT / 'customer-support-router' / 'outputs' / 'customer_support_router_hybrid' / 'metrics.json',
    'content_moderation_hybrid': ROOT / 'content-moderation-router' / 'outputs' / 'content_moderation_router_hybrid' / 'metrics.json',
    'legal_hybrid': ROOT / 'legal-compliance-router' / 'outputs' / 'legal_compliance_router_hybrid' / 'metrics.json',
    'cicd_hybrid': ROOT / 'cicd-pipeline-router' / 'outputs' / 'cicd_pipeline_router_hybrid' / 'metrics.json',
    'insurance_hybrid': ROOT / 'insurance-claims-router' / 'outputs' / 'insurance_claims_router_hybrid' / 'metrics.json',
}
REPORT_DIR = ROOT / 'reports'
REPORT_JSON = REPORT_DIR / 'demo_comparison.json'
REPORT_MD = REPORT_DIR / 'demo_comparison.md'


def collect() -> dict:
    payload = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'demos': {},
    }
    for name, path in RUNS.items():
        if path.exists():
            payload['demos'][name] = json.loads(path.read_text())
        else:
            payload['demos'][name] = {'missing': True, 'path': str(path)}
    return payload


def write_reports(payload: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = ['# KVRM Demo Comparison', '']
    for name, metrics in payload['demos'].items():
        if metrics.get('missing'):
            lines.append(f'- {name}: missing ({metrics["path"]})')
            continue
        lines.append(
            f'- {name}: semantic={metrics["semantic_correctness_rate"]}, unsupported_rejection={metrics["unsupported_case_rejection_rate"]}, '
            f'abstention={metrics["abstention_rate"]}, fallback={metrics["fallback_rate"]}, '
            f'ood_supported={metrics.get("ood_accuracy_supported_only", 0.0)}, '
            f'support_gate_trigger={metrics.get("support_gate_trigger_rate", 0.0)}, '
            f'support_gate_rescue={metrics.get("supported_support_gate_rescue_rate", 0.0)}, '
            f'cost={metrics.get("mean_decision_cost", "n/a")}'
        )
    REPORT_MD.write_text('\n'.join(lines) + '\n')


def main() -> None:
    payload = collect()
    write_reports(payload)
    print(REPORT_MD.read_text(), end='')


if __name__ == '__main__':
    main()
