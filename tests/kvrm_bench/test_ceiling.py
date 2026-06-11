from __future__ import annotations

from kvrm_bench.ceiling import exact_conflict_groups, exact_feature_oracle_accuracy, support_overlap_cases, top_overlap_pairs
from kvrm_core.types import ActionSpec, RegistrySpec


def _registry() -> RegistrySpec:
    return RegistrySpec(
        registry_name="toy",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="action_a",
                name="Action A",
                description="A",
                support_spec={"feature": "kind", "op": "eq", "value": "shared"},
            ),
            ActionSpec(
                action_id="action_b",
                name="Action B",
                description="B",
                support_spec={"feature": "severity", "op": "eq", "value": "high"},
            ),
            ActionSpec(
                action_id="action_c",
                name="Action C",
                description="C",
                support_spec={"feature": "kind", "op": "eq", "value": "other"},
            ),
        ],
    )


def test_exact_feature_oracle_accuracy_reflects_conflicting_duplicate_labels():
    cases = [
        {"case_id": "c1", "input_features": {"kind": "shared", "severity": "low"}, "expected_action_id": "action_a", "supported": True},
        {"case_id": "c2", "input_features": {"kind": "shared", "severity": "low"}, "expected_action_id": "action_b", "supported": True},
        {"case_id": "c3", "input_features": {"kind": "other", "severity": "high"}, "expected_action_id": "action_c", "supported": True},
    ]

    assert exact_feature_oracle_accuracy(cases) == 2 / 3


def test_exact_conflict_groups_reports_duplicate_feature_collisions():
    cases = [
        {"case_id": "c1", "input_features": {"kind": "shared"}, "expected_action_id": "action_a", "supported": True},
        {"case_id": "c2", "input_features": {"kind": "shared"}, "expected_action_id": "action_b", "supported": True},
        {"case_id": "c3", "input_features": {"kind": "other"}, "expected_action_id": "action_c", "supported": True},
    ]

    groups = exact_conflict_groups(cases)

    assert len(groups) == 1
    assert groups[0]["size"] == 2
    assert groups[0]["label_counts"] == {"action_a": 1, "action_b": 1}


def test_support_overlap_cases_and_pair_counts_capture_registry_ambiguity():
    cases = [
        {"case_id": "c1", "input_features": {"kind": "shared", "severity": "high"}, "expected_action_id": "action_a", "supported": True},
        {"case_id": "c2", "input_features": {"kind": "other", "severity": "low"}, "expected_action_id": "action_c", "supported": True},
    ]

    overlap_rows = support_overlap_cases(_registry(), cases)
    pair_rows = top_overlap_pairs(overlap_rows)

    assert len(overlap_rows) == 1
    assert overlap_rows[0]["matched_actions"] == ["action_a", "action_b"]
    assert pair_rows == [{"pair": ["action_a", "action_b"], "count": 1}]
