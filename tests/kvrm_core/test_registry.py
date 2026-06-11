from __future__ import annotations

import json

import pytest

from kvrm_core import load_registry
from kvrm_core.registry import RegistryValidationError, compute_registry_digest, validate_registry
from kvrm_core.types import RegistrySpec


def test_kvrm_core_imports_cleanly():
    import kvrm_core
    assert kvrm_core is not None


def test_registry_loads_from_json(tmp_path):
    payload = {
        "registry_name": "demo",
        "version": "1.0.0",
        "actions": [{"action_id": "a", "name": "A", "description": "A", "parameters_schema": {"type": "object", "properties": {}, "required": []}}],
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload))
    registry = load_registry(path)
    assert registry.registry_name == "demo"
    assert registry.digest


def test_registry_rejects_duplicate_action_ids():
    registry = RegistrySpec(
        registry_name="demo",
        version="1.0.0",
        actions=[
            {"action_id": "dup", "name": "A", "description": "A"},
            {"action_id": "dup", "name": "B", "description": "B"},
        ],
    )
    with pytest.raises(RegistryValidationError):
        validate_registry(registry)


def test_registry_digest_is_stable(tmp_path):
    payload = {
        "registry_name": "demo",
        "version": "1.0.0",
        "actions": [{"action_id": "a", "name": "A", "description": "A"}],
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload))
    one = load_registry(path)
    two = load_registry(path)
    assert compute_registry_digest(one) == compute_registry_digest(two)


def test_registry_rejects_invalid_support_spec():
    registry = RegistrySpec(
        registry_name="demo",
        version="1.0.0",
        actions=[
            {
                "action_id": "a",
                "name": "A",
                "description": "A",
                "support_spec": {"feature": "risk", "op": "between", "value": [0, 1]},
            }
        ],
    )
    with pytest.raises(RegistryValidationError):
        validate_registry(registry)


def test_registry_rejects_required_feature_missing_from_context_schema():
    registry = RegistrySpec(
        registry_name="demo",
        version="1.0.0",
        required_features=["risk_level"],
        context_schema={},
        actions=[{"action_id": "a", "name": "A", "description": "A"}],
    )
    with pytest.raises(RegistryValidationError):
        validate_registry(registry)


def test_registry_rejects_support_spec_with_undeclared_feature():
    registry = RegistrySpec(
        registry_name="demo",
        version="1.0.0",
        required_features=["risk_level"],
        context_schema={"risk_level": {"type": "string", "enum": ["low", "high"]}},
        actions=[
            {
                "action_id": "a",
                "name": "A",
                "description": "A",
                "support_spec": {"feature": "urgency", "op": "eq", "value": "high"},
            }
        ],
    )
    with pytest.raises(RegistryValidationError):
        validate_registry(registry)


def test_registry_rejects_zero_actions():
    registry = RegistrySpec(
        registry_name="empty",
        version="1.0.0",
        required_features=["x"],
        context_schema={"x": {"type": "string"}},
        actions=[],
    )
    with pytest.raises(RegistryValidationError):
        validate_registry(registry)
