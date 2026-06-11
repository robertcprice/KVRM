"""Shared factory for building domain selector suites.

Eliminates ~2,200 lines of copy-paste across 12 domain demo packages.
Each domain provides a DomainConfig dataclass instance; this module
builds all 6 selector constructors plus the executor.
"""
from __future__ import annotations

import json
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .context import feature_key
from .context_schema import load_registry_and_unsupported_predicate
from .execution import DictionaryExecutor
from .learned import CompactLearnedSelector
from .selectors import (
    EvidenceFusionHybridSelector,
    RegistrySemanticSelector,
    RetrievalSelector,
    RuleSelector,
    SupportAwarePrototypeSelector,
)

DomainSelectors = namedtuple(
    "DomainSelectors",
    [
        "build_rule_selector",
        "build_retrieval_selector",
        "build_prototype_selector",
        "build_semantic_selector",
        "build_learned_selector",
        "build_hybrid_selector",
    ],
)


@dataclass(frozen=True)
class DomainConfig:
    name: str

    # Feature schema
    feature_order: list[str]
    categorical_values: dict[str, list[str]]

    # Rules: mapping from feature_key string to (action_id, confidence)
    rules: dict[str, tuple[str, float]]

    # Executor: mapping from action_id to its output value (e.g. "continuous_integration", "auto_approval")
    executor_handlers: dict[str, str]
    # The output key name (e.g. "policy", "workflow", "pipeline", "playbook")
    executor_output_key: str = "policy"
    # Whether to also include {"action": action_id} in executor output
    executor_include_action_key: bool = False
    # Override the "action" value for specific action_ids (e.g. {"escalate_p1": "page_p1"})
    executor_action_overrides: dict[str, str] | None = None
    # Actions that also forward params.get("reason") into output
    reason_actions: set[str] = field(default_factory=set)

    # Fallback / abstain
    fallback_action_id: str = ""

    # Numeric feature handling
    numeric_feature_ranges: dict[str, tuple[float, float]] | None = None
    custom_numeric_keys: dict[str, float] | None = None
    unsupported_penalty: float = 1.25

    # Registry loading
    extra_predicate: Callable[[dict[str, Any]], bool] | None = None
    registry_resolver: Callable[[Path], Path] | None = None

    # Retrieval
    support_aware_retrieval: bool = False

    # Prototype tuning
    prototype_max_distance: float = 5.0
    prototype_raw_distance_floor_ratio: float = 1.0
    prototype_confidence_masked_distance_weight: float | None = None

    # Semantic tuning
    semantic_tags: set[str] | None = None
    semantic_min_leaf_count: int = 5
    semantic_base_confidence: float = 0.80
    semantic_per_leaf_bonus: float = 0.03
    semantic_max_confidence: float = 0.96

    # Learned tuning
    learned_min_confidence: float = 0.42
    learned_candidate_floor: float = 0.20
    learned_top_k: int = 3

    # Drone-specific: default feature values for rule construction
    rule_feature_defaults: dict[str, Any] | None = None

    # Drone-specific: broader tags for hybrid's semantic stage
    hybrid_semantic_tags: set[str] | None = None


def _case_feature_key(payload: dict) -> str:
    return feature_key(payload["input_features"])


def make_feature_distance(config: DomainConfig) -> Callable[[dict[str, Any], dict[str, Any]], float]:
    """Build a feature distance function from domain config."""
    order = config.feature_order
    cat_vals = config.categorical_values
    num_ranges = config.numeric_feature_ranges
    custom_num = config.custom_numeric_keys
    penalty = config.unsupported_penalty

    def _feature_distance(lhs: dict[str, Any], rhs: dict[str, Any]) -> float:
        distance = 0.0
        for key in order:
            left = lhs.get(key)
            right = rhs.get(key)
            if left is None and right is None:
                continue
            # Numeric ranges (SRE pattern)
            if num_ranges and key in num_ranges:
                if left is None or right is None:
                    distance += 1.0
                    continue
                low, high = num_ranges[key]
                span = max(1.0, high - low)
                try:
                    distance += min(penalty, abs(float(left) - float(right)) / span)
                except (TypeError, ValueError):
                    distance += penalty
                continue
            # Custom per-key numeric (CI/CD, insurance, legal pattern)
            if custom_num and key in custom_num:
                divisor = custom_num[key]
                lv = float(left) if left is not None else 0.0
                rv = float(right) if right is not None else 0.0
                distance += abs(lv - rv) / divisor
                continue
            # Bool
            if isinstance(left, bool) or isinstance(right, bool):
                distance += 0.0 if left == right else 1.0
                continue
            # Categorical
            if key in cat_vals:
                values = cat_vals[key]
                if left not in values or right not in values:
                    distance += penalty
                else:
                    span = max(1, len(values) - 1)
                    distance += abs(values.index(left) - values.index(right)) / span
                continue
            # Fallback: equality
            distance += 0.0 if left == right else 1.0
        return distance

    return _feature_distance


def _load_jsonl_cases(path: Path) -> list[dict]:
    cases = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            cases.append(json.loads(line))
    return cases


def _load_registry(config: DomainConfig, cases_path: Path):
    return load_registry_and_unsupported_predicate(
        cases_path,
        registry_resolver=config.registry_resolver,
        extra_predicate=config.extra_predicate,
    )


