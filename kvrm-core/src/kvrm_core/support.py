from __future__ import annotations

from typing import Any


LEAF_OPS = {"eq", "neq", "in", "not_in", "gt", "gte", "lt", "lte", "exists", "not_exists"}


def validate_support_spec(spec: dict[str, Any] | None, path: str = "support_spec") -> None:
    """Validate a support spec tree structure, raising ValueError on malformed nodes."""
    if not spec:
        return
    if not isinstance(spec, dict):
        raise ValueError(f"{path} must be an object")

    if "feature" in spec:
        feature = spec.get("feature")
        op = spec.get("op")
        if not isinstance(feature, str) or not feature:
            raise ValueError(f"{path}.feature must be a non-empty string")
        if op not in LEAF_OPS:
            raise ValueError(f"{path}.op must be one of {sorted(LEAF_OPS)}")
        if op in {"in", "not_in"} and not isinstance(spec.get("value"), list):
            raise ValueError(f"{path}.value must be a list for op={op}")
        if op in {"exists", "not_exists"} and "value" in spec:
            raise ValueError(f"{path}.value is not allowed for op={op}")
        return

    for key in ("all", "any"):
        if key in spec:
            children = spec[key]
            if not isinstance(children, list) or not children:
                raise ValueError(f"{path}.{key} must be a non-empty list")
            for idx, child in enumerate(children):
                validate_support_spec(child, f"{path}.{key}[{idx}]")
            return

    if "not" in spec:
        validate_support_spec(spec["not"], f"{path}.not")
        return

    raise ValueError(f"{path} must be a leaf condition or one of all/any/not")


def evaluate_support_spec(spec: dict[str, Any] | None, features: dict[str, Any]) -> tuple[bool, str | None]:
    """Evaluate a support spec against feature values; return (supported, reason_if_not)."""
    if not spec:
        return (True, None)
    return _eval_node(spec, features, path="support_spec")


def support_spec_feature_names(spec: dict[str, Any] | None) -> set[str]:
    names: set[str] = set()
    if not spec:
        return names
    _collect_feature_names(spec, names)
    return names


def support_spec_leaf_count(spec: dict[str, Any] | None) -> int:
    """Count the effective leaf conditions in a support spec (max across any-branches)."""
    if not spec:
        return 0
    return _count_leaf_nodes(spec)


def _eval_node(node: dict[str, Any], features: dict[str, Any], path: str) -> tuple[bool, str | None]:
    if "feature" in node:
        return _eval_leaf(node, features, path)

    if "all" in node:
        for idx, child in enumerate(node["all"]):
            ok, reason = _eval_node(child, features, f"{path}.all[{idx}]")
            if not ok:
                return (False, reason)
        return (True, None)

    if "any" in node:
        first_reason = None
        for idx, child in enumerate(node["any"]):
            ok, reason = _eval_node(child, features, f"{path}.any[{idx}]")
            if ok:
                return (True, None)
            if first_reason is None:
                first_reason = reason
        return (False, first_reason or f"{path}.any")

    if "not" in node:
        ok, _ = _eval_node(node["not"], features, f"{path}.not")
        if ok:
            return (False, f"{path}.not")
        return (True, None)

    return (False, path)


def _eval_leaf(node: dict[str, Any], features: dict[str, Any], path: str) -> tuple[bool, str | None]:
    feature = node["feature"]
    op = node["op"]
    expected = node.get("value")
    value, exists = _lookup_feature(features, feature)

    if op == "exists":
        return _result(exists, path, feature, op)
    if op == "not_exists":
        return _result(not exists, path, feature, op)
    if not exists:
        return (False, f"{path}:{feature}:missing")

    if op == "eq":
        return _result(value == expected, path, feature, op)
    if op == "neq":
        return _result(value != expected, path, feature, op)
    if op == "in":
        return _result(value in expected, path, feature, op)
    if op == "not_in":
        return _result(value not in expected, path, feature, op)
    try:
        if op == "gt":
            return _result(value > expected, path, feature, op)
        if op == "gte":
            return _result(value >= expected, path, feature, op)
        if op == "lt":
            return _result(value < expected, path, feature, op)
        if op == "lte":
            return _result(value <= expected, path, feature, op)
    except TypeError:
        return (False, f"{path}:{feature}:{op}")
    return (False, f"{path}:{feature}:{op}")


def _lookup_feature(features: dict[str, Any], feature: str) -> tuple[Any, bool]:
    current: Any = features
    for part in feature.split("."):
        if not isinstance(current, dict) or part not in current:
            return (None, False)
        current = current[part]
    return (current, True)


def _result(ok: bool, path: str, feature: str, op: str) -> tuple[bool, str | None]:
    if ok:
        return (True, None)
    return (False, f"{path}:{feature}:{op}")


def _collect_feature_names(node: dict[str, Any], names: set[str]) -> None:
    if "feature" in node:
        names.add(node["feature"])
        return
    if "all" in node:
        for child in node["all"]:
            _collect_feature_names(child, names)
        return
    if "any" in node:
        for child in node["any"]:
            _collect_feature_names(child, names)
        return
    if "not" in node:
        _collect_feature_names(node["not"], names)


def _count_leaf_nodes(node: dict[str, Any]) -> int:
    if "feature" in node:
        return 1
    if "all" in node:
        return sum(_count_leaf_nodes(child) for child in node["all"])
    if "any" in node:
        return max(_count_leaf_nodes(child) for child in node["any"])
    if "not" in node:
        return _count_leaf_nodes(node["not"])
    return 0
