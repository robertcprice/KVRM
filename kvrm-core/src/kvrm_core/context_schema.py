from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .types import RegistrySpec


VALID_CONTEXT_TYPES = {"string", "number", "integer", "boolean"}


def validate_context_schema(
    schema: dict[str, dict[str, Any]] | None,
    required_features: list[str] | None = None,
    path: str = "context_schema",
) -> None:
    """Validate a context schema's types, enums, and numeric bounds; raise ValueError on failure."""
    if schema is None:
        schema = {}
    if not isinstance(schema, dict):
        raise ValueError(f"{path} must be an object")

    for feature_name, spec in schema.items():
        if not isinstance(feature_name, str) or not feature_name:
            raise ValueError(f"{path} keys must be non-empty strings")
        if not isinstance(spec, dict):
            raise ValueError(f"{path}.{feature_name} must be an object")

        field_type = spec.get("type")
        if field_type not in VALID_CONTEXT_TYPES:
            raise ValueError(f"{path}.{feature_name}.type must be one of {sorted(VALID_CONTEXT_TYPES)}")

        enum_values = spec.get("enum")
        if enum_values is not None:
            if not isinstance(enum_values, list) or not enum_values:
                raise ValueError(f"{path}.{feature_name}.enum must be a non-empty list")
            _validate_enum_values(field_type, enum_values, path=f"{path}.{feature_name}.enum")

        minimum = spec.get("minimum")
        maximum = spec.get("maximum")
        if minimum is not None or maximum is not None:
            if field_type not in {"number", "integer"}:
                raise ValueError(f"{path}.{feature_name} numeric bounds require type=number or integer")
            _validate_numeric_bound(field_type, minimum, path=f"{path}.{feature_name}.minimum")
            _validate_numeric_bound(field_type, maximum, path=f"{path}.{feature_name}.maximum")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"{path}.{feature_name}.minimum must be <= maximum")

    required_features = required_features or []
    if not isinstance(required_features, list):
        raise ValueError("required_features must be a list")
    if len(required_features) != len(set(required_features)):
        raise ValueError("required_features must not contain duplicates")
    for feature_name in required_features:
        if not isinstance(feature_name, str) or not feature_name:
            raise ValueError("required_features entries must be non-empty strings")
        if feature_name not in schema:
            raise ValueError(f"required_features contains undeclared feature: {feature_name}")


def validate_context_features(
    schema: dict[str, dict[str, Any]] | None,
    required_features: list[str] | None,
    features: dict[str, Any],
    *,
    reject_unknown_features: bool = True,
    path: str = "context",
) -> tuple[bool, str | None]:
    """Check that features satisfy schema constraints; return (valid, reason_if_not)."""
    if not isinstance(features, dict) or not features:
        return (False, f"{path}:empty")

    schema = schema or {}
    required = required_features or []

    for feature_name in required:
        if feature_name not in features:
            return (False, f"{path}:missing:{feature_name}")

    if reject_unknown_features and schema:
        for feature_name in features:
            if feature_name not in schema:
                return (False, f"{path}:unknown:{feature_name}")

    for feature_name, value in features.items():
        if feature_name not in schema:
            continue
        ok, reason = _validate_feature_value(feature_name, value, schema[feature_name], path=path)
        if not ok:
            return (False, reason)

    return (True, None)


def evaluate_registry_context(
    registry: RegistrySpec,
    features: dict[str, Any],
    *,
    reject_unknown_features: bool = True,
    path: str = "context",
) -> tuple[bool, str | None]:
    """Validate features against a registry's context schema and required features."""
    return validate_context_features(
        registry.context_schema,
        registry.required_features,
        features,
        reject_unknown_features=reject_unknown_features,
        path=path,
    )


def build_registry_unsupported_predicate(
    registry: RegistrySpec,
    *,
    reject_unknown_features: bool = True,
    extra_predicate: Callable[[dict[str, Any]], bool] | None = None,
) -> Callable[[dict[str, Any]], bool]:
    """Build a predicate that returns True when features are unsupported by the registry schema."""
    def predicate(features: dict[str, Any]) -> bool:
        supported, _ = evaluate_registry_context(
            registry,
            features,
            reject_unknown_features=reject_unknown_features,
        )
        if not supported:
            return True
        if extra_predicate is not None and extra_predicate(features):
            return True
        return False

    return predicate


def load_registry_and_unsupported_predicate(
    cases_or_registry_path: str | Path,
    *,
    extra_predicate: Callable[[dict[str, Any]], bool] | None = None,
    registry_path: str | Path | None = None,
    registry_resolver: Callable[[Path], Path] | None = None,
) -> tuple[RegistrySpec, Callable[[dict[str, Any]], bool]]:
    """Load a registry (default: registry.json sibling to the cases file, or the path itself if
    it already points at a registry) and return (registry, unsupported_predicate).

    Optional enhancements for legacy packs:
    - registry_path: explicit path to the registry file (overrides discovery)
    - registry_resolver: callable that takes the cases Path and returns the desired registry Path
      (used by SRE for v4 legacy registry selection)

    This single helper replaces the duplicated 3-line loader + build_registry_unsupported_predicate
    pattern that existed in every domain's selectors.py.
    """
    from .registry import load_registry

    p = Path(cases_or_registry_path)

    if registry_path is not None:
        resolved = Path(registry_path)
    elif registry_resolver is not None:
        resolved = registry_resolver(p)
    elif p.name == "registry.json":
        resolved = p
    else:
        resolved = p.with_name("registry.json")

    registry = load_registry(resolved)
    predicate = build_registry_unsupported_predicate(
        registry, extra_predicate=extra_predicate
    )
    return registry, predicate


def _validate_enum_values(field_type: str, values: list[Any], path: str) -> None:
    for value in values:
        if field_type == "string" and (not isinstance(value, str) or not value):
            raise ValueError(f"{path} must contain only non-empty strings")
        if field_type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"{path} must contain only booleans")
        if field_type == "integer" and not _is_integer(value):
            raise ValueError(f"{path} must contain only integers")
        if field_type == "number" and not _is_number(value):
            raise ValueError(f"{path} must contain only numbers")


def _validate_numeric_bound(field_type: str, value: Any, path: str) -> None:
    if value is None:
        return
    if field_type == "integer" and not _is_integer(value):
        raise ValueError(f"{path} must be an integer")
    if field_type == "number" and not _is_number(value):
        raise ValueError(f"{path} must be a number")


def _validate_feature_value(
    feature_name: str,
    value: Any,
    spec: dict[str, Any],
    *,
    path: str,
) -> tuple[bool, str | None]:
    field_type = spec["type"]
    if field_type == "string" and not isinstance(value, str):
        return (False, f"{path}:type:{feature_name}:string")
    if field_type == "boolean" and not isinstance(value, bool):
        return (False, f"{path}:type:{feature_name}:boolean")
    if field_type == "integer" and not _is_integer(value):
        return (False, f"{path}:type:{feature_name}:integer")
    if field_type == "number" and not _is_number(value):
        return (False, f"{path}:type:{feature_name}:number")

    enum_values = spec.get("enum")
    if enum_values is not None and value not in enum_values:
        return (False, f"{path}:enum:{feature_name}")

    minimum = spec.get("minimum")
    if minimum is not None and value < minimum:
        return (False, f"{path}:minimum:{feature_name}")
    maximum = spec.get("maximum")
    if maximum is not None and value > maximum:
        return (False, f"{path}:maximum:{feature_name}")
    return (True, None)


def _is_integer(value: Any) -> bool:
    return type(value) is int


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
