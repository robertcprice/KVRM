from __future__ import annotations

from pathlib import Path

from kvrm_core.execution import DictionaryExecutor
from kvrm_core.registry import load_registry
from kvrm_core.types import ActionSpec, DecisionCandidate, ExecutionStatus, RegistrySpec
from kvrm_core.validation import DeterministicValidator

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "kvrm-core" / "examples" / "toy_registry.json"


def test_unsupported_action_is_rejected():
    registry = load_registry(REGISTRY_PATH)
    validator = DeterministicValidator(registry)
    result = validator.validate(DecisionCandidate(action_id="not_real", confidence=1.0))
    assert result.valid is False


def test_missing_required_parameter_is_rejected():
    registry = load_registry(REGISTRY_PATH)
    validator = DeterministicValidator(registry)
    result = validator.validate(DecisionCandidate(action_id="request_human_review", confidence=1.0, parameters={}))
    assert result.valid is False


def test_support_spec_rejects_semantically_unsupported_action():
    registry = load_registry(REGISTRY_PATH)
    validator = DeterministicValidator(registry)
    result = validator.validate(
        DecisionCandidate(action_id="allow_low_risk", confidence=1.0),
        features={"risk": "high", "anomaly": 0.95},
    )
    assert result.valid is False
    assert result.reason and result.reason.startswith("unsupported_features:")


def test_valid_action_executes_through_deterministic_executor():
    executor = DictionaryExecutor(handlers={"allow_low_risk": lambda params: {"ok": True}})
    result = executor.execute(DecisionCandidate(action_id="allow_low_risk", confidence=1.0))
    assert result.status == ExecutionStatus.SUCCESS


def test_runtime_fallback_action_with_support_spec_is_still_validated():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="safe_action",
                name="Safe Action",
                description="Compatible action.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Request Human Review",
                description="Fallback action with feasibility constraints.",
                parameters_schema={"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
                support_spec={"feature": "handoff_ready", "op": "eq", "value": True},
                tags=["fallback", "safe"],
            ),
        ],
    )
    validator = DeterministicValidator(registry)
    result = validator.validate(
        DecisionCandidate(
            action_id="request_human_review",
            confidence=1.0,
            parameters={"reason": "manual_review"},
            source="fallback",
        ),
        features={"kind": "unknown", "handoff_ready": False},
    )
    assert result.valid is False
    assert result.reason == "unsupported_features:support_spec:handoff_ready:eq"
