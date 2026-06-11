from __future__ import annotations

import numpy as np

from kvrm_core.calibration import (
    DistanceRejector,
    EvidenceFusionCalibrator,
    IsotonicScaler,
    PlattScaler,
    TemperatureScaler,
    ThresholdCalibrator,
)
from kvrm_core.types import DecisionCandidate


def test_threshold_calibrator_abstains_below_threshold():
    candidate, abstain = ThresholdCalibrator(threshold=0.6).choose([DecisionCandidate(action_id="a", confidence=0.5)])
    assert candidate.action_id == "a"
    assert abstain is True


def test_threshold_calibrator_keeps_action_above_threshold():
    candidate, abstain = ThresholdCalibrator(threshold=0.6).choose([DecisionCandidate(action_id="a", confidence=0.9)])
    assert candidate.action_id == "a"
    assert abstain is False


def test_threshold_calibrator_uses_support_confidence():
    candidate, abstain = ThresholdCalibrator(threshold=0.6).choose([
        DecisionCandidate(action_id="a", confidence=0.95, support_confidence=0.4),
        DecisionCandidate(action_id="b", confidence=0.7, support_confidence=0.7),
    ])
    assert candidate.action_id == "b"
    assert abstain is False


def test_distance_rejector_flags_large_distance():
    rejector = DistanceRejector(max_distance=0.25)
    assert rejector.reject(0.3) is True


def test_evidence_fusion_calibrator_rewards_cross_source_agreement():
    candidate, abstain = EvidenceFusionCalibrator(threshold=0.6).choose(
        [
            DecisionCandidate(action_id="a", confidence=0.58, source="hybrid:retrieval"),
            DecisionCandidate(action_id="a", confidence=0.57, source="hybrid:prototype", agreement=1.0, margin=2.0),
            DecisionCandidate(action_id="b", confidence=0.61, source="hybrid:semantic"),
        ]
    )
    assert candidate is not None
    assert candidate.action_id == "a"
    assert candidate.source == "evidence_fusion_calibrator"
    assert candidate.evidence["fused_source_families"] == ["prototype", "retrieval"]
    assert abstain is False


def test_evidence_fusion_calibrator_penalizes_close_multi_source_conflicts():
    candidate, abstain = EvidenceFusionCalibrator(threshold=0.68).choose(
        [
            DecisionCandidate(action_id="a", confidence=0.70, source="hybrid:retrieval"),
            DecisionCandidate(action_id="a", confidence=0.68, source="hybrid:prototype"),
            DecisionCandidate(action_id="b", confidence=0.69, source="hybrid:rule"),
            DecisionCandidate(action_id="b", confidence=0.68, source="hybrid:semantic"),
        ]
    )
    assert candidate is not None
    assert candidate.action_id == "a"
    assert candidate.evidence["ambiguity_penalty"] > 0.0
    assert candidate.effective_confidence() < 0.68
    assert abstain is True


def test_evidence_fusion_calibrator_does_not_let_fallback_consensus_overpower_supported_action():
    candidate, abstain = EvidenceFusionCalibrator(threshold=0.6).choose(
        [
            DecisionCandidate(
                action_id="manual_review",
                confidence=0.98,
                source="hybrid:semantic",
                evidence={"support_gate": "fallback_action", "is_fallback_action": True, "support_leaf_count": 5},
            ),
            DecisionCandidate(
                action_id="manual_review",
                confidence=0.92,
                source="hybrid:prototype",
                agreement=0.66,
                margin=1.73,
                evidence={"support_gate": "fallback_action", "is_fallback_action": True, "support_leaf_count": 5},
            ),
            DecisionCandidate(
                action_id="lower_limit_temporarily",
                confidence=0.90,
                source="hybrid:semantic",
                evidence={"support_gate": "passed", "support_leaf_count": 6},
            ),
        ]
    )

    assert candidate is not None
    assert candidate.action_id == "lower_limit_temporarily"
    assert candidate.evidence.get("ambiguity_penalty") is None
    assert abstain is False


# ---------------------------------------------------------------------------
# Expected Calibration Error helper
# ---------------------------------------------------------------------------


def _expected_calibration_error(confidences: list[float], labels: list[int], n_bins: int = 10) -> float:
    """Compute ECE: weighted average of |avg_confidence - avg_accuracy| per bin."""
    confs = np.asarray(confidences)
    labs = np.asarray(labels)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (confs > lo) & (confs <= hi)
        if mask.sum() == 0:
            continue
        avg_conf = confs[mask].mean()
        avg_acc = labs[mask].mean()
        ece += mask.sum() / len(confs) * abs(avg_conf - avg_acc)
    return float(ece)


