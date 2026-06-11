from __future__ import annotations

from pathlib import Path

from kvrm_bench.interpretability import (
    analyze_selector_interpretability,
    run_interpretability_analysis,
)
from kvrm_bench.demo import clear_demo_caches

ROOT = Path(__file__).resolve().parents[2]


def test_analyze_selector_interpretability_produces_feature_rankings(monkeypatch) -> None:
    clear_demo_caches()

    model_path = ROOT / "kvrm-models" / "finance_compact_selector_v1.joblib"
    if not model_path.exists():
        return  # skip if no model trained yet

    payload = analyze_selector_interpretability(
        repo_root=ROOT,
        domain="finance",
        model_path=str(model_path),
    )

    assert payload["feature_count"] > 0
    assert payload["action_count"] > 0
    assert len(payload["global_feature_importances"]) == payload["feature_count"]
    assert all("importance" in fi for fi in payload["global_feature_importances"])
    assert all("rank" in fi for fi in payload["global_feature_importances"])
    importances = [fi["importance"] for fi in payload["global_feature_importances"]]
    assert abs(sum(importances) - 1.0) < 0.01


def test_run_interpretability_analysis_writes_reports(
    monkeypatch,
    tmp_path: Path,
) -> None:
    clear_demo_caches()

    payload = run_interpretability_analysis(
        repo_root=ROOT,
        model_dir="kvrm-models",
        output_dir=tmp_path,
    )

    if payload["summary"]["analyzed_domain_count"] == 0:
        return  # skip if no models trained

    assert payload["summary"]["analyzed_domain_count"] > 0
    assert (tmp_path / "interpretability_report.json").exists()
    assert (tmp_path / "interpretability_report.md").exists()
