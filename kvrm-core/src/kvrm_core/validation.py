from __future__ import annotations

from typing import Callable

from .support import evaluate_support_spec
from .types import DecisionCandidate, RegistrySpec, ValidationResult


class DeterministicValidator:
    """Validate candidates against registry schemas, support specs, and preconditions."""

    def __init__(self, registry: RegistrySpec, preconditions: dict[str, Callable[[dict], bool]] | None = None):
        self.registry = registry
        self.preconditions = preconditions or {}
        self._actions = {action.action_id: action for action in registry.actions}

    def validate(self, candidate: DecisionCandidate, features: dict | None = None) -> ValidationResult:
        """Check that the candidate's action, parameters, support spec, and preconditions are valid."""
        if candidate.action_id not in self._actions:
            return ValidationResult(valid=False, reason="unknown_action")
        action = self._actions[candidate.action_id]
        schema = action.parameters_schema or {}
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        for key in required:
            if key not in candidate.parameters:
                return ValidationResult(valid=False, reason=f"missing_required_parameter:{key}")
        for key in candidate.parameters:
            if properties and key not in properties:
                return ValidationResult(valid=False, reason=f"unexpected_parameter:{key}")
        if features is not None and action.support_spec:
            supported, reason = evaluate_support_spec(action.support_spec, features)
            if not supported:
                return ValidationResult(valid=False, reason=f"unsupported_features:{reason}")
        if candidate.action_id in self.preconditions and not self.preconditions[candidate.action_id](candidate.parameters):
            return ValidationResult(valid=False, reason="precondition_failed")
        return ValidationResult(valid=True, reason=None)