# ---------------------------------------------------------------------------
# TemperatureScaler
# ---------------------------------------------------------------------------


def test_temperature_scaler_unfitted_returns_identity():
    """Before fitting, T=1 so transform is the identity (sigmoid(logit) = original)."""
    scaler = TemperatureScaler()
    for c in [0.1, 0.3, 0.5, 0.7, 0.95]:
        assert abs(scaler.transform(c) - c) < 1e-6


def test_temperature_scaler_fit_learns_temperature_above_one_for_overconfident_data():
    """When predictions are systematically overconfident, the learned T should exceed 1."""
    # Overconfident: all predictions near 0.95, but only ~half are actually positive.
    rng = np.random.default_rng(42)
    n = 200
    confidences = rng.uniform(0.85, 0.99, size=n).tolist()
    labels = rng.integers(0, 2, size=n).tolist()

    scaler = TemperatureScaler()
    scaler.fit(confidences, labels)

    assert scaler._fitted is True
    assert scaler.temperature > 1.0, f"Expected T > 1 for overconfident data, got {scaler.temperature}"


def test_temperature_scaler_reduces_overconfident_predictions():
    """After fitting on overconfident data, transform should push high confidences down."""
    rng = np.random.default_rng(99)
    n = 200
    confidences = rng.uniform(0.85, 0.99, size=n).tolist()
    labels = rng.integers(0, 2, size=n).tolist()

    scaler = TemperatureScaler().fit(confidences, labels)

    # Every high-confidence value should be reduced (T > 1 shrinks toward 0.5).
    for c in [0.90, 0.95, 0.99]:
        calibrated = scaler.transform(c)
        assert calibrated < c, f"Expected {calibrated} < {c} after temperature scaling"

    # 0.5 stays at 0.5 regardless of T (logit = 0).
    assert abs(scaler.transform(0.5) - 0.5) < 1e-6


def test_temperature_scaler_single_sample_defaults():
    """With fewer than 2 samples, fit sets T=1 without error."""
    scaler = TemperatureScaler().fit([0.9], [1])
    assert scaler.temperature == 1.0
    assert scaler._fitted is True


# ---------------------------------------------------------------------------
# PlattScaler
# ---------------------------------------------------------------------------


def test_platt_scaler_output_bounded_zero_one():
    """Transform output must always be in [0, 1] for any input."""
    rng = np.random.default_rng(77)
    n = 200
    confs = rng.uniform(0.0, 1.0, size=n).tolist()
    labs = (rng.uniform(size=n) < np.array(confs)).astype(int).tolist()

    scaler = PlattScaler().fit(confs, labs)

    for c in [0.0, 0.01, 0.25, 0.5, 0.75, 0.99, 1.0]:
        out = scaler.transform(c)
        assert 0.0 <= out <= 1.0, f"Platt output {out} out of [0,1] for input {c}"


def test_platt_scaler_corrects_biased_data():
    """When raw confidences are systematically biased high, Platt should recalibrate down."""
    # Positive class has conf ~0.8, negative class also has conf ~0.8 (all biased high).
    rng = np.random.default_rng(123)
    n = 300
    labels = rng.integers(0, 2, size=n).tolist()
    confidences = [0.80 + rng.uniform(-0.05, 0.05) for _ in range(n)]

    scaler = PlattScaler().fit(confidences, labels)
    assert scaler._fitted is True

    # A raw 0.80 should be recalibrated closer to 0.50 (the true accuracy at that conf).
    calibrated = scaler.transform(0.80)
    assert calibrated < 0.80, f"Expected recalibrated < 0.80, got {calibrated}"


def test_platt_scaler_degenerate_labels_defaults():
    """With a single class in labels, Platt should fall back to identity parameters."""
    scaler = PlattScaler().fit([0.5, 0.6, 0.7], [1, 1, 1])
    assert scaler.a == 1.0
    assert scaler.b == 0.0


# ---------------------------------------------------------------------------
# IsotonicScaler
# ---------------------------------------------------------------------------


def test_isotonic_scaler_unfitted_returns_input():
    """Before fitting, transform returns the input unchanged."""
    scaler = IsotonicScaler()
    assert scaler.transform(0.42) == 0.42


def test_isotonic_scaler_output_is_monotone():
    """After fitting, transform must be non-decreasing."""
    rng = np.random.default_rng(55)
    n = 300
    confs = sorted(rng.uniform(0.0, 1.0, size=n).tolist())
    # True probability increases with confidence (well-calibrated, noisy).
    labels = [int(rng.random() < c) for c in confs]

    scaler = IsotonicScaler().fit(confs, labels)
    assert scaler._fitted is True

    test_inputs = [i / 20.0 for i in range(21)]
    outputs = [scaler.transform(c) for c in test_inputs]
    for i in range(1, len(outputs)):
        assert outputs[i] >= outputs[i - 1] - 1e-9, (
            f"Monotonicity violated: f({test_inputs[i]})={outputs[i]} < f({test_inputs[i-1]})={outputs[i-1]}"
        )


