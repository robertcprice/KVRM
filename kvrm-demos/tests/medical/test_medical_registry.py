from __future__ import annotations

from pathlib import Path

from kvrm_core.registry import load_registry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "medical-workflow-router" / "data" / "registry.json"


def test_medical_registry_loads_and_has_expected_actions():
    registry = load_registry(REGISTRY_PATH)
    action_ids = {action.action_id for action in registry.actions}
    assert "routine_review" in action_ids
    assert "escalate_supervisor_review" in action_ids
    assert len(action_ids) == 8
    assert "age_bracket" in registry.required_features
    assert registry.context_schema["hypotension"]["type"] == "boolean"
