from __future__ import annotations


def render_summary(config: dict, registry: dict, metrics: dict) -> str:
    lines = [
        '# KVRM Benchmark Summary',
        '',
        f"- Run name: {config.get('run_name', 'unknown')}",
        f"- Selector: {config.get('selector_name', 'unknown')}",
        f"- Threshold: {config.get('threshold', 'unknown')}",
        f"- Registry: {registry.get('registry_name', 'unknown')}@{registry.get('version', 'unknown')}",
        '',
        '## Metrics',
        '',
    ]
    for key, value in metrics.items():
        lines.append(f'- {key}: {value}')
    return "\n".join(lines) + "\n"