def build_domain_selectors(config: DomainConfig) -> DomainSelectors:
    """Build all 6 selector constructors for a domain from its config."""
    distance_fn = make_feature_distance(config)
    prefix = config.name

    def build_rule_selector() -> RuleSelector:
        return RuleSelector(rules=config.rules, name=f"{prefix}_rule_selector")

    def build_retrieval_selector(cases_path: str | Path) -> RetrievalSelector:
        cases = _load_jsonl_cases(Path(cases_path))
        support_bank: dict[str, tuple[str, float]] = {}
        for payload in cases:
            expected = payload.get("expected_action_id")
            if expected is None:
                continue
            if config.support_aware_retrieval:
                confidence = 0.96 if payload.get("supported", True) else 0.35
            else:
                confidence = 0.96
            support_bank[_case_feature_key(payload)] = (expected, confidence)
        return RetrievalSelector(support_bank=support_bank, name=f"{prefix}_retrieval_selector")

    def build_prototype_selector(cases_path: str | Path) -> SupportAwarePrototypeSelector:
        cases_path = Path(cases_path)
        cases = _load_jsonl_cases(cases_path)
        prototypes = []
        for payload in cases:
            expected = payload.get("expected_action_id")
            if expected is None:
                continue
            prototypes.append({
                "case_id": payload.get("case_id"),
                "action_id": expected,
                "features": payload["input_features"],
            })
        registry, unsupported_predicate = _load_registry(config, cases_path)
        kwargs: dict[str, Any] = dict(
            registry=registry,
            prototypes=prototypes,
            distance_fn=distance_fn,
            abstain_action_id=config.fallback_action_id,
            max_distance=config.prototype_max_distance,
            unsupported_predicate=unsupported_predicate,
            unsupported_reason="prototype_out_of_support",
            raw_distance_floor_ratio=config.prototype_raw_distance_floor_ratio,
            name=f"{prefix}_prototype_selector",
        )
        if config.prototype_confidence_masked_distance_weight is not None:
            kwargs["confidence_masked_distance_weight"] = config.prototype_confidence_masked_distance_weight
        return SupportAwarePrototypeSelector(**kwargs)

    def build_semantic_selector(
        cases_path: str | Path,
        *,
        required_any_tags: set[str] | None = None,
    ) -> RegistrySemanticSelector:
        cases_path = Path(cases_path)
        registry, unsupported_predicate = _load_registry(config, cases_path)
        tags = required_any_tags or config.semantic_tags or set()
        return RegistrySemanticSelector(
            registry=registry,
            required_any_tags=tags,
            unsupported_predicate=unsupported_predicate,
            min_leaf_count=config.semantic_min_leaf_count,
            base_confidence=config.semantic_base_confidence,
            per_leaf_bonus=config.semantic_per_leaf_bonus,
            max_confidence=config.semantic_max_confidence,
            name=f"{prefix}_semantic_selector",
        )

    def build_learned_selector(
        train_cases_path: str | Path,
        artifact_path: str | Path,
    ) -> CompactLearnedSelector:
        registry, unsupported_predicate = _load_registry(config, Path(train_cases_path))
        return CompactLearnedSelector.from_artifact(
            artifact_path=artifact_path,
            registry=registry,
            unsupported_predicate=unsupported_predicate,
            min_confidence=config.learned_min_confidence,
            candidate_floor=config.learned_candidate_floor,
            top_k=config.learned_top_k,
            name=f"{prefix}_learned_selector",
        )

    def build_hybrid_selector(
        train_cases_path: str | Path,
        learned_model_path: str | Path | None = None,
    ) -> EvidenceFusionHybridSelector:
        registry, unsupported_predicate = _load_registry(config, Path(train_cases_path))
        learned_selector = None
        if learned_model_path is not None and Path(learned_model_path).exists():
            learned_selector = build_learned_selector(train_cases_path, learned_model_path)
        # If hybrid has its own broader semantic tags, use those
        semantic_kwargs: dict[str, Any] = {}
        if config.hybrid_semantic_tags is not None:
            semantic_kwargs["required_any_tags"] = config.hybrid_semantic_tags
        return EvidenceFusionHybridSelector(
            retrieval_selector=build_retrieval_selector(train_cases_path),
            rule_selector=build_rule_selector(),
            prototype_selector=build_prototype_selector(train_cases_path),
            registry=registry,
            semantic_selector=build_semantic_selector(train_cases_path, **semantic_kwargs),
            learned_selector=learned_selector,
            unsupported_predicate=unsupported_predicate,
            fallback_action_id=config.fallback_action_id,
            name=f"{prefix}_hybrid_selector",
        )

    return DomainSelectors(
        build_rule_selector=build_rule_selector,
        build_retrieval_selector=build_retrieval_selector,
        build_prototype_selector=build_prototype_selector,
        build_semantic_selector=build_semantic_selector,
        build_learned_selector=build_learned_selector,
        build_hybrid_selector=build_hybrid_selector,
    )


def build_domain_executor(config: DomainConfig) -> DictionaryExecutor:
    """Build an executor from domain config handler definitions."""
    handlers: dict[str, Callable[[dict], dict]] = {}
    output_key = config.executor_output_key
    include_action = config.executor_include_action_key
    action_overrides = config.executor_action_overrides or {}
    for action_id, output_value in config.executor_handlers.items():
        action_val = action_overrides.get(action_id, action_id)
        if action_id in config.reason_actions:
            if include_action:
                handlers[action_id] = lambda params, ov=output_value, av=action_val: {
                    output_key: ov,
                    "action": av,
                    "reason": params.get("reason"),
                }
            else:
                handlers[action_id] = lambda params, ov=output_value: {
                    output_key: ov,
                    "reason": params.get("reason"),
                }
        else:
            if include_action:
                handlers[action_id] = lambda params, ov=output_value, av=action_val: {
                    output_key: ov,
                    "action": av,
                }
            else:
                handlers[action_id] = lambda params, ov=output_value: {
                    output_key: ov,
                }
    return DictionaryExecutor(handlers=handlers)
