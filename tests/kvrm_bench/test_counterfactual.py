from __future__ import annotations

from pathlib import Path

from kvrm_bench.counterfactual import (
    generate_boundary_counterfactual_cases,
    load_or_generate_boundary_counterfactual_cases,
    run_counterfactual_boundary_benchmark,
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


def test_generate_finance_counterfactual_cases_include_velocity_spike_boundary(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = generate_boundary_counterfactual_cases(
        repo_root=ROOT,
        domain="finance",
    )

    case = next(
        row
        for row in payload["cases"]
        if row["case_id"] == "finance_case_017:velocity_indicator:high"
    )
    assert payload["generated_case_count"] > 20
    assert payload["supported_case_count"] > 0
    assert payload["unsupported_case_count"] > 0
    assert case["expected_action_id"] == "lower_limit_temporarily"
    assert case["supported"] is True


def test_counterfactual_boundary_benchmark_finance_report_shows_hybrid_matching_best(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = run_counterfactual_boundary_benchmark(
        repo_root=ROOT,
        domains=["finance"],
        output_dir=tmp_path,
    )

    finance_payload = payload["domains"]["finance"]
    comparison = finance_payload["comparison"]
    strategies = finance_payload["strategies"]
    best_non_hybrid = comparison["best_non_hybrid_strategy"]

    assert finance_payload["generated_case_count"] > 20
    assert finance_payload["supported_case_count"] > 0
    assert finance_payload["unsupported_case_count"] > 0
    assert strategies["hybrid"]["metrics"]["semantic_correctness_rate"] == 1.0
    assert strategies["hybrid"]["metrics"]["false_accept_rate"] == 0.0
    assert strategies["hybrid"]["metrics"]["unsupported_case_rejection_rate"] == 1.0
    assert strategies["hybrid"]["regret"]["mean_decision_regret"] <= strategies[best_non_hybrid]["regret"]["mean_decision_regret"]
    assert comparison["hybrid_regret_gain"] >= 0.0
    assert (tmp_path / "counterfactual_boundary_report.json").exists()
    assert (tmp_path / "counterfactual_boundary_report.md").exists()
    assert (tmp_path / "counterfactual_boundary_cases.json").exists()


def test_counterfactual_case_pack_cache_reuses_matching_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    case_pack_dir = tmp_path / "counterfactual_boundary_case_cache"

    first_payload = load_or_generate_boundary_counterfactual_cases(
        repo_root=ROOT,
        domain="finance",
        artifact_dir=case_pack_dir,
    )
    second_payload = load_or_generate_boundary_counterfactual_cases(
        repo_root=ROOT,
        domain="finance",
        artifact_dir=case_pack_dir,
    )

    assert first_payload["case_pack_source"] == "generated"
    assert second_payload["case_pack_source"] == "cache"
    assert first_payload["case_pack_signature"] == second_payload["case_pack_signature"]
    assert first_payload["generated_case_count"] == second_payload["generated_case_count"]
    assert first_payload["cases"] == second_payload["cases"]
    assert (case_pack_dir / "finance.json").exists()
