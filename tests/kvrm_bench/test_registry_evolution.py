from __future__ import annotations

from pathlib import Path

from kvrm_bench.demo import clear_demo_caches
from kvrm_bench.registry_evolution import (
    generate_registry_evolution_cases,
    run_registry_evolution_benchmark,
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


def test_generate_finance_registry_evolution_cases_include_all_migration_families(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = generate_registry_evolution_cases(
        repo_root=ROOT,
        domain="finance",
    )

    assert payload["generated_case_count"] >= 10
    assert payload["supported_case_count"] > 0
    assert payload["unsupported_case_count"] > 0
    assert payload["case_kind_counts"]["action_id_renamed"] > 0
    assert payload["case_kind_counts"]["action_split"] > 0
    assert payload["case_kind_counts"]["tightened_support"] > 0
    stale_ids = {case["stale_selected_action_id"] for case in payload["cases"]}
    assert "legacy_lower_limit_temporarily" in stale_ids
    assert "legacy_document_risk_review" in stale_ids


def test_registry_evolution_benchmark_finance_shows_live_continuity_and_stale_risk(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = run_registry_evolution_benchmark(
        repo_root=ROOT,
        domains=["finance"],
        output_dir=tmp_path,
    )

    domain_payload = payload["domains"]["finance"]
    live_metrics = domain_payload["variants"]["live_hybrid"]["evolution_metrics"]
    stale_validated_metrics = domain_payload["variants"]["stale_validated"]["evolution_metrics"]
    stale_unvalidated_metrics = domain_payload["variants"]["stale_unvalidated"]["evolution_metrics"]
    comparison = domain_payload["comparison"]

    assert live_metrics["supported_migration_success_rate"] == 1.0
    assert live_metrics["tightened_support_safe_rejection_rate"] == 1.0
    assert live_metrics["obsolete_action_execution_rate"] == 0.0
    assert stale_validated_metrics["supported_migration_success_rate"] < live_metrics["supported_migration_success_rate"]
    assert stale_validated_metrics["tightened_support_false_accept_rate"] == 0.0
    assert stale_unvalidated_metrics["obsolete_action_execution_rate"] > 0.5
    assert stale_unvalidated_metrics["tightened_support_false_accept_rate"] > 0.5
    assert comparison["supported_continuity_gain_over_stale_validated"] > 0.5
    assert comparison["obsolete_execution_reduction_vs_unvalidated"] > 0.5
    assert comparison["tightened_support_false_accept_reduction_vs_unvalidated"] > 0.5
    assert (tmp_path / "registry_evolution_report.json").exists()
    assert (tmp_path / "registry_evolution_report.md").exists()
    assert (tmp_path / "registry_evolution_cases.json").exists()
