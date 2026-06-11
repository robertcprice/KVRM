from __future__ import annotations

from kvrm_core.selectors import EvidenceFusionHybridSelector, RegistrySemanticSelector, SupportAwarePrototypeSelector
from kvrm_core.types import ActionSpec, DecisionCandidate, DecisionInput, RegistrySpec


def _distance(lhs: dict[str, object], rhs: dict[str, object]) -> float:
    distance = abs(int(lhs["rank"]) - int(rhs["rank"]))
    if lhs.get("noise") != rhs.get("noise"):
        distance += 1.0
    return distance


class StaticSelector:
    def __init__(self, candidates):
        self._candidates = candidates

    def select(self, decision_input: DecisionInput):
        return list(self._candidates)


def test_support_aware_prototype_selector_skips_nearest_incompatible_action():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="safe_action",
                name="Safe Action",
                description="Compatible with safe inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="risky_action",
                name="Risky Action",
                description="Compatible with risky inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "risky"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Request Human Review",
                description="Fallback action.",
                tags=["fallback", "safe"],
            ),
        ],
    )
    selector = SupportAwarePrototypeSelector(
        registry=registry,
        prototypes=[
            {"case_id": "near-risky", "action_id": "risky_action", "features": {"kind": "risky", "rank": 0, "noise": 0}},
            {"case_id": "mid-safe", "action_id": "safe_action", "features": {"kind": "safe", "rank": 1, "noise": 0}},
            {"case_id": "far-safe", "action_id": "safe_action", "features": {"kind": "safe", "rank": 2, "noise": 0}},
        ],
        distance_fn=_distance,
        abstain_action_id="request_human_review",
        max_distance=3.0,
        agreement_k=2,
    )

    result = selector.select(DecisionInput(case_id="x", features={"kind": "safe", "rank": 0, "noise": 999}))

    assert len(result) == 1
    assert result[0].action_id == "safe_action"
    assert result[0].distance == 1.0
    assert result[0].agreement == 1.0
    assert result[0].evidence["nearest_case_id"] == "mid-safe"
    assert result[0].evidence["confidence_distance"] == 1.0
    assert result[0].evidence["masked_distance"] == 0.0


def test_support_aware_prototype_selector_abstains_when_no_compatible_action_exists():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="safe_action",
                name="Safe Action",
                description="Compatible with safe inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Request Human Review",
                description="Fallback action.",
                tags=["fallback", "safe"],
            ),
        ],
    )
    selector = SupportAwarePrototypeSelector(
        registry=registry,
        prototypes=[{"case_id": "safe-1", "action_id": "safe_action", "features": {"kind": "safe", "rank": 1}}],
        distance_fn=_distance,
        abstain_action_id="request_human_review",
        max_distance=3.0,
    )

    result = selector.select(DecisionInput(case_id="x", features={"kind": "unknown", "rank": 1}))

    assert len(result) == 1
    assert result[0].action_id == "request_human_review"
    assert result[0].support_confidence == 0.0
    assert result[0].parameters["reason"] == "prototype_out_of_support"


def test_support_aware_prototype_selector_can_calibrate_confidence_from_masked_distance():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="safe_action",
                name="Safe Action",
                description="Compatible with safe inputs.",
                support_spec={
                    "all": [
                        {"feature": "kind", "op": "eq", "value": "safe"},
                        {"feature": "rank", "op": "eq", "value": 1},
                    ]
                },
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Request Human Review",
                description="Fallback action.",
                tags=["fallback", "safe"],
            ),
        ],
    )
    selector = SupportAwarePrototypeSelector(
        registry=registry,
        prototypes=[{"case_id": "safe-1", "action_id": "safe_action", "features": {"kind": "safe", "rank": 1, "noise": 0}}],
        distance_fn=_distance,
        abstain_action_id="request_human_review",
        max_distance=3.0,
        raw_distance_floor_ratio=1.0,
        confidence_masked_distance_weight=0.75,
    )

    result = selector.select(DecisionInput(case_id="x", features={"kind": "safe", "rank": 1, "noise": 1}))

    assert len(result) == 1
    assert result[0].action_id == "safe_action"
    assert result[0].distance == 1.0
    assert result[0].evidence["masked_distance"] == 0.0
    assert result[0].evidence["confidence_distance"] == 0.25
    assert result[0].confidence == 0.9166666666666666


