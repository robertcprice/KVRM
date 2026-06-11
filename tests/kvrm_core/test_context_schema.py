from __future__ import annotations

from kvrm_core.context_schema import build_registry_unsupported_predicate, evaluate_registry_context
from kvrm_core.types import RegistrySpec


def _demo_registry() -> RegistrySpec:
    return RegistrySpec(
        registry_name="demo",
        version="1.0.0",
        required_features=["risk_level", "score", "requires_handoff"],
        context_schema={
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "requires_handoff": {"type": "boolean"},
        },
        actions=[{"action_id": "noop", "name": "Noop", "description": "Noop"}],
    )


def test_evaluate_registry_context_accepts_valid_features():
    supported, reason = evaluate_registry_context(
        _demo_registry(),
        {"risk_level": "medium", "score": 0.7, "requires_handoff": False},
    )
    assert supported is True
    assert reason is None


def test_evaluate_registry_context_rejects_missing_required_feature():
    supported, reason = evaluate_registry_context(
        _demo_registry(),
        {"risk_level": "medium", "score": 0.7},
    )
    assert supported is False
    assert reason == "context:missing:requires_handoff"


def test_evaluate_registry_context_rejects_invalid_enum_and_unknown_feature():
    supported, reason = evaluate_registry_context(
        _demo_registry(),
        {"risk_level": "urgent", "score": 0.7, "requires_handoff": False, "extra": "nope"},
    )
    assert supported is False
    assert reason in {"context:unknown:extra", "context:enum:risk_level"}


def test_registry_unsupported_predicate_composes_extra_rule():
    predicate = build_registry_unsupported_predicate(
        _demo_registry(),
        extra_predicate=lambda features: features["risk_level"] == "high" and features["score"] < 0.2,
    )
    assert predicate({"risk_level": "medium", "score": 0.7, "requires_handoff": False}) is False
    assert predicate({"risk_level": "high", "score": 0.1, "requires_handoff": False}) is True
