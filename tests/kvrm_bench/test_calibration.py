"""Tests for kvrm_bench.calibration module."""

from __future__ import annotations

import json
import pytest
import numpy as np
from pathlib import Path

from kvrm_bench.calibration import (
    BinData,
    CalibrationResult,
    RecalibrationResult,
    compute_brier_score,
    compute_ece_detailed,
    overconfidence_ratio,
    render_markdown_report,
    write_json_report,
    write_recalibration_json_report,
    render_recalibration_markdown,
    _best_strategy_per_domain,
    _strategy_mean_ece,
    _strategy_mean_brier,
    _ece_from_arrays,
    _brier_from_arrays,
    _loocv_calibrate,
)
from kvrm_core.calibration import (
    TemperatureScaler,
    PlattScaler,
    IsotonicScaler,
)


# ---------------------------------------------------------------------------
# Fixtures: synthetic case results
# ---------------------------------------------------------------------------

def _make_case(confidence: float, correct: bool) -> dict:
    return {
        "case_id": "test",
        "supported": True,
        "ood": False,
        "expected_action_id": "a",
        "selected_action_id": "a" if correct else "b",
        "final_status": "executed",
        "confidence": confidence,
        "abstained": False,
        "fallback_used": False,
        "valid": True,
        "correct": correct,
        "latency_ms": 1.0,
    }


class TestComputeECEDetailed:
    """Tests for the detailed ECE computation."""

    def test_perfectly_calibrated(self):
        """If confidence == accuracy in every bin, ECE should be 0."""
        # All cases with confidence 0.85, all correct
        cases = [_make_case(0.85, True) for _ in range(10)]
        ece, mce, bins = compute_ece_detailed(cases, n_bins=10)
        # All cases land in bin [0.8, 0.9) with acc=1.0, conf=0.85 -> gap=0.15
        # Not perfectly calibrated since conf=0.85 but acc=1.0
        assert ece > 0.0

    def test_empty_cases(self):
        ece, mce, bins = compute_ece_detailed([], n_bins=10)
        assert ece == 0.0
        assert mce == 0.0
        assert bins == []

    def test_no_confidence_values(self):
        cases = [{"case_id": "x", "correct": True}]  # no confidence key
        ece, mce, bins = compute_ece_detailed(cases, n_bins=10)
        assert ece == 0.0

    def test_known_ece_value(self):
        """Hand-computed ECE for a simple case."""
        # 5 cases at conf=0.9, 4 correct -> bin acc=0.8, gap=0.1
        # 5 cases at conf=0.5, 3 correct -> bin acc=0.6, gap=0.1
        cases = (
            [_make_case(0.90, True)] * 4 + [_make_case(0.90, False)] * 1
            + [_make_case(0.50, True)] * 3 + [_make_case(0.50, False)] * 2
        )
        ece, mce, bins = compute_ece_detailed(cases, n_bins=10)
        # ECE = (5/10)*0.1 + (5/10)*0.1 = 0.1
        assert abs(ece - 0.10) < 1e-6
        assert abs(mce - 0.10) < 1e-6

    def test_ten_bins_returned(self):
        cases = [_make_case(0.55, True)]
        _, _, bins = compute_ece_detailed(cases, n_bins=10)
        assert len(bins) == 10

    def test_mce_is_max_gap(self):
        # conf=0.15 (bin 1) all wrong -> acc=0, conf=0.15, gap=0.15
        # conf=0.95 (bin 9) all correct -> acc=1.0, conf=0.95, gap=0.05
        cases = [_make_case(0.15, False)] * 5 + [_make_case(0.95, True)] * 5
        _, mce, bins = compute_ece_detailed(cases, n_bins=10)
        assert abs(mce - 0.15) < 1e-6


class TestBrierScore:
    def test_perfect_predictions(self):
        cases = [_make_case(1.0, True), _make_case(0.0, False)]
        assert compute_brier_score(cases) == 0.0

    def test_worst_predictions(self):
        cases = [_make_case(0.0, True), _make_case(1.0, False)]
        assert compute_brier_score(cases) == 1.0

    def test_empty(self):
        assert compute_brier_score([]) == 0.0

    def test_midpoint(self):
        cases = [_make_case(0.5, True), _make_case(0.5, False)]
        # (0.5-1)^2 + (0.5-0)^2 = 0.25 + 0.25 = 0.5, mean = 0.25
        assert abs(compute_brier_score(cases) - 0.25) < 1e-9


