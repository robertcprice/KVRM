from __future__ import annotations

from pathlib import Path

from kvrm_bench.fallback_feasibility import (
    generate_fallback_feasibility_cases,
    run_fallback_feasibility_benchmark,
)

ROOT = Path(__file__).resolve().parents[2]


def test_generate_fallback_feasibility_cases_sre_includes_supported_and_generated_probes() -> None:
    payload = generate_fallback_feasibility_cases(
        repo_root=ROOT,
        domain="sre",
    )

    assert payload["fallback_action_id"] == "page_human_operator"
    assert payload["supported_case_count"] > 0
    assert payload["unsupported_case_count"] > 0
    assert payload["case_kind_counts"]["supported_handoff_control"] > 0
    assert payload["case_kind_counts"]["generated_infeasible_handoff"] > 0
    assert payload["case_kind_counts"]["generated_combined_infeasible_handoff"] > 0
    assert payload["violation_feature_counts"]["operator_response_eta"] > 0
    assert payload["violation_feature_counts"]["mitigation_window_remaining"] > 0


def test_fallback_feasibility_benchmark_shows_strict_blocking_legacy_bypass(tmp_path) -> None:
    payload = run_fallback_feasibility_benchmark(
        repo_root=ROOT,
        domains=["sre"],
        output_dir=tmp_path,
    )

    domain_payload = payload["domains"]["sre"]
    strict_metrics = domain_payload["variants"]["strict"]["feasibility_metrics"]
    legacy_metrics = domain_payload["variants"]["legacy_bypass"]["feasibility_metrics"]
    comparison = domain_payload["comparison"]

    assert strict_metrics["supported_handoff_success_rate"] == 1.0
    assert legacy_metrics["supported_handoff_success_rate"] == 1.0
    assert strict_metrics["unsupported_unsafe_execution_rate"] == 0.0
    assert legacy_metrics["unsupported_unsafe_execution_rate"] > 0.5
    assert strict_metrics["unsupported_infeasible_handoff_execution_rate"] == 0.0
    assert legacy_metrics["unsupported_infeasible_handoff_execution_rate"] > 0.5
    assert strict_metrics["unsupported_safe_rejection_rate"] == 1.0
    assert strict_metrics["mean_feasibility_cost"] < legacy_metrics["mean_feasibility_cost"]
    assert comparison["unsafe_execution_reduction"] > 0.5
    assert comparison["feasibility_cost_reduction"] > 0.5
    assert (tmp_path / "fallback_feasibility_report.json").exists()
    assert (tmp_path / "fallback_feasibility_report.md").exists()
    assert (tmp_path / "fallback_feasibility_cases.json").exists()
