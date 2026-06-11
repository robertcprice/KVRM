from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .context_schema import validate_context_schema
from .support import validate_support_spec
from .support import support_spec_feature_names
from .types import RegistrySpec


class RegistryValidationError(ValueError):
    pass


def canonical_registry_payload(registry: RegistrySpec) -> dict:
    return {
        "registry_name": registry.registry_name,
        "version": registry.version,
        "required_features": list(registry.required_features),
        "context_schema": registry.context_schema,
        "actions": [action.model_dump() for action in registry.actions],
    }


def compute_registry_digest(registry: RegistrySpec) -> str:
    """Compute a deterministic SHA-256 hex digest of the registry's canonical payload."""
    payload = canonical_registry_payload(registry)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_registry(registry: RegistrySpec) -> None:
    """Validate registry integrity: unique action IDs, context schema, and support specs.

    Raise RegistryValidationError on any structural or referential violation.
    """
    action_ids = [action.action_id for action in registry.actions]
    if len(action_ids) != len(set(action_ids)):
        raise RegistryValidationError("duplicate action_id found in registry")
    if not registry.actions:
        raise RegistryValidationError("registry must contain at least one action")
    try:
        validate_context_schema(registry.context_schema, registry.required_features)
    except ValueError as exc:
        raise RegistryValidationError(str(exc)) from exc
    declared_features = set(registry.context_schema)
    for action in registry.actions:
        try:
            validate_support_spec(action.support_spec, path=f"actions[{action.action_id}].support_spec")
        except ValueError as exc:
            raise RegistryValidationError(str(exc)) from exc
        if declared_features:
            referenced_features = support_spec_feature_names(action.support_spec)
            undeclared = sorted(feature for feature in referenced_features if feature not in declared_features)
            if undeclared:
                raise RegistryValidationError(
                    f"actions[{action.action_id}].support_spec references undeclared features: {', '.join(undeclared)}"
                )


def load_registry(path: str | Path) -> RegistrySpec:
    """Load a registry from a JSON file, validate it, and compute its digest."""
    payload = json.loads(Path(path).read_text())
    registry = RegistrySpec(**payload)
    validate_registry(registry)
    registry.digest = compute_registry_digest(registry)
    return registry