def test_registry_semantic_selector_emits_high_specificity_noop_candidate():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="do_nothing_validated",
                name="Do Nothing",
                description="Benign noop.",
                support_spec={
                    "all": [
                        {"feature": "severity", "op": "eq", "value": "informational"},
                        {"feature": "blast_radius", "op": "eq", "value": "none"},
                        {"feature": "lateral_movement", "op": "eq", "value": False},
                    ]
                },
                tags=["noop", "safe"],
            ),
            ActionSpec(
                action_id="monitor_only",
                name="Monitor Only",
                description="Broad observation action.",
                support_spec={"feature": "severity", "op": "eq", "value": "informational"},
                tags=["monitoring"],
            ),
        ],
    )
    selector = RegistrySemanticSelector(
        registry=registry,
        required_any_tags={"noop"},
        min_leaf_count=2,
        base_confidence=0.80,
        per_leaf_bonus=0.04,
    )

    result = selector.select(
        DecisionInput(
            case_id="x",
            features={"severity": "informational", "blast_radius": "none", "lateral_movement": False},
        )
    )

    assert len(result) == 1
    assert result[0].action_id == "do_nothing_validated"
    assert result[0].confidence == 0.92
    assert result[0].evidence["support_leaf_count"] == 3


def test_registry_semantic_selector_can_filter_to_uncovered_actions():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="covered_action",
                name="Covered Action",
                description="Has examples already.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
                tags=["fallback"],
            ),
            ActionSpec(
                action_id="uncovered_action",
                name="Uncovered Action",
                description="Needs semantic coverage.",
                support_spec={
                    "all": [
                        {"feature": "kind", "op": "eq", "value": "safe"},
                        {"feature": "mode", "op": "eq", "value": "manual"},
                    ]
                },
                tags=["fallback"],
            ),
        ],
    )
    selector = RegistrySemanticSelector(
        registry=registry,
        prototype_counts={"covered_action": 2, "uncovered_action": 0},
        max_prototype_count=0,
        required_any_tags={"fallback"},
        min_leaf_count=2,
        base_confidence=0.80,
        per_leaf_bonus=0.05,
    )

    result = selector.select(
        DecisionInput(
            case_id="x",
            features={"kind": "safe", "mode": "manual"},
        )
    )

    assert len(result) == 1
    assert result[0].action_id == "uncovered_action"


def test_evidence_fusion_hybrid_selector_collects_all_high_value_sources():
    selector = EvidenceFusionHybridSelector(
        retrieval_selector=StaticSelector([DecisionCandidate(action_id="a", confidence=0.96, source="retrieval")]),
        rule_selector=StaticSelector([DecisionCandidate(action_id="a", confidence=0.90, source="rule")]),
        semantic_selector=StaticSelector([DecisionCandidate(action_id="b", confidence=0.81, source="semantic")]),
        learned_selector=StaticSelector([DecisionCandidate(action_id="a", confidence=0.66, source="learned")]),
        prototype_selector=StaticSelector([DecisionCandidate(action_id="a", confidence=0.72, source="prototype")]),
        fallback_action_id="request_human_review",
        name="fusion_test_selector",
    )

    result = selector.select(DecisionInput(case_id="x", features={"kind": "safe"}))

    assert [candidate.action_id for candidate in result] == ["a", "a", "b", "a", "a"]
    assert [candidate.source for candidate in result] == [
        "fusion_test_selector:retrieval",
        "fusion_test_selector:rule",
        "fusion_test_selector:semantic",
        "fusion_test_selector:learned",
        "fusion_test_selector:prototype",
    ]


