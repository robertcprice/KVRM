from __future__ import annotations

import pytest

from kvrm_bench.metrics import compute_metrics, compute_regret_metrics


def test_metric_aggregation_on_small_sample():
    metrics = compute_metrics([
        {'supported': True, 'ood': False, 'valid': True, 'correct': True, 'abstained': False, 'fallback_used': False, 'latency_ms': 1.0, 'final_status': 'executed'},
        {'supported': False, 'ood': True, 'valid': True, 'correct': False, 'abstained': True, 'fallback_used': True, 'latency_ms': 2.0, 'final_status': 'fallback_executed'},
    ])
    assert metrics['total_cases'] == 2
    assert metrics['structural_validity_rate'] == 1.0
    assert metrics['abstention_rate'] == 0.5
    assert metrics['mean_decision_cost'] == 0.0


def test_metric_aggregation_tracks_abstention_and_false_accept_cost():
    metrics = compute_metrics([
        {'supported': True, 'ood': False, 'valid': True, 'correct': False, 'abstained': True, 'fallback_used': True, 'latency_ms': 1.0, 'final_status': 'fallback_executed'},
        {'supported': True, 'ood': False, 'valid': True, 'correct': False, 'abstained': False, 'fallback_used': False, 'latency_ms': 1.0, 'final_status': 'executed'},
        {'supported': False, 'ood': True, 'valid': True, 'correct': False, 'abstained': False, 'fallback_used': False, 'latency_ms': 1.0, 'final_status': 'executed'},
        {'supported': False, 'ood': True, 'valid': True, 'correct': False, 'abstained': True, 'fallback_used': True, 'latency_ms': 1.0, 'final_status': 'fallback_executed'},
    ])
    assert metrics['supported_mean_decision_cost'] == 0.675
    assert metrics['unsupported_mean_decision_cost'] == 0.625
    assert metrics['mean_decision_cost'] == 0.65


def test_metric_aggregation_tracks_support_gate_activity():
    metrics = compute_metrics([
        {
            'supported': True,
            'ood': False,
            'valid': True,
            'correct': True,
            'abstained': False,
            'fallback_used': False,
            'latency_ms': 1.0,
            'final_status': 'executed',
            'support_gate_filtered_count': 1,
            'support_gate_rescued': True,
            'support_gate': None,
        },
        {
            'supported': False,
            'ood': True,
            'valid': True,
            'correct': False,
            'abstained': False,
            'fallback_used': False,
            'latency_ms': 1.0,
            'final_status': 'fallback_executed',
            'support_gate_filtered_count': 0,
            'support_gate_rescued': False,
            'support_gate': 'unsupported_context',
        },
        {
            'supported': False,
            'ood': True,
            'valid': True,
            'correct': False,
            'abstained': False,
            'fallback_used': False,
            'latency_ms': 1.0,
            'final_status': 'fallback_executed',
            'support_gate_filtered_count': 0,
            'support_gate_rescued': False,
            'support_gate': 'support_gate_exhausted',
        },
    ])

    assert metrics['support_gate_trigger_rate'] == 2 / 3
    assert metrics['supported_support_gate_rescue_rate'] == 1.0
    assert metrics['unsupported_support_gate_short_circuit_rate'] == 0.5
    assert metrics['support_gate_exhausted_rate'] == 1 / 3


def test_regret_metrics_discount_safe_abstention_but_not_severe_errors():
    regret = compute_regret_metrics([
        {'supported': True, 'ood': False, 'valid': True, 'correct': True, 'abstained': False, 'fallback_used': False, 'latency_ms': 1.0, 'final_status': 'executed'},
        {'supported': True, 'ood': False, 'valid': True, 'correct': False, 'abstained': True, 'fallback_used': True, 'latency_ms': 1.0, 'final_status': 'fallback_executed'},
        {'supported': True, 'ood': False, 'valid': True, 'correct': False, 'abstained': False, 'fallback_used': False, 'latency_ms': 1.0, 'final_status': 'executed'},
        {'supported': False, 'ood': True, 'valid': True, 'correct': False, 'abstained': False, 'fallback_used': False, 'latency_ms': 1.0, 'final_status': 'executed'},
    ])

    assert regret['mean_decision_regret'] == pytest.approx(0.6125)
    assert regret['supported_mean_decision_regret'] == pytest.approx(0.4)
    assert regret['unsupported_mean_decision_regret'] == pytest.approx(1.25)
    assert regret['supported_abstention_regret_rate'] == pytest.approx(1 / 3)
    assert regret['severe_regret_rate'] == pytest.approx(0.5)
