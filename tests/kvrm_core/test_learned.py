from __future__ import annotations

from pathlib import Path

from kvrm_core.learned import CompactLearnedSelector, save_compact_model_artifact, train_compact_model
from kvrm_core.types import ActionSpec, DecisionInput, RegistrySpec


def _registry() -> RegistrySpec:
    return RegistrySpec(
        registry_name="learned-test",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="safe_action",
                name="Safe Action",
                description="Safe lane.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="risky_action",
                name="Risky Action",
                description="Risky lane.",
                support_spec={"feature": "kind", "op": "eq", "value": "risky"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Human Review",
                description="Fallback.",
                tags=["fallback"],
            ),
        ],
    )


def _train_cases() -> list[dict]:
    return [
        {"case_id": "safe-1", "expected_action_id": "safe_action", "supported": True, "input_features": {"kind": "safe", "rank": 1, "flag": False}},
        {"case_id": "safe-2", "expected_action_id": "safe_action", "supported": True, "input_features": {"kind": "safe", "rank": 2, "flag": False}},
        {"case_id": "risky-1", "expected_action_id": "risky_action", "supported": True, "input_features": {"kind": "risky", "rank": 8, "flag": True}},
        {"case_id": "risky-2", "expected_action_id": "risky_action", "supported": True, "input_features": {"kind": "risky", "rank": 9, "flag": True}},
    ]


def test_compact_learned_selector_trains_and_selects_supported_action(tmp_path: Path):
    registry = _registry()
    artifact = train_compact_model(train_cases=_train_cases(), registry=registry, n_estimators=64)
    artifact_path = tmp_path / "compact_selector.joblib"
    save_compact_model_artifact(artifact_path, artifact)

    selector = CompactLearnedSelector.from_artifact(
        artifact_path=artifact_path,
        registry=registry,
        min_confidence=0.30,
        candidate_floor=0.10,
        top_k=2,
    )
    result = selector.select(DecisionInput(case_id="x", features={"kind": "safe", "rank": 1, "flag": False}))

    assert result
    assert result[0].action_id == "safe_action"
    assert result[0].support_confidence == 1.0
    assert result[0].evidence["model_probability"] >= 0.30


def test_compact_learned_selector_filters_incompatible_actions(tmp_path: Path):
    registry = _registry()
    artifact = train_compact_model(train_cases=_train_cases(), registry=registry, n_estimators=64)
    artifact_path = tmp_path / "compact_selector.joblib"
    save_compact_model_artifact(artifact_path, artifact)

    selector = CompactLearnedSelector.from_artifact(
        artifact_path=artifact_path,
        registry=registry,
        min_confidence=0.0,
        candidate_floor=0.0,
        top_k=3,
    )
    result = selector.select(DecisionInput(case_id="x", features={"kind": "safe", "rank": 9, "flag": True}))

    assert result
    assert all(candidate.action_id == "safe_action" for candidate in result)


def test_compact_learned_selector_abstains_when_global_support_guard_fails(tmp_path: Path):
    registry = _registry()
    artifact = train_compact_model(train_cases=_train_cases(), registry=registry, n_estimators=64)
    artifact_path = tmp_path / "compact_selector.joblib"
    save_compact_model_artifact(artifact_path, artifact)

    selector = CompactLearnedSelector.from_artifact(
        artifact_path=artifact_path,
        registry=registry,
        unsupported_predicate=lambda features: not isinstance(features.get("rank"), int) or not isinstance(features.get("flag"), bool),
        min_confidence=0.0,
        candidate_floor=0.0,
        top_k=3,
    )
    result = selector.select(DecisionInput(case_id="x", features={"kind": "safe", "rank": "bad", "flag": "yes"}))

    assert result == []
