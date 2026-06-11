from __future__ import annotations

import json
from pathlib import Path


def write_run_artifacts(output_dir, config, registry, metrics, cases, summary_markdown):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'config.json').write_text(json.dumps(config, indent=2, sort_keys=True))
    (output_dir / 'registry.json').write_text(json.dumps(registry, indent=2, sort_keys=True))
    (output_dir / 'metrics.json').write_text(json.dumps(metrics, indent=2, sort_keys=True))
    with (output_dir / 'per_case_results.jsonl').open('w', encoding='utf-8') as handle:
        for row in cases:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (output_dir / 'summary.md').write_text(summary_markdown)
