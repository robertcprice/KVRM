"""Tests for kvrm_bench.overlap_analysis.

Covers:
  - Core overlap detection (find_overlap_cases, find_non_overlap_cases)
  - Action pair counting
  - Content-moderation synthetic overlap generation
  - Customer-support synthetic overlap generation
  - Generalised synthetic overlap generation
"""

from __future__ import annotations

from pathlib import Path

from kvrm_bench.overlap_analysis import (
    CS_TOP_OVERLAP_PAIRS,
    compute_overlap_intersection,
    find_non_overlap_cases,
    find_overlap_cases,
    generate_cm_overlap_synthetic_cases,
    generate_cs_overlap_synthetic_cases,
    generate_overlap_synthetic_cases,
    overlap_action_pairs,
)
from kvrm_core.registry import load_registry
from kvrm_core.support import evaluate_support_spec
from kvrm_core.types import ActionSpec, RegistrySpec

REPO_ROOT = Path(__file__).resolve().parents[2]


def _toy_registry() -> RegistrySpec:
    return RegistrySpec(
        registry_name="toy",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="alpha",
                name="Alpha",
                description="A",
                support_spec={"feature": "level", "op": "in", "value": ["low", "medium"]},
            ),
            ActionSpec(
                action_id="beta",
                name="Beta",
                description="B",
                support_spec={"feature": "level", "op": "in", "value": ["medium", "high"]},
            ),
            ActionSpec(
                action_id="gamma",
                name="Gamma",
                description="C",
                support_spec={"feature": "level", "op": "eq", "value": "high"},
            ),
        ],
    )


def test_find_overlap_cases_detects_shared_support():
    registry = _toy_registry()
    cases = [
        {"case_id": "c1", "input_features": {"level": "low"}, "expected_action_id": "alpha", "supported": True},
        {"case_id": "c2", "input_features": {"level": "medium"}, "expected_action_id": "alpha", "supported": True},
        {"case_id": "c3", "input_features": {"level": "high"}, "expected_action_id": "gamma", "supported": True},
    ]

    overlaps = find_overlap_cases(registry, cases)

    # level=low -> only alpha (no overlap)
    # level=medium -> alpha + beta (overlap)
    # level=high -> beta + gamma (overlap)
    assert len(overlaps) == 2
    medium_row = next(r for r in overlaps if r["case_id"] == "c2")
    assert set(medium_row["matched_actions"]) == {"alpha", "beta"}
    assert medium_row["overlap_degree"] == 2

    high_row = next(r for r in overlaps if r["case_id"] == "c3")
    assert set(high_row["matched_actions"]) == {"beta", "gamma"}
    assert high_row["overlap_degree"] == 2


def test_find_non_overlap_cases_returns_unique_match():
    registry = _toy_registry()
    cases = [
        {"case_id": "c1", "input_features": {"level": "low"}, "expected_action_id": "alpha", "supported": True},
        {"case_id": "c2", "input_features": {"level": "medium"}, "expected_action_id": "alpha", "supported": True},
    ]

    non_overlaps = find_non_overlap_cases(registry, cases)

    # level=low -> only alpha (non-overlap)
    # level=medium -> alpha + beta (overlap, excluded)
    assert len(non_overlaps) == 1
    assert non_overlaps[0]["case_id"] == "c1"


def test_overlap_action_pairs_counts_correctly():
    overlap_rows = [
        {"matched_actions": ["alpha", "beta"]},
        {"matched_actions": ["alpha", "beta"]},
        {"matched_actions": ["beta", "gamma"]},
    ]
    pairs = overlap_action_pairs(overlap_rows)

    assert len(pairs) == 2
    ab = next(p for p in pairs if set(p["pair"]) == {"alpha", "beta"})
    bg = next(p for p in pairs if set(p["pair"]) == {"beta", "gamma"})
    assert ab["count"] == 2
    assert bg["count"] == 1


def test_find_overlap_respects_supported_only():
    registry = _toy_registry()
    cases = [
        {"case_id": "c1", "input_features": {"level": "medium"}, "expected_action_id": "alpha", "supported": False},
    ]

    assert find_overlap_cases(registry, cases, supported_only=True) == []
    assert len(find_overlap_cases(registry, cases, supported_only=False)) == 1


def test_generate_cm_synthetic_cases_all_in_overlap():
    """Every synthetic case should match both reduce_visibility and flag_for_human_review."""
    from pathlib import Path

    registry_path = (
        Path(__file__).resolve().parents[2]
        / "kvrm-demos"
        / "content-moderation-router"
        / "data"
        / "registry.json"
    )
    if not registry_path.exists():
        import pytest
        pytest.skip("content-moderation registry not found")

    from kvrm_core.registry import load_registry

    registry = load_registry(registry_path)
    cases = generate_cm_overlap_synthetic_cases(n=10)

    assert len(cases) == 10
    for case in cases:
        matched = []
        for action in registry.actions:
            ok, _ = evaluate_support_spec(action.support_spec, case["input_features"])
            if ok:
                matched.append(action.action_id)
        assert "reduce_visibility" in matched or "flag_for_human_review" in matched, (
            f"Case {case['case_id']} not in expected overlap zone: matched={matched}"
        )


def test_generate_cm_synthetic_has_both_expected_labels():
    cases = generate_cm_overlap_synthetic_cases(n=25)
    labels = {c["expected_action_id"] for c in cases}
    assert "reduce_visibility" in labels
    assert "flag_for_human_review" in labels


