from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PYTHON = sys.executable
COMMON_PATH = f"{PROJECT_ROOT}/kvrm-core:{PROJECT_ROOT}/kvrm-bench"
DEMO_PATHS = {
    'soc': f"{COMMON_PATH}:{ROOT}/soc-playbook-router",
    'sre': f"{COMMON_PATH}:{ROOT}/sre-policy-router",
    'drone': f"{COMMON_PATH}:{ROOT}/drone-mission-router",
    'grid': f"{COMMON_PATH}:{ROOT}/grid-ops-router",
    'finance': f"{COMMON_PATH}:{ROOT}/finance-risk-router",
    'medical': f"{COMMON_PATH}:{ROOT}/medical-workflow-router",
    'iam': f"{COMMON_PATH}:{ROOT}/iam-access-router",
    'customer_support': f"{COMMON_PATH}:{ROOT}/customer-support-router",
    'content_moderation': f"{COMMON_PATH}:{ROOT}/content-moderation-router",
    'legal': f"{COMMON_PATH}:{ROOT}/legal-compliance-router",
    'cicd': f"{COMMON_PATH}:{ROOT}/cicd-pipeline-router",
    'insurance': f"{COMMON_PATH}:{ROOT}/insurance-claims-router",
}
SCRIPTS = {
    'soc': ROOT / 'soc-playbook-router' / 'scripts' / 'run_benchmark.py',
    'sre': ROOT / 'sre-policy-router' / 'scripts' / 'run_benchmark.py',
    'drone': ROOT / 'drone-mission-router' / 'scripts' / 'run_benchmark.py',
    'grid': ROOT / 'grid-ops-router' / 'scripts' / 'run_benchmark.py',
    'finance': ROOT / 'finance-risk-router' / 'scripts' / 'run_benchmark.py',
    'medical': ROOT / 'medical-workflow-router' / 'scripts' / 'run_benchmark.py',
    'iam': ROOT / 'iam-access-router' / 'scripts' / 'run_benchmark.py',
    'customer_support': ROOT / 'customer-support-router' / 'scripts' / 'run_benchmark.py',
    'content_moderation': ROOT / 'content-moderation-router' / 'scripts' / 'run_benchmark.py',
    'legal': ROOT / 'legal-compliance-router' / 'scripts' / 'run_benchmark.py',
    'cicd': ROOT / 'cicd-pipeline-router' / 'scripts' / 'run_benchmark.py',
    'insurance': ROOT / 'insurance-claims-router' / 'scripts' / 'run_benchmark.py',
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in SCRIPTS:
        print('usage: run_demo.py [soc|sre|drone|grid|finance|medical|iam|customer_support|content_moderation|legal|cicd|insurance]')
        raise SystemExit(1)
    key = sys.argv[1]
    cmd = f"PYTHONPATH={DEMO_PATHS[key]} {PYTHON} {SCRIPTS[key]}"
    raise SystemExit(subprocess.call(cmd, shell=True))


if __name__ == '__main__':
    main()
