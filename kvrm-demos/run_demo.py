from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PYTHON = '/opt/homebrew/bin/python3.14'
COMMON_PATH = f"{PROJECT_ROOT}/kvrm-core/src:{PROJECT_ROOT}/kvrm-bench/src"
DEMO_PATHS = {
    'soc': f"{COMMON_PATH}:{ROOT}/soc-playbook-router/src",
    'sre': f"{COMMON_PATH}:{ROOT}/sre-policy-router/src",
    'drone': f"{COMMON_PATH}:{ROOT}/drone-mission-router/src",
    'grid': f"{COMMON_PATH}:{ROOT}/grid-ops-router/src",
    'finance': f"{COMMON_PATH}:{ROOT}/finance-risk-router/src",
    'medical': f"{COMMON_PATH}:{ROOT}/medical-workflow-router/src",
    'iam': f"{COMMON_PATH}:{ROOT}/iam-access-router/src",
    'customer_support': f"{COMMON_PATH}:{ROOT}/customer-support-router/src",
    'content_moderation': f"{COMMON_PATH}:{ROOT}/content-moderation-router/src",
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
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in SCRIPTS:
        print('usage: run_demo.py [soc|sre|drone|grid|finance|medical|iam|customer_support|content_moderation]')
        raise SystemExit(1)
    key = sys.argv[1]
    cmd = f"PYTHONPATH={DEMO_PATHS[key]} {PYTHON} {SCRIPTS[key]}"
    raise SystemExit(subprocess.call(cmd, shell=True))


if __name__ == '__main__':
    main()
