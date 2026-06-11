from __future__ import annotations

from pathlib import Path

from kvrm_bench.adversarial_stress import (
    generate_adversarial_near_boundary_cases,
    run_adversarial_stress_benchmark,
)
from kvrm_bench.demo import clear_demo_caches

ROOT = Path(__file__).resolve().parents[2]


def test_generate_adversarial_cases_produces_near_boundary_mutations(monkeypatch) -> None:
    clear_demo_caches()

    payload = generate_adversarial_near_boundary_cases(
        repo_root=ROOT,
        domain="finance",
    )

    assert payload["adversarial_case_count"] > 0
    assert payload["single_condition_miss_count"] > 0
    assert payload["boundary_step_count"] > 0
    assert all("mutation_type" in case for case in payload["cases"])
    assert all(case["ood"] is True for case in payload["cases"])


def test_adversarial_stress_benchmark_hybrid_dominates(
    monkeypatch,
    tmp_path: Path,
) -> None:
    clear_demo_caches()

    payload = run_adversarial_stress_benchmark(
        repo_root=ROOT,
        domains=["grid"],
        output_dir=tmp_path,
    )

    grid_payload = payload["domains"]["grid"]
    hybrid_metrics = grid_payload["strategies"]["hybrid"]["metrics"]

    assert hybrid_metrics["false_accept_rate"] == 0.0
    assert hybrid_metrics["unsupported_case_rejection_rate"] >= 0.9
    assert (tmp_path / "adversarial_stress_report.json").exists()
    assert (tmp_path / "adversarial_stress_report.md").exists()
