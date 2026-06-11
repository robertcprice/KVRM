from __future__ import annotations

import json
from pathlib import Path

from kvrm_bench.dashboard import load_dashboard_snapshot


def test_dashboard_snapshot_loads_canonical_demo_and_training_artifacts(tmp_path: Path):
    results_dir = tmp_path / "kvrm-bench" / "results"
    results_dir.mkdir(parents=True)
    (results_dir / "legacy").mkdir()

    demo_comparison_payload = {
        "demos": {
            "soc_hybrid": {
                "semantic_correctness_rate": 1.0,
                "false_accept_rate": 0.0,
                "unsupported_case_rejection_rate": 1.0,
                "abstention_rate": 0.29,
                "mean_decision_cost": 0.0,
            },
            "finance_hybrid": {
                "semantic_correctness_rate": 0.94,
                "false_accept_rate": 0.0,
                "unsupported_case_rejection_rate": 1.0,
                "abstention_rate": 0.25,
                "mean_decision_cost": 0.06,
            },
            "grid_hybrid": {
                "semantic_correctness_rate": 1.0,
                "false_accept_rate": 0.0,
                "unsupported_case_rejection_rate": 1.0,
                "abstention_rate": 0.25,
                "mean_decision_cost": 0.0,
            },
        }
    }
    sre_training_payload = {
        "domain": "sre",
        "selector_only": {
            "semantic_correctness_rate": 0.88,
            "false_accept_rate": 0.0,
            "mean_decision_cost": 0.08,
        },
        "hybrid_augmented": {
            "semantic_correctness_rate": 1.0,
            "false_accept_rate": 0.0,
            "mean_decision_cost": 0.0,
        },
    }
    finance_training_payload = {
        "domain": "finance",
        "selector_only": {
            "semantic_correctness_rate": 0.72,
            "false_accept_rate": 0.0,
            "mean_decision_cost": 0.18,
        },
        "hybrid_augmented": {
            "semantic_correctness_rate": 0.94,
            "false_accept_rate": 0.0,
            "mean_decision_cost": 0.06,
        },
    }
    grid_training_payload = {
        "domain": "grid",
        "selector_only": {
            "semantic_correctness_rate": 0.28,
            "false_accept_rate": 0.0,
            "mean_decision_cost": 0.16,
        },
        "hybrid_augmented": {
            "semantic_correctness_rate": 1.0,
            "false_accept_rate": 0.0,
            "mean_decision_cost": 0.0,
        },
    }

    (results_dir / "sre_compact_training_report_v1.json").write_text(json.dumps(sre_training_payload), encoding="utf-8")
    (results_dir / "finance_compact_training_report_v1.json").write_text(json.dumps(finance_training_payload), encoding="utf-8")
    (results_dir / "grid_compact_training_report_v1.json").write_text(json.dumps(grid_training_payload), encoding="utf-8")
    reports_dir = tmp_path / "kvrm-demos" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "demo_comparison.json").write_text(json.dumps(demo_comparison_payload), encoding="utf-8")

    snapshot = load_dashboard_snapshot(tmp_path)

    assert snapshot.available_files["demo_comparison"] is not None
    assert snapshot.available_files["legacy_results"] is not None
    soc = next(domain for domain in snapshot.domains if domain.domain == "soc")
    assert soc.demo_hybrid.semantic_correctness_rate == 1.0
    sre = next(domain for domain in snapshot.domains if domain.domain == "sre")
    assert sre.training.hybrid_augmented_accuracy == 1.0
    finance = next(domain for domain in snapshot.domains if domain.domain == "finance")
    assert finance.demo_hybrid.mean_decision_cost == 0.06
    assert finance.training.hybrid_augmented_accuracy == 0.94
    grid = next(domain for domain in snapshot.domains if domain.domain == "grid")
    assert grid.demo_hybrid.semantic_correctness_rate == 1.0
    assert grid.training.hybrid_augmented_accuracy == 1.0
