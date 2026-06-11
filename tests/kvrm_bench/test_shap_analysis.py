from __future__ import annotations

from pathlib import Path

from kvrm_bench.shap_analysis import analyze_shap_importances, run_shap_analysis
from kvrm_bench.demo import clear_demo_caches

ROOT = Path(__file__).resolve().parents[2]


def test_analyze_shap_single_domain() -> None:
    clear_demo_caches()

    model_path = ROOT / "kvrm-models" / "finance_compact_selector_v1.joblib"
    if not model_path.exists():
        return

    result = analyze_shap_importances(
        repo_root=ROOT,
        domain="finance",
        model_path=model_path,
    )

    assert result["feature_count"] > 0
    assert result["action_count"] > 0
    assert len(result["global_shap_importances"]) == result["feature_count"]
    importances = [f["shap_importance"] for f in result["global_shap_importances"]]
    assert abs(sum(importances) - 1.0) < 0.01
    assert result["per_action_directions"]
    for action, feats in result["per_action_directions"].items():
        assert len(feats) > 0
        assert all("direction" in f for f in feats)


def test_run_shap_analysis_writes_reports(tmp_path: Path) -> None:
    clear_demo_caches()

    result = run_shap_analysis(
        repo_root=ROOT,
        model_dir="kvrm-models",
        output_dir=tmp_path,
    )

    if result["summary"]["analyzed_domain_count"] == 0:
        return

    assert result["summary"]["analyzed_domain_count"] > 0
    assert (tmp_path / "shap_analysis_report.json").exists()
    assert (tmp_path / "shap_analysis_report.md").exists()
