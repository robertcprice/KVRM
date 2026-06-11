from __future__ import annotations

from pathlib import Path

from kvrm_bench.scale_test import (
    generate_scale_test_cases,
    run_scale_benchmark,
)
from kvrm_bench.demo import clear_demo_caches

ROOT = Path(__file__).resolve().parents[2]


def test_generate_scale_cases_produces_target_count(monkeypatch) -> None:
    clear_demo_caches()

    payload = generate_scale_test_cases(
        repo_root=ROOT,
        domain="grid",
        target_count=200,
        seed=42,
    )

    assert payload["generated_case_count"] >= 100
    assert payload["supported_case_count"] > 0
    assert payload["unsupported_case_count"] > 0
    assert payload["total_feature_space_size"] > 0
    assert all("input_features" in case for case in payload["cases"])


def test_scale_benchmark_reports_latency_and_correctness(
    monkeypatch,
    tmp_path: Path,
) -> None:
    clear_demo_caches()

    payload = run_scale_benchmark(
        repo_root=ROOT,
        domains=["grid"],
        target_count=100,
        output_dir=tmp_path,
    )

    grid_payload = payload["domains"]["grid"]
    assert grid_payload["case_count"] >= 50
    assert grid_payload["latency"]["throughput_decisions_per_sec"] > 0
    assert grid_payload["latency"]["p50_ms"] >= 0
    assert grid_payload["latency"]["p99_ms"] >= grid_payload["latency"]["p50_ms"]
    assert grid_payload["correctness"]["false_accept_rate"] == 0.0
    assert (tmp_path / "scale_benchmark_report.json").exists()
    assert (tmp_path / "scale_benchmark_report.md").exists()
