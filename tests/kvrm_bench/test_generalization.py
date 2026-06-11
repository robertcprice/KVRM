"""Tests for kvrm_bench.generalization module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from kvrm_bench.generalization import (
    _load_supported_cases,
    confusion_summary,
    per_class_accuracy,
    run_loocv,
    run_stratified_kfold,
)


# ── fixtures ────────────────────────────────────────────────────────────────────

def _make_cases(n_per_class: int = 4) -> list[dict]:
    """Fabricate a small training set with 3 classes and clear feature separation."""
    cases = []
    idx = 0
    for action_id, severity, score_range in [
        ("action_a", "high", (0.8, 1.0)),
        ("action_b", "medium", (0.4, 0.6)),
        ("action_c", "low", (0.0, 0.2)),
    ]:
        for i in range(n_per_class):
            score = score_range[0] + (score_range[1] - score_range[0]) * (i / max(n_per_class - 1, 1))
            cases.append({
                "case_id": f"case_{idx}",
                "input_features": {"severity": severity, "score": score},
                "expected_action_id": action_id,
                "supported": True,
            })
            idx += 1
    return cases


# ── tests: LOOCV ────────────────────────────────────────────────────────────────

def test_loocv_returns_expected_keys():
    cases = _make_cases(4)
    result = run_loocv(cases)
    assert "accuracy" in result
    assert "n_cases" in result
    assert "n_correct" in result
    assert "n_misclassified" in result
    assert "misclassified" in result
    assert "y_true" in result
    assert "y_pred" in result


def test_loocv_accuracy_range():
    cases = _make_cases(4)
    result = run_loocv(cases)
    assert 0.0 <= result["accuracy"] <= 1.0
    assert result["n_cases"] == len(cases)
    assert result["n_correct"] + result["n_misclassified"] == result["n_cases"]


def test_loocv_perfect_on_well_separated_data():
    """With well-separated features, LOOCV should be perfect or near-perfect."""
    cases = _make_cases(6)
    result = run_loocv(cases)
    # With such clear separation, accuracy should be quite high
    assert result["accuracy"] >= 0.8


def test_loocv_y_true_y_pred_lengths():
    cases = _make_cases(3)
    result = run_loocv(cases)
    assert len(result["y_true"]) == len(cases)
    assert len(result["y_pred"]) == len(cases)


def test_loocv_misclassified_entries_have_required_fields():
    cases = _make_cases(3)
    result = run_loocv(cases)
    for mc in result["misclassified"]:
        assert "case_id" in mc
        assert "true" in mc
        assert "predicted" in mc
        assert mc["true"] != mc["predicted"]


# ── tests: stratified K-fold ────────────────────────────────────────────────────

def test_kfold_returns_expected_keys():
    cases = _make_cases(4)
    result = run_stratified_kfold(cases)
    assert "k" in result
    assert "overall_accuracy" in result
    assert "mean_fold_accuracy" in result
    assert "std_fold_accuracy" in result
    assert "fold_accuracies" in result


def test_kfold_k_capped_at_min_class_size():
    cases = _make_cases(3)
    result = run_stratified_kfold(cases)
    assert result["k"] <= 3  # min class size
    assert result["k"] >= 2  # floor


def test_kfold_fold_count_matches_k():
    cases = _make_cases(5)
    result = run_stratified_kfold(cases, k=3)
    assert len(result["fold_accuracies"]) == 3


def test_kfold_accuracy_range():
    cases = _make_cases(4)
    result = run_stratified_kfold(cases)
    assert 0.0 <= result["overall_accuracy"] <= 1.0
    for fa in result["fold_accuracies"]:
        assert 0.0 <= fa <= 1.0


# ── tests: per-class accuracy ───────────────────────────────────────────────────

def test_per_class_accuracy_perfect():
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "a", "b", "b"]
    pca = per_class_accuracy(y_true, y_pred)
    assert pca["a"]["accuracy"] == 1.0
    assert pca["b"]["accuracy"] == 1.0
    assert pca["a"]["errors"] == {}


def test_per_class_accuracy_with_errors():
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "b", "b", "a"]
    pca = per_class_accuracy(y_true, y_pred)
    assert pca["a"]["accuracy"] == 0.5
    assert pca["a"]["errors"] == {"b": 1}
    assert pca["b"]["accuracy"] == 0.5
    assert pca["b"]["errors"] == {"a": 1}


def test_per_class_accuracy_support_counts():
    y_true = ["a", "a", "a", "b"]
    y_pred = ["a", "a", "a", "b"]
    pca = per_class_accuracy(y_true, y_pred)
    assert pca["a"]["support"] == 3
    assert pca["b"]["support"] == 1


# ── tests: confusion summary ────────────────────────────────────────────────────

def test_confusion_summary_shape():
    y_true = ["a", "a", "b", "b", "c"]
    y_pred = ["a", "b", "b", "c", "c"]
    cm = confusion_summary(y_true, y_pred)
    assert len(cm["labels"]) == 3
    assert len(cm["matrix"]) == 3
    assert all(len(row) == 3 for row in cm["matrix"])


def test_confusion_summary_diagonal_sum():
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "a", "b", "b"]
    cm = confusion_summary(y_true, y_pred)
    diag = sum(cm["matrix"][i][i] for i in range(len(cm["labels"])))
    assert diag == 4


# ── tests: file loading ─────────────────────────────────────────────────────────

def test_load_supported_cases_filters_correctly():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Supported with label
        json.dump({"case_id": "c1", "input_features": {"x": 1}, "expected_action_id": "a", "supported": True}, f)
        f.write("\n")
        # Unsupported — should be excluded
        json.dump({"case_id": "c2", "input_features": {"x": 2}, "expected_action_id": "b", "supported": False}, f)
        f.write("\n")
        # No label — should be excluded
        json.dump({"case_id": "c3", "input_features": {"x": 3}, "supported": True}, f)
        f.write("\n")
        # No supported key — defaults to True
        json.dump({"case_id": "c4", "input_features": {"x": 4}, "expected_action_id": "c"}, f)
        f.write("\n")
        tmp_path = Path(f.name)

    cases = _load_supported_cases(tmp_path)
    assert len(cases) == 2
    assert cases[0]["case_id"] == "c1"
    assert cases[1]["case_id"] == "c4"
    tmp_path.unlink()