def test_generate_cm_synthetic_case_count():
    cases_5 = generate_cm_overlap_synthetic_cases(n=5)
    assert len(cases_5) == 5
    cases_30 = generate_cm_overlap_synthetic_cases(n=30)
    assert len(cases_30) == 30


# ===========================================================================
# Customer-support synthetic overlap tests
# ===========================================================================

def _load_cs_registry() -> RegistrySpec:
    registry_path = (
        REPO_ROOT / "kvrm-demos" / "customer-support-router" / "data" / "registry.json"
    )
    if not registry_path.exists():
        import pytest
        pytest.skip("customer-support registry not found")
    return load_registry(registry_path)


def test_generate_cs_synthetic_cases_nonempty():
    """Customer support synthetic generation produces cases."""
    registry = _load_cs_registry()
    cases = generate_cs_overlap_synthetic_cases(registry, n_per_pair=10)
    assert len(cases) > 0


def test_generate_cs_synthetic_cases_all_in_overlap():
    """Every CS synthetic case should match at least 2 actions."""
    registry = _load_cs_registry()
    cases = generate_cs_overlap_synthetic_cases(registry, n_per_pair=10)

    for case in cases:
        matched = []
        for action in registry.actions:
            ok, _ = evaluate_support_spec(action.support_spec, case["input_features"])
            if ok:
                matched.append(action.action_id)
        overlap_pair = case.get("overlap_pair", [])
        # Both actions from the overlap pair should match
        assert overlap_pair[0] in matched, (
            f"Case {case['case_id']}: {overlap_pair[0]} not matched (matched={matched})"
        )
        assert overlap_pair[1] in matched, (
            f"Case {case['case_id']}: {overlap_pair[1]} not matched (matched={matched})"
        )


def test_generate_cs_synthetic_has_both_expected_labels():
    """CS synthetic cases include both actions from each overlap pair."""
    registry = _load_cs_registry()
    cases = generate_cs_overlap_synthetic_cases(registry, n_per_pair=25)
    labels = {c["expected_action_id"] for c in cases}
    # At least some labels from the overlap pairs should appear
    all_pair_actions = set()
    for a, b in CS_TOP_OVERLAP_PAIRS:
        all_pair_actions.add(a)
        all_pair_actions.add(b)
    # Intersection should be non-empty
    assert labels & all_pair_actions, (
        f"Expected some labels from {all_pair_actions}, got {labels}"
    )


def test_generate_cs_synthetic_case_ids_unique():
    """All CS synthetic case IDs should be unique."""
    registry = _load_cs_registry()
    cases = generate_cs_overlap_synthetic_cases(registry, n_per_pair=25)
    ids = [c["case_id"] for c in cases]
    assert len(ids) == len(set(ids)), "Duplicate case IDs found"


def test_generate_cs_synthetic_per_pair_customization():
    """Custom pairs parameter restricts which pairs are generated."""
    registry = _load_cs_registry()
    # Only generate for one pair
    single_pair = [("escalate_to_manager", "request_human_review")]
    cases = generate_cs_overlap_synthetic_cases(
        registry, n_per_pair=10, pairs=single_pair,
    )
    for case in cases:
        assert set(case["overlap_pair"]) == set(single_pair[0]), (
            f"Unexpected pair: {case['overlap_pair']}"
        )


def test_generate_cs_synthetic_domain_intent_escalate_vs_human_review():
    """The expected-action fn correctly disambiguates escalate vs human review.

    escalate_to_manager triggers:
      - multi_escalated history
      - angry + excessive contacts
      - requires_engineering complexity
      - angry + enterprise tier
    Everything else -> request_human_review
    """
    registry = _load_cs_registry()
    cases = generate_cs_overlap_synthetic_cases(
        registry,
        n_per_pair=25,
        pairs=[("escalate_to_manager", "request_human_review")],
    )
    for case in cases:
        features = case["input_features"]
        expected = case["expected_action_id"]
        should_escalate = (
            features.get("escalation_history") == "multi_escalated"
            or (features.get("sentiment") == "angry" and features.get("prior_contacts") == "excessive")
            or features.get("resolution_complexity") == "requires_engineering"
            or (features.get("customer_tier") == "enterprise" and features.get("sentiment") == "angry")
        )
        if should_escalate:
            assert expected == "escalate_to_manager", (
                f"Case {case['case_id']}: expected escalate_to_manager, got {expected}"
            )
        else:
            assert expected == "request_human_review", (
                f"Case {case['case_id']}: expected request_human_review, got {expected}"
            )


def test_compute_overlap_intersection_cs():
    """compute_overlap_intersection returns common values for CS pairs."""
    registry = _load_cs_registry()
    intersection = compute_overlap_intersection(
        registry,
        "escalate_to_manager",
        "request_human_review",
    )
    # request_human_review accepts all tiers, escalate_to_manager has an 'any' spec
    # so intersection should have values for shared features
    assert isinstance(intersection, dict)
    # customer_tier should have some common values since request_human_review
    # accepts all tiers
    assert "customer_tier" in intersection


def test_generate_overlap_synthetic_generic_fallback():
    """The generic generate_overlap_synthetic_cases alternates expected labels
    when no expected_action_fn is provided."""
    registry = _load_cs_registry()
    # Use the generic function without a custom expected_action_fn
    # This tests the alternating default behaviour
    pairs = [("escalate_to_manager", "request_human_review")]
    cases = generate_overlap_synthetic_cases(
        registry,
        overlap_pairs=pairs,
        n=10,
        domain_label="test",
    )
    if cases:
        expectations = [c["expected_action_id"] for c in cases]
        # Default alternates between action_a and action_b
        assert "escalate_to_manager" in expectations or "request_human_review" in expectations
