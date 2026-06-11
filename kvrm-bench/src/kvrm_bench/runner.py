from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from kvrm_core.artifacts import write_run_artifacts
from kvrm_core.logging import decision_result_to_case_result
from kvrm_core.registry import canonical_registry_payload, load_registry

from .datasets import load_cases
from .metrics import compute_metrics
from .reporting import render_summary


class BenchmarkRunner:
    def __init__(self, runtime, registry_path, cases_path, output_dir):
        self.runtime = runtime
        self.registry_path = Path(registry_path)
        self.cases_path = Path(cases_path)
        self.output_dir = Path(output_dir)

    def run(self, run_name: str = 'toy_benchmark') -> dict:
        registry = load_registry(self.registry_path)
        cases = load_cases(self.cases_path)
        per_case = []
        for case in cases:
            result = self.runtime.decide_and_execute(case)
            per_case.append(decision_result_to_case_result(result, case.expected_action_id, case.supported, case.ood))
        metrics = compute_metrics(per_case)
        config = {
            'run_name': run_name,
            'selector_name': getattr(self.runtime.selector, 'name', 'unknown'),
            'threshold': self.runtime.threshold,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        registry_payload = canonical_registry_payload(registry)
        registry_payload['digest'] = registry.digest
        summary = render_summary(config, registry_payload, metrics)
        write_run_artifacts(self.output_dir, config, registry_payload, metrics, per_case, summary)
        return {
            'config': config,
            'registry': registry_payload,
            'metrics': metrics,
            'cases': per_case,
            'summary': summary,
        }
