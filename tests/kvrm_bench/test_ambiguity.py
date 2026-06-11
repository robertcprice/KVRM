from __future__ import annotations

from pathlib import Path

from kvrm_bench.ambiguity import run_ambiguity_regret_benchmark
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


def test_ambiguity_regret_report_shows_hybrid_beating_best_non_hybrid(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = run_ambiguity_regret_benchmark(
        repo_root=ROOT,
        domains=["finance"],
        output_dir=tmp_path,
    )

    finance_payload = payload["domains"]["finance"]
    comparison = finance_payload["comparison"]
    strategies = finance_payload["strategies"]
    best_non_hybrid = comparison["best_non_hybrid_strategy"]

    assert finance_payload["frontier_case_count"] > 0
    assert finance_payload["supported_frontier_case_count"] > 0
    assert finance_payload["unsupported_frontier_case_count"] > 0
    assert "hybrid" in strategies
    assert best_non_hybrid != "hybrid"
    assert strategies["hybrid"]["regret"]["mean_decision_regret"] <= strategies[best_non_hybrid]["regret"]["mean_decision_regret"]
    assert comparison["hybrid_regret_gain"] >= 0.0
    assert (tmp_path / "ambiguity_regret_report.json").exists()
    assert (tmp_path / "ambiguity_regret_report.md").exists()
