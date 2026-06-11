"""Live domain schemas derived from the canonical KVRM registries."""
from __future__ import annotations

from typing import Any

from .data_loader import DEMO_PATHS, DOMAIN_ORDER, load_registry


def _build_feature_schema(
    context_schema: dict[str, dict[str, Any]],
    feature_order: list[str],
) -> dict[str, str | list[object]]:
    feature_schema: dict[str, str | list[object]] = {}
    for feature_name in feature_order:
        spec = context_schema[feature_name]
        value_type = spec.get("type")
        if value_type in {"number", "integer"}:
            feature_schema[feature_name] = "numeric"
        elif value_type == "boolean":
            feature_schema[feature_name] = [False, True]
        elif value_type == "string" and "enum" in spec:
            feature_schema[feature_name] = list(spec["enum"])
        else:
            raise ValueError(
                f"Unsupported schema for feature {feature_name}: {spec!r}"
            )
    return feature_schema


def _extract_fallback_action(registry: dict[str, Any]) -> str | None:
    fallback_actions = [
        action["action_id"]
        for action in registry["actions"]
        if "fallback" in action.get("tags", [])
    ]
    if not fallback_actions:
        return None
    # Return the first fallback action; domains with multiple fallback-tagged
    # actions use the first as the primary handoff target.
    return fallback_actions[0]


def _build_domain_config(domain: str) -> dict[str, Any]:
    registry = load_registry(DEMO_PATHS[domain]["registry"])
    feature_order = list(registry["required_features"])
    labels = [action["action_id"] for action in registry["actions"]]
    descriptions = {
        action["action_id"]: action.get("description", "").strip()
        for action in registry["actions"]
    }
    return {
        "registry_name": registry["registry_name"],
        "registry_version": registry["version"],
        "feature_order": feature_order,
        "feature_schema": _build_feature_schema(registry["context_schema"], feature_order),
        "context_schema": registry["context_schema"],
        "labels": labels,
        "label_descriptions": descriptions,
        "fallback": _extract_fallback_action(registry),
    }


DOMAINS = {domain: _build_domain_config(domain) for domain in DOMAIN_ORDER}

