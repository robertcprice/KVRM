from __future__ import annotations

from pathlib import Path

from kvrm_bench.coordination import (
    generate_coordination_chain_sequences,
    run_coordination_chain_benchmark,
)
from kvrm_bench.demo import clear_demo_caches

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


def test_generate_finance_coordination_chains_include_all_chain_types(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = generate_coordination_chain_sequences(
        repo_root=ROOT,
        domain="finance",
    )

    assert payload["chain_count"] > 0
    assert payload["chain_type_counts"]["supported_fail_closed_recovery"] > 0
    assert payload["chain_type_counts"]["supported_switch_fail_closed"] > 0
    assert payload["chain_type_counts"]["fail_closed_recovery_switch"] > 0
    assert payload["counterfactual_case_pack_signature"]


def test_coordination_chain_benchmark_finance_report_shows_hybrid_matching_best(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = run_coordination_chain_benchmark(
        repo_root=ROOT,
        domains=["finance"],
        output_dir=tmp_path,
    )

    finance_payload = payload["domains"]["finance"]
    comparison = finance_payload["comparison"]
    strategies = finance_payload["strategies"]
    best_non_hybrid = comparison["best_non_hybrid_strategy"]

    assert finance_payload["chain_count"] > 0
    assert finance_payload["chain_type_counts"]["supported_fail_closed_recovery"] > 0
    assert finance_payload["chain_type_counts"]["supported_switch_fail_closed"] > 0
    assert strategies["hybrid"]["chain_metrics"]["mean_chain_regret"] <= strategies[best_non_hybrid]["chain_metrics"]["mean_chain_regret"]
    assert comparison["hybrid_chain_regret_gain"] >= 0.0
    assert (tmp_path / "coordination_chain_report.json").exists()
    assert (tmp_path / "coordination_chain_report.md").exists()
    assert (tmp_path / "coordination_chain_sequences.json").exists()