def test_evidence_fusion_hybrid_selector_filters_support_incompatible_candidates_before_fusion():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="safe_action",
                name="Safe Action",
                description="Compatible with safe inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="risky_action",
                name="Risky Action",
                description="Compatible with risky inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "risky"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Request Human Review",
                description="Fallback action.",
                tags=["fallback", "safe"],
            ),
        ],
    )
    selector = EvidenceFusionHybridSelector(
        retrieval_selector=StaticSelector([DecisionCandidate(action_id="risky_action", confidence=0.96, source="retrieval")]),
        rule_selector=StaticSelector([]),
        semantic_selector=StaticSelector([DecisionCandidate(action_id="safe_action", confidence=0.81, source="semantic")]),
        prototype_selector=StaticSelector([DecisionCandidate(action_id="safe_action", confidence=0.72, source="prototype")]),
        registry=registry,
        fallback_action_id="request_human_review",
        name="fusion_test_selector",
    )

    result = selector.select(DecisionInput(case_id="x", features={"kind": "safe"}))

    assert [candidate.action_id for candidate in result] == ["safe_action", "safe_action"]
    assert [candidate.source for candidate in result] == [
        "fusion_test_selector:semantic",
        "fusion_test_selector:prototype",
    ]
    assert all(candidate.support_confidence == 1.0 for candidate in result)
    assert all(candidate.evidence["support_gate"] == "passed" for candidate in result)


def test_evidence_fusion_hybrid_selector_marks_fallback_actions_for_conservative_fusion():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="allow_action",
                name="Allow Action",
                description="Compatible with safe inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Request Human Review",
                description="Fallback action.",
                tags=["fallback", "safe"],
            ),
        ],
    )
    selector = EvidenceFusionHybridSelector(
        retrieval_selector=StaticSelector([]),
        rule_selector=StaticSelector([]),
        semantic_selector=StaticSelector([DecisionCandidate(action_id="request_human_review", confidence=0.88, source="semantic")]),
        prototype_selector=StaticSelector([DecisionCandidate(action_id="allow_action", confidence=0.81, source="prototype")]),
        registry=registry,
        fallback_action_id="request_human_review",
        name="fusion_test_selector",
    )

    result = selector.select(DecisionInput(case_id="x", features={"kind": "safe"}))
    fallback_candidate = next(candidate for candidate in result if candidate.action_id == "request_human_review")

    assert fallback_candidate.evidence["support_gate"] == "fallback_action"
    assert fallback_candidate.evidence["is_fallback_action"] is True


def test_evidence_fusion_hybrid_selector_filters_selector_local_fallback_abstain():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="allow_action",
                name="Allow Action",
                description="Compatible with safe inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Request Human Review",
                description="Fallback action.",
                tags=["fallback", "safe"],
            ),
        ],
    )
    selector = EvidenceFusionHybridSelector(
        retrieval_selector=StaticSelector([]),
        rule_selector=StaticSelector([]),
        semantic_selector=StaticSelector([DecisionCandidate(action_id="allow_action", confidence=0.88, source="semantic")]),
        prototype_selector=StaticSelector(
            [
                DecisionCandidate(
                    action_id="request_human_review",
                    confidence=0.35,
                    source="prototype",
                    support_confidence=0.0,
                    parameters={"reason": "prototype_out_of_support"},
                )
            ]
        ),
        registry=registry,
        fallback_action_id="request_human_review",
        name="fusion_test_selector",
    )

    result = selector.select(DecisionInput(case_id="x", features={"kind": "safe"}))

    assert [candidate.action_id for candidate in result] == ["allow_action"]
    assert result[0].evidence["support_gate_filtered_count"] == 1
    assert result[0].evidence["support_gate_filtered_reasons"] == ["selector_fallback_abstain"]


def test_evidence_fusion_hybrid_selector_short_circuits_globally_unsupported_context():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="safe_action",
                name="Safe Action",
                description="Compatible with safe inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Request Human Review",
                description="Fallback action.",
                tags=["fallback", "safe"],
            ),
        ],
    )
    selector = EvidenceFusionHybridSelector(
        retrieval_selector=StaticSelector([DecisionCandidate(action_id="safe_action", confidence=0.96, source="retrieval")]),
        rule_selector=StaticSelector([]),
        semantic_selector=StaticSelector([]),
        prototype_selector=StaticSelector([]),
        registry=registry,
        unsupported_predicate=lambda features: features.get("kind") == "unknown",
        fallback_action_id="request_human_review",
        name="fusion_test_selector",
    )

    result = selector.select(DecisionInput(case_id="x", features={"kind": "unknown"}))

    assert len(result) == 1
    assert result[0].action_id == "request_human_review"
    assert result[0].source == "fusion_test_selector:support_gate"
    assert result[0].parameters["reason"] == "unsupported_context"
    assert result[0].support_confidence == 1.0
    assert result[0].evidence["support_gate"] == "unsupported_context"