def test_isotonic_scaler_output_bounded():
    """IsotonicScaler with y_min=0, y_max=1 should always produce [0, 1]."""
    rng = np.random.default_rng(66)
    n = 200
    confs = rng.uniform(0.0, 1.0, size=n).tolist()
    labels = [int(rng.random() < c) for c in confs]

    scaler = IsotonicScaler().fit(confs, labels)
    for c in [0.0, 0.01, 0.5, 0.99, 1.0]:
        out = scaler.transform(c)
        assert 0.0 <= out <= 1.0, f"Isotonic output {out} out of [0,1] for input {c}"


def test_isotonic_scaler_improves_calibration():
    """Fitting on known-miscalibrated data should reduce ECE."""
    rng = np.random.default_rng(88)
    n = 500
    # Overconfident predictions: raw confidence near 0.9, true accuracy ~0.5.
    confs = rng.uniform(0.80, 0.99, size=n).tolist()
    labels = rng.integers(0, 2, size=n).tolist()

    ece_before = _expected_calibration_error(confs, labels)

    scaler = IsotonicScaler().fit(confs, labels)
    calibrated = [scaler.transform(c) for c in confs]
    ece_after = _expected_calibration_error(calibrated, labels)

    assert ece_after < ece_before, f"ECE should decrease: {ece_after} >= {ece_before}"


# ---------------------------------------------------------------------------
# Integration: each scaler reduces ECE on hybrid predictions
# ---------------------------------------------------------------------------


def _make_overconfident_hybrid_data(rng: np.random.Generator, n: int = 400):
    """Generate synthetic overconfident predictions and ground-truth labels."""
    # True probability is uniform, but raw confidence is biased upward.
    true_prob = rng.uniform(0.2, 0.8, size=n)
    labels = (rng.uniform(size=n) < true_prob).astype(int).tolist()
    # Raw confidence = true_prob + 0.2  (clamped to [0, 1]).
    confidences = np.clip(true_prob + 0.20, 0.0, 1.0).tolist()
    return confidences, labels


def test_integration_temperature_scaler_reduces_ece():
    rng = np.random.default_rng(1001)
    confs, labels = _make_overconfident_hybrid_data(rng)
    ece_before = _expected_calibration_error(confs, labels)

    scaler = TemperatureScaler().fit(confs, labels)
    calibrated = [scaler.transform(c) for c in confs]
    ece_after = _expected_calibration_error(calibrated, labels)

    assert ece_after < ece_before, f"TemperatureScaler ECE: {ece_after} >= {ece_before}"


def test_integration_platt_scaler_reduces_ece():
    rng = np.random.default_rng(1002)
    confs, labels = _make_overconfident_hybrid_data(rng)
    ece_before = _expected_calibration_error(confs, labels)

    scaler = PlattScaler().fit(confs, labels)
    calibrated = [scaler.transform(c) for c in confs]
    ece_after = _expected_calibration_error(calibrated, labels)

    assert ece_after < ece_before, f"PlattScaler ECE: {ece_after} >= {ece_before}"


def test_integration_isotonic_scaler_reduces_ece():
    rng = np.random.default_rng(1003)
    confs, labels = _make_overconfident_hybrid_data(rng)
    ece_before = _expected_calibration_error(confs, labels)

    scaler = IsotonicScaler().fit(confs, labels)
    calibrated = [scaler.transform(c) for c in confs]
    ece_after = _expected_calibration_error(calibrated, labels)

    assert ece_after < ece_before, f"IsotonicScaler ECE: {ece_after} >= {ece_before}"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_threshold_calibrator_returns_none_on_empty_candidates():
    chosen, abstain = ThresholdCalibrator(threshold=0.5).choose([])
    assert chosen is None
    assert abstain is True


def test_evidence_fusion_calibrator_returns_none_on_empty_candidates():
    chosen, abstain = EvidenceFusionCalibrator(threshold=0.5).choose([])
    assert chosen is None
    assert abstain is True


def test_temperature_scaler_handles_boundary_confidences():
    """Extreme confidences (near 0 or 1) should not produce NaN or Inf."""
    scaler = TemperatureScaler(temperature=1.5)
    assert 0.0 <= scaler.transform(0.001) <= 1.0
    assert 0.0 <= scaler.transform(0.999) <= 1.0
    assert 0.0 <= scaler.transform(0.0) <= 1.0
    assert 0.0 <= scaler.transform(1.0) <= 1.0
