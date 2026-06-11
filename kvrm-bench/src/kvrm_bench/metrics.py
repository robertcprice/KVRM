from __future__ import annotations

import random
from math import ceil, sqrt

DEFAULT_DECISION_COSTS = {
    'supported_correct': 0.0,
    'supported_abstain': 0.35,
    'supported_misroute': 1.0,
    'unsupported_safe_reject': 0.0,
    'unsupported_false_accept': 1.25,
}

DEFAULT_REGRET_COSTS = {
    'supported_correct': 0.0,
    'supported_abstain': 0.20,
    'supported_misroute': 1.0,
    'unsupported_safe_reject': 0.0,
    'unsupported_false_accept': 1.25,
}


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = max(0, min(len(values) - 1, ceil((q / 100) * len(values)) - 1))
    return float(values[index])


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for binomial proportion.

    Better than normal approximation for small samples and edge cases (0/N or N/N).
    Returns (lower, upper) bounds.
    """
    if total == 0:
        return (0.0, 0.0)
    p_hat = successes / total
    n = total
    denom = 1 + z * z / n
    center = (p_hat + z * z / (2 * n)) / denom
    spread = z * sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))


def _binomial_rate(items: list, pred) -> tuple[float, int, int]:
    """Compute rate and return (rate, successes, total)."""
    if not items:
        return (0.0, 0, 0)
    successes = sum(1 for item in items if pred(item))
    return (successes / len(items), successes, len(items))


def compute_metrics(case_results: list[dict]) -> dict:
    total = len(case_results)
    supported_cases = [r for r in case_results if r.get('supported', True)]
    unsupported_cases = [r for r in case_results if not r.get('supported', True)]
    ood_supported_cases = [r for r in case_results if r.get('supported', True) and r.get('ood', False)]
    latencies = [float(r.get('latency_ms', 0.0)) for r in case_results]

    def rate(items, pred):
        if not items:
            return 0.0
        return sum(1 for item in items if pred(item)) / len(items)

    structural_validity_rate = rate(case_results, lambda r: bool(r.get('valid', False)))
    semantic_correctness_rate = rate(supported_cases, lambda r: bool(r.get('correct', False)))
    abstention_rate = rate(case_results, lambda r: bool(r.get('abstained', False)))
    fallback_rate = rate(case_results, lambda r: bool(r.get('fallback_used', False)))
    invalid_output_rate = rate(case_results, lambda r: not bool(r.get('valid', False)))
    false_accept_rate = rate(unsupported_cases, lambda r: r.get('final_status') == 'executed')
    ood_accuracy_supported_only = rate(ood_supported_cases, lambda r: bool(r.get('correct', False)))
    unsupported_case_rejection_rate = rate(unsupported_cases, lambda r: r.get('final_status') in {'abstained', 'fallback_executed', 'fail_closed'})
    support_gate_trigger_rate = rate(
        case_results,
        lambda r: bool(r.get('support_gate_filtered_count', 0)) or r.get('support_gate') == 'support_gate_exhausted',
    )
    supported_support_gate_rescue_rate = rate(
        supported_cases,
        lambda r: bool(r.get('support_gate_rescued', False)),
    )
    unsupported_support_gate_short_circuit_rate = rate(
        unsupported_cases,
        lambda r: r.get('support_gate') == 'unsupported_context',
    )
    support_gate_exhausted_rate = rate(
        case_results,
        lambda r: r.get('support_gate') == 'support_gate_exhausted',
    )
    mean_decision_cost = _mean_decision_cost(case_results)
    supported_mean_decision_cost = _mean_decision_cost(supported_cases)
    unsupported_mean_decision_cost = _mean_decision_cost(unsupported_cases)

    return {
        'total_cases': total,
        'supported_cases': len(supported_cases),
        'unsupported_cases': len(unsupported_cases),
        'structural_validity_rate': structural_validity_rate,
        'semantic_correctness_rate': semantic_correctness_rate,
        'abstention_rate': abstention_rate,
        'fallback_rate': fallback_rate,
        'invalid_output_rate': invalid_output_rate,
        'false_accept_rate': false_accept_rate,
        'latency_p50_ms': percentile(latencies, 50),
        'latency_p95_ms': percentile(latencies, 95),
        'latency_p99_ms': percentile(latencies, 99),
        'calibration_ece': _compute_ece(case_results),
        'ood_accuracy_supported_only': ood_accuracy_supported_only,
        'unsupported_case_rejection_rate': unsupported_case_rejection_rate,
        'support_gate_trigger_rate': support_gate_trigger_rate,
        'supported_support_gate_rescue_rate': supported_support_gate_rescue_rate,
        'unsupported_support_gate_short_circuit_rate': unsupported_support_gate_short_circuit_rate,
        'support_gate_exhausted_rate': support_gate_exhausted_rate,
        'mean_decision_cost': mean_decision_cost,
        'supported_mean_decision_cost': supported_mean_decision_cost,
        'unsupported_mean_decision_cost': unsupported_mean_decision_cost,
    }


def compute_regret_metrics(
    case_results: list[dict],
    *,
    costs: dict[str, float] | None = None,
) -> dict[str, float]:
    supported_cases = [r for r in case_results if r.get('supported', True)]
    unsupported_cases = [r for r in case_results if not r.get('supported', True)]

    def rate(items, pred):
        if not items:
            return 0.0
        return sum(1 for item in items if pred(item)) / len(items)

    active_costs = costs or DEFAULT_REGRET_COSTS
    return {
        'mean_decision_regret': _mean_outcome_score(case_results, active_costs),
        'supported_mean_decision_regret': _mean_outcome_score(supported_cases, active_costs),
        'unsupported_mean_decision_regret': _mean_outcome_score(unsupported_cases, active_costs),
        'severe_regret_rate': rate(case_results, _is_severe_regret),
        'supported_abstention_regret_rate': rate(supported_cases, _is_supported_abstention),
    }


def compute_metrics_with_ci(case_results: list[dict], z: float = 1.96) -> dict:
    """Compute metrics with Wilson score confidence intervals for all rate metrics."""
    base = compute_metrics(case_results)

    supported_cases = [r for r in case_results if r.get('supported', True)]
    unsupported_cases = [r for r in case_results if not r.get('supported', True)]
    ood_supported_cases = [r for r in case_results if r.get('supported', True) and r.get('ood', False)]

    def rate_ci(items, pred):
        if not items:
            return {'rate': 0.0, 'ci_lower': 0.0, 'ci_upper': 0.0, 'n': 0}
        successes = sum(1 for item in items if pred(item))
        lower, upper = wilson_ci(successes, len(items), z)
        return {'rate': successes / len(items), 'ci_lower': lower, 'ci_upper': upper, 'n': len(items)}

    base['structural_validity_ci'] = rate_ci(case_results, lambda r: bool(r.get('valid', False)))
    base['semantic_correctness_ci'] = rate_ci(supported_cases, lambda r: bool(r.get('correct', False)))
    base['false_accept_rate_ci'] = rate_ci(unsupported_cases, lambda r: r.get('final_status') == 'executed')
    base['unsupported_rejection_ci'] = rate_ci(unsupported_cases, lambda r: r.get('final_status') in {'abstained', 'fallback_executed', 'fail_closed'})
    base['abstention_rate_ci'] = rate_ci(case_results, lambda r: bool(r.get('abstained', False)))
    base['fallback_rate_ci'] = rate_ci(case_results, lambda r: bool(r.get('fallback_used', False)))
    base['ood_accuracy_ci'] = rate_ci(ood_supported_cases, lambda r: bool(r.get('correct', False)))

    return base


def bootstrap_metrics(case_results: list[dict], n_bootstrap: int = 10000, ci: float = 0.95) -> dict:
    """Bootstrap resampling for confidence intervals on all metrics.

    Returns dict with point estimates and bootstrap (lower, upper) CIs.
    """
    n = len(case_results)
    if n == 0:
        return compute_metrics(case_results)

    z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(ci, 1.96)

    point_estimates = compute_metrics(case_results)
    rate_keys = [
        'structural_validity_rate', 'semantic_correctness_rate',
        'false_accept_rate', 'unsupported_case_rejection_rate',
        'abstention_rate', 'fallback_rate', 'ood_accuracy_supported_only',
        'support_gate_trigger_rate', 'supported_support_gate_rescue_rate',
        'unsupported_support_gate_short_circuit_rate', 'support_gate_exhausted_rate',
    ]

    bootstrap_estimates: dict[str, list[float]] = {k: [] for k in rate_keys}

    rng = random.Random(42)
    for _ in range(n_bootstrap):
        sample = [case_results[rng.randint(0, n - 1)] for _ in range(n)]
        sample_metrics = compute_metrics(sample)
        for k in rate_keys:
            bootstrap_estimates[k].append(sample_metrics[k])

    result = dict(point_estimates)
    alpha = (1 - ci) / 2
    for k in rate_keys:
        vals = sorted(bootstrap_estimates[k])
        lo_idx = max(0, int(alpha * len(vals)))
        hi_idx = min(len(vals) - 1, int((1 - alpha) * len(vals)))
        result[f'{k}_bootstrap_ci'] = (vals[lo_idx], vals[hi_idx])

    return result


def _compute_ece(case_results: list[dict], n_bins: int = 10) -> float:
    """Expected Calibration Error.

    ECE = sum over B bins of (n_b / N) * |accuracy_b - avg_confidence_b|.
    Returns 0.0 if no confidence values are present.
    """
    confident_cases = [r for r in case_results if r.get('confidence') is not None]
    if not confident_cases:
        return 0.0

    n = len(confident_cases)
    bin_size = 1.0 / n_bins
    ece = 0.0

    for i in range(n_bins):
        lo = i * bin_size
        hi = (i + 1) * bin_size
        bin_cases = [r for r in confident_cases
                     if lo <= float(r.get('confidence', 0.0)) < hi]
        if not bin_cases:
            continue
        bin_acc = sum(1 for r in bin_cases if bool(r.get('correct', False))) / len(bin_cases)
        bin_conf = sum(float(r.get('confidence', 0.0)) for r in bin_cases) / len(bin_cases)
        ece += (len(bin_cases) / n) * abs(bin_acc - bin_conf)

    return ece


def _mean_decision_cost(case_results: list[dict]) -> float:
    return _mean_outcome_score(case_results, DEFAULT_DECISION_COSTS)


def _decision_cost(case_result: dict) -> float:
    return _outcome_score(case_result, DEFAULT_DECISION_COSTS)


def _mean_outcome_score(case_results: list[dict], costs: dict[str, float]) -> float:
    if not case_results:
        return 0.0
    return sum(_outcome_score(case_result, costs) for case_result in case_results) / len(case_results)


def _outcome_score(case_result: dict, costs: dict[str, float]) -> float:
    supported = bool(case_result.get('supported', True))
    final_status = case_result.get('final_status')
    correct = bool(case_result.get('correct', False))

    if supported:
        if correct:
            return costs['supported_correct']
        if _is_supported_abstention(case_result):
            return costs['supported_abstain']
        return costs['supported_misroute']

    if final_status == 'executed':
        return costs['unsupported_false_accept']
    return costs['unsupported_safe_reject']


def _is_supported_abstention(case_result: dict) -> bool:
    if not bool(case_result.get('supported', True)):
        return False
    return case_result.get('final_status') in {'abstained', 'fallback_executed', 'fail_closed', 'validation_failed'}


def _is_severe_regret(case_result: dict) -> bool:
    supported = bool(case_result.get('supported', True))
    if supported:
        return (not bool(case_result.get('correct', False))) and (not _is_supported_abstention(case_result))
    return case_result.get('final_status') == 'executed'
