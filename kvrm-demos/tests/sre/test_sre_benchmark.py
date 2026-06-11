from __future__ import annotations

from pathlib import Path

from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.validation import DeterministicValidator
from kvrm_bench.runner import BenchmarkRunner
from sre_policy_router import build_executor
from sre_policy_router import build_retrieval_selector, build_hybrid_selector

ROOT = Path(__file__).resolve().parents[2] / 'sre-policy-router'
REGISTRY_PATH = ROOT / 'data' / 'registry.json'
TRAIN_CASES_PATH = ROOT / 'data' / 'train_cases.jsonl'
CASES_PATH = ROOT / 'data' / 'cases.jsonl'


def test_sre_benchmark_runs_and_writes_artifacts(tmp_path):
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(registry, build_retrieval_selector(TRAIN_CASES_PATH), DeterministicValidator(registry), build_executor(), threshold=0.60, fallback_action_id='page_human_operator')
    result = BenchmarkRunner(runtime, REGISTRY_PATH, CASES_PATH, tmp_path).run(run_name='sre_test')
    assert result['metrics']['structural_validity_rate'] == 1.0
    assert result['metrics']['unsupported_case_rejection_rate'] >= 1.0


def test_hybrid_beats_retrieval_on_supported_accuracy(tmp_path):
    registry = load_registry(REGISTRY_PATH)
    retrieval_runtime = KVRMRuntime(registry, build_retrieval_selector(TRAIN_CASES_PATH), DeterministicValidator(registry), build_executor(), threshold=0.60, fallback_action_id='page_human_operator')
    hybrid_runtime = KVRMRuntime(registry, build_hybrid_selector(TRAIN_CASES_PATH), DeterministicValidator(registry), build_executor(), threshold=0.60, fallback_action_id='page_human_operator')
    retrieval_result = BenchmarkRunner(retrieval_runtime, REGISTRY_PATH, CASES_PATH, tmp_path / 'retrieval').run(run_name='retrieval')
    hybrid_result = BenchmarkRunner(hybrid_runtime, REGISTRY_PATH, CASES_PATH, tmp_path / 'hybrid').run(run_name='hybrid')
    assert hybrid_result['metrics']['semantic_correctness_rate'] >= retrieval_result['metrics']['semantic_correctness_rate']
    assert hybrid_result['metrics']['unsupported_case_rejection_rate'] >= 1.0
