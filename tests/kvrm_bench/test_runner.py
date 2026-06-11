from __future__ import annotations

from pathlib import Path

from kvrm_core.context import feature_key
from kvrm_core.execution import DictionaryExecutor
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.selectors import RuleSelector
from kvrm_core.validation import DeterministicValidator
from kvrm_bench.datasets import load_cases
from kvrm_bench.runner import BenchmarkRunner

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / 'kvrm-core' / 'examples' / 'toy_registry.json'
CASES_PATH = ROOT / 'kvrm-core' / 'examples' / 'toy_cases.jsonl'


def build_runtime():
    registry = load_registry(REGISTRY_PATH)
    rules = {
        feature_key({'risk': 'low', 'anomaly': 0.1}): ('allow_low_risk', 0.95),
        feature_key({'risk': 'medium', 'anomaly': 0.4}): ('collect_more_context', 0.80),
        feature_key({'risk': 'high', 'anomaly': 0.9}): ('block_request', 0.97),
        feature_key({'risk': 'unknown', 'anomaly': 0.8}): ('request_human_review', 0.45),
    }
    return KVRMRuntime(
        registry,
        RuleSelector(rules=rules),
        DeterministicValidator(registry),
        DictionaryExecutor(handlers={
            'allow_low_risk': lambda params: {'decision': 'allowed'},
            'collect_more_context': lambda params: {'decision': 'collect_context'},
            'block_request': lambda params: {'decision': 'blocked'},
            'request_human_review': lambda params: {'decision': 'handoff', 'reason': params.get('reason')},
        }),
        threshold=0.5,
    )


def test_dataset_loader_reads_cases():
    cases = load_cases(CASES_PATH)
    assert len(cases) == 4
    assert cases[0].case_id == 'c1'


def test_benchmark_runner_processes_all_cases(tmp_path):
    runner = BenchmarkRunner(build_runtime(), REGISTRY_PATH, CASES_PATH, tmp_path)
    result = runner.run(run_name='test_run')
    assert len(result['cases']) == 4
    assert (tmp_path / 'metrics.json').exists()
