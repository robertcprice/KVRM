from __future__ import annotations

import json
from pathlib import Path


REQUIRED_FILES = ['config.json', 'registry.json', 'metrics.json', 'per_case_results.jsonl', 'summary.md']


def load_run(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    for name in REQUIRED_FILES:
        if not (run_dir / name).exists():
            raise FileNotFoundError(name)
    cases = []
    with (run_dir / 'per_case_results.jsonl').open('r', encoding='utf-8') as handle:
        for line in handle:
            cases.append(json.loads(line))
    return {
        'config': json.loads((run_dir / 'config.json').read_text()),
        'registry': json.loads((run_dir / 'registry.json').read_text()),
        'metrics': json.loads((run_dir / 'metrics.json').read_text()),
        'cases': cases,
        'summary': (run_dir / 'summary.md').read_text(),
    }
