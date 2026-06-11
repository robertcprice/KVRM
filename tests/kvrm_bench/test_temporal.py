from __future__ import annotations

from pathlib import Path

from kvrm_bench.demo import clear_demo_caches
from kvrm_bench.temporal import (
    generate_temporal_transition_sequences,
    run_temporal_transition_benchmark,
)

ROOT = Path(__file__).resolve().parents[2]


def _prepend_demo_paths(monkeypatch) -> None:
    for rel in (
        "kvrm-core/src",
        "kvrm-bench/src",
        "kvrm-demos/soc-playbook-router",
        "kvrm-demos/sre-policy-router",
        "kvrm-demos/drone-mission-router",
        "kvrm-demos/grid-ops-router",
        "kvrm-demos/finance-risk-router",
        "kvrm-demos/medical-workflow-router",
    ):
        monkeypatch.syspath_prepend(str(ROOT / rel))


def test_generate_finance_temporal_sequences_include_recovery_and_switch(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = generate_temporal_transition_sequences(
        repo_root=ROOT,
        domain="finance",
    )

    assert payload["sequence_count"] > 0
    assert payload["transition_type_counts"]["unsupported_to_supported_recovery"] > 0
    assert payload["transition_type_counts"]["supported_to_unsupported_fail_closed"] > 0
    assert payload["transition_type_counts"]["supported_action_switch"] > 0
    assert payload["counterfactual_case_pack_signature"]


def test_temporal_transition_benchmark_finance_report_shows_hybrid_matching_best(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = run_temporal_transition_benchmark(
        repo_root=ROOT,
        domains=["finance"],
        output_dir=tmp_path,
    )

    finance_payload = payload["domains"]["finance"]
    comparison = finance_payload["comparison"]
    strategies = finance_payload["strategies"]
    best_non_hybrid = comparison["best_non_hybrid_strategy"]

    assert finance_payload["sequence_count"] > 0
    assert finance_payload["transition_type_counts"]["unsupported_to_supported_recovery"] > 0
    assert finance_payload["transition_type_counts"]["supported_to_unsupported_fail_closed"] > 0
    assert strategies["hybrid"]["sequence_metrics"]["mean_sequence_regret"] <= strategies[best_non_hybrid]["sequence_metrics"]["mean_sequence_regret"]
    assert comparison["hybrid_sequence_regret_gain"] >= 0.0
    assert (tmp_path / "temporal_transition_report.json").exists()
    assert (tmp_path / "temporal_transition_report.md").exists()
    assert (tmp_path / "temporal_transition_sequences.json").exists()
