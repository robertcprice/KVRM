from __future__ import annotations

from pathlib import Path

from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.validation import DeterministicValidator
from kvrm_bench.runner import BenchmarkRunner
from sre_policy_router import build_executor
from sre_policy_router import build_retrieval_selector, build_rule_selector, build_hybrid_selector

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / 'data' / 'registry.json'
TRAIN_CASES_PATH = ROOT / 'data' / 'train_cases.jsonl'
CASES_PATH = ROOT / 'data' / 'cases.jsonl'
OUTPUT_DIR = ROOT / 'outputs'


def _run(name: str, selector, threshold: float) -> dict:
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(registry, selector, DeterministicValidator(registry), build_executor(), threshold=threshold, fallback_action_id='page_human_operator')
    return BenchmarkRunner(runtime, REGISTRY_PATH, CASES_PATH, OUTPUT_DIR / name).run(run_name=name)


def main() -> None:
    retrieval_result = _run('sre_policy_router_retrieval', build_retrieval_selector(TRAIN_CASES_PATH), 0.60)
    rule_result = _run('sre_policy_router_rule', build_rule_selector(), 0.60)
    hybrid_result = _run('sre_policy_router_hybrid', build_hybrid_selector(TRAIN_CASES_PATH), 0.60)
    print('=== Retrieval baseline ===')
    print(retrieval_result['summary'])
    print('=== Rule baseline ===')
    print(rule_result['summary'])
    print('=== Hybrid selector ===')
    print(hybrid_result['summary'])


if __name__ == '__main__':
    main()