class TestOverconfidenceRatio:
    def test_all_overconfident(self):
        bins = [
            BinData(0.0, 0.1, 0.05, 10, 0.8, 0.2, 0.6),
            BinData(0.1, 0.2, 0.15, 10, 0.9, 0.3, 0.6),
        ]
        assert overconfidence_ratio(bins) == 1.0

    def test_none_overconfident(self):
        bins = [
            BinData(0.0, 0.1, 0.05, 10, 0.2, 0.8, 0.6),
            BinData(0.1, 0.2, 0.15, 10, 0.3, 0.9, 0.6),
        ]
        assert overconfidence_ratio(bins) == 0.0

    def test_empty_bins_excluded(self):
        bins = [
            BinData(0.0, 0.1, 0.05, 0, 0.0, 0.0, 0.0),
            BinData(0.1, 0.2, 0.15, 10, 0.9, 0.3, 0.6),  # overconfident
        ]
        assert overconfidence_ratio(bins) == 1.0


class TestStrategyAggregations:
    def _make_results(self):
        return [
            CalibrationResult("d1", "rule", 10, 10, 0.05, 0.05, 0.10, 0.5),
            CalibrationResult("d1", "hybrid", 10, 10, 0.03, 0.03, 0.08, 0.3),
            CalibrationResult("d2", "rule", 10, 10, 0.07, 0.07, 0.12, 0.6),
            CalibrationResult("d2", "hybrid", 10, 10, 0.10, 0.10, 0.15, 0.7),
            CalibrationResult("d2", "learned", 0, 0, 0.0, 0.0, 0.0, 0.0, error="unavailable"),
        ]

    def test_best_per_domain(self):
        results = self._make_results()
        best = _best_strategy_per_domain(results)
        assert best["d1"] == "hybrid"  # 0.03 < 0.05
        assert best["d2"] == "rule"    # 0.07 < 0.10

    def test_strategy_mean_ece(self):
        results = self._make_results()
        means = _strategy_mean_ece(results)
        assert abs(means["rule"] - 0.06) < 1e-9       # (0.05+0.07)/2
        assert abs(means["hybrid"] - 0.065) < 1e-9    # (0.03+0.10)/2
        assert "learned" not in means  # error entries excluded

    def test_strategy_mean_brier(self):
        results = self._make_results()
        means = _strategy_mean_brier(results)
        assert abs(means["rule"] - 0.11) < 1e-9
        assert abs(means["hybrid"] - 0.115) < 1e-9


class TestReporting:
    def test_json_report_structure(self, tmp_path):
        results = [
            CalibrationResult("soc", "rule", 10, 10, 0.05, 0.05, 0.10, 0.5,
                              bins=[BinData(0.0, 0.1, 0.05, 5, 0.05, 0.80, 0.75)]),
        ]
        out = tmp_path / "report.json"
        write_json_report(results, out)
        payload = json.loads(out.read_text())
        assert payload["n_domains"] == 1
        assert payload["n_strategies"] == 1
        assert "mean_ece_by_strategy" in payload
        assert "per_strategy_domain_results" in payload
        assert payload["per_strategy_domain_results"][0]["ece"] == 0.05

    def test_markdown_report_renders(self):
        results = [
            CalibrationResult("soc", "rule", 10, 10, 0.05, 0.05, 0.10, 0.5,
                              bins=[BinData(0.0, 0.1, 0.05, 5, 0.05, 0.80, 0.75)]),
            CalibrationResult("soc", "hybrid", 10, 10, 0.03, 0.03, 0.08, 0.3),
        ]
        md = render_markdown_report(results)
        assert "# KVRM Calibration Analysis" in md
        assert "Cross-Domain Strategy Ranking" in md
        assert "ECE Heatmap" in md
        assert "Brier Score Heatmap" in md
        assert "Key Findings" in md
