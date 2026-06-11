from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .context import feature_key
from .support import evaluate_support_spec, support_spec_feature_names, support_spec_leaf_count
from .types import DecisionCandidate, DecisionInput, RegistrySpec


@dataclass
class BaseSelector:
    """Abstract base for all selector strategies."""

    name: str = "base"

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        raise NotImplementedError


@dataclass
class RuleSelector(BaseSelector):
    """Select actions by exact feature-key lookup in a static rule table."""

    rules: dict[str, tuple[str, float]] | None = None
    name: str = "rule_selector"

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        key = feature_key(decision_input.features)
        if self.rules and key in self.rules:
            action_id, confidence = self.rules[key]
            return [DecisionCandidate(action_id=action_id, confidence=confidence, source=self.name)]
        return [DecisionCandidate(action_id="collect_more_context", confidence=0.55, source=self.name)]


@dataclass
class RetrievalSelector(BaseSelector):
    """Select actions by retrieving the best match from a pre-built support bank."""

    support_bank: dict[str, tuple[str, float]] | None = None
    name: str = "retrieval_selector"

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        key = feature_key(decision_input.features)
        if self.support_bank and key in self.support_bank:
            action_id, confidence = self.support_bank[key]
            return [DecisionCandidate(action_id=action_id, confidence=confidence, source=self.name)]
        return [DecisionCandidate(action_id="request_human_review", confidence=0.40, source=self.name)]


@dataclass
class ConstantAbstainSelector(BaseSelector):
    """Always emit a low-confidence fallback candidate, forcing abstention."""

    confidence: float = 0.0
    name: str = "constant_abstain_selector"

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        return [DecisionCandidate(action_id="request_human_review", confidence=self.confidence, source=self.name)]


class RegistrySemanticSelector(BaseSelector):
    """Select actions whose support specs match the input features, scoring by leaf count."""

    def __init__(
        self,
        *,
        registry: RegistrySpec,
        prototype_counts: dict[str, int] | None = None,
        max_prototype_count: int | None = None,
        required_any_tags: set[str] | None = None,
        unsupported_predicate: Callable[[dict[str, Any]], bool] | None = None,
        min_leaf_count: int = 1,
        base_confidence: float = 0.70,
        per_leaf_bonus: float = 0.05,
        max_confidence: float = 0.98,
        name: str = "registry_semantic_selector",
    ):
        self.registry = registry
        self.prototype_counts = prototype_counts or {}
        self.max_prototype_count = max_prototype_count
        self.required_any_tags = required_any_tags or set()
        self.unsupported_predicate = unsupported_predicate
        self.min_leaf_count = min_leaf_count
        self.base_confidence = base_confidence
        self.per_leaf_bonus = per_leaf_bonus
        self.max_confidence = max_confidence
        self.name = name
        self._actions = [
            action
            for action in registry.actions
            if action.support_spec
            and support_spec_leaf_count(action.support_spec) >= self.min_leaf_count
            and (
                self.max_prototype_count is None
                or self.prototype_counts.get(action.action_id, 0) <= self.max_prototype_count
            )
            and (
                not self.required_any_tags
                or any(tag in action.tags for tag in self.required_any_tags)
            )
        ]

    def _confidence_for(self, leaf_count: int) -> float:
        return min(self.max_confidence, self.base_confidence + self.per_leaf_bonus * leaf_count)

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        """Return candidates for all registry actions whose support spec is satisfied."""
        if self.unsupported_predicate and self.unsupported_predicate(decision_input.features):
            return []
        candidates: list[DecisionCandidate] = []
        for action in self._actions:
            supported, _ = evaluate_support_spec(action.support_spec, decision_input.features)
            if not supported:
                continue
            leaf_count = support_spec_leaf_count(action.support_spec)
            confidence = self._confidence_for(leaf_count)
            candidates.append(
                DecisionCandidate(
                    action_id=action.action_id,
                    confidence=confidence,
                    action_confidence=confidence,
                    support_confidence=1.0,
                    evidence={"support_leaf_count": leaf_count},
                    source=self.name,
                )
            )
        return candidates


class SupportAwarePrototypeSelector(BaseSelector):
    """Select the nearest prototype whose action's support spec matches, with k-NN agreement."""

    def __init__(
        self,
        *,
        registry: RegistrySpec,
        prototypes: list[dict[str, Any]],
        distance_fn: Callable[[dict[str, Any], dict[str, Any]], float],
        abstain_action_id: str = "request_human_review",
        max_distance: float = 4.0,
        unsupported_predicate: Callable[[dict[str, Any]], bool] | None = None,
        unsupported_confidence: float = 0.35,
        unsupported_reason: str = "prototype_out_of_support",
        agreement_k: int = 3,
        raw_distance_floor_ratio: float = 0.5,
        confidence_masked_distance_weight: float = 0.0,
        name: str = "support_aware_prototype_selector",
    ):
        self.registry = registry
        self.prototypes = prototypes
        self.distance_fn = distance_fn
        self.abstain_action_id = abstain_action_id
        self.max_distance = max_distance
        self.unsupported_predicate = unsupported_predicate
        self.unsupported_confidence = unsupported_confidence
        self.unsupported_reason = unsupported_reason
        self.agreement_k = agreement_k
        self.raw_distance_floor_ratio = raw_distance_floor_ratio
        self.confidence_masked_distance_weight = confidence_masked_distance_weight
        self.name = name
        self._actions = {action.action_id: action for action in registry.actions}
        self._distance_feature_names = {
            action.action_id: {name.split(".", 1)[0] for name in support_spec_feature_names(action.support_spec)}
            for action in registry.actions
        }

    def _action_supported(self, action_id: str, features: dict[str, Any]) -> bool:
        action = self._actions.get(action_id)
        if action is None:
            return False
        supported, _ = evaluate_support_spec(action.support_spec, features)
        return supported

    def _distance_components(
        self,
        action_id: str,
        features: dict[str, Any],
        prototype_features: dict[str, Any],
    ) -> tuple[float, float, float]:
        raw_distance = self.distance_fn(features, prototype_features)
        relevant = self._distance_feature_names.get(action_id) or set()
        if not relevant:
            return (raw_distance, raw_distance, raw_distance)

        masked_features = dict(features)
        masked_prototype = dict(prototype_features)
        for key in set(masked_features) | set(masked_prototype):
            if key in relevant:
                continue
            if key in masked_prototype:
                masked_features[key] = masked_prototype[key]
            elif key in masked_features:
                masked_prototype[key] = masked_features[key]
        masked_distance = self.distance_fn(masked_features, masked_prototype)
        if self.raw_distance_floor_ratio <= 0.0:
            return (masked_distance, raw_distance, masked_distance)
        final_distance = max(masked_distance, raw_distance * self.raw_distance_floor_ratio)
        return (final_distance, raw_distance, masked_distance)

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        """Find the closest support-compatible prototype and return it as a candidate."""
        features = decision_input.features
        if self.unsupported_predicate and self.unsupported_predicate(features):
            return [
                DecisionCandidate(
                    action_id=self.abstain_action_id,
                    confidence=self.unsupported_confidence,
                    support_confidence=0.0,
                    parameters={"reason": self.unsupported_reason},
                    source=self.name,
                )
            ]

        compatible: list[tuple[float, float, float, dict[str, Any]]] = []
        for prototype in self.prototypes:
            if not self._action_supported(prototype["action_id"], features):
                continue
            distance, raw_distance, masked_distance = self._distance_components(
                prototype["action_id"],
                features,
                prototype["features"],
            )
            if distance > self.max_distance:
                continue
            compatible.append((distance, raw_distance, masked_distance, prototype))

        if not compatible:
            return [
                DecisionCandidate(
                    action_id=self.abstain_action_id,
                    confidence=self.unsupported_confidence,
                    support_confidence=0.0,
                    parameters={"reason": self.unsupported_reason},
                    source=self.name,
                )
            ]

        compatible.sort(key=lambda item: item[0])
        best_distance, _, best_masked_distance, best = compatible[0]
        best_action = best["action_id"]
        confidence_distance = best_distance
        if self.confidence_masked_distance_weight > 0.0:
            weight = min(1.0, max(0.0, self.confidence_masked_distance_weight))
            confidence_distance = ((1.0 - weight) * best_distance) + (weight * best_masked_distance)
        confidence = max(0.0, 1.0 - (confidence_distance / self.max_distance))
        neighborhood = compatible[: max(1, self.agreement_k)]
        agreement = sum(1 for _, _, _, proto in neighborhood if proto["action_id"] == best_action) / len(neighborhood)
        next_best_distance = next((distance for distance, _, _, proto in compatible if proto["action_id"] != best_action), None)
        margin = None if next_best_distance is None else max(0.0, next_best_distance - best_distance)

        return [
            DecisionCandidate(
                action_id=best_action,
                confidence=confidence,
                action_confidence=confidence,
                support_confidence=1.0,
                distance=best_distance,
                agreement=agreement,
                margin=margin,
                evidence={
                    "nearest_case_id": best.get("case_id"),
                    "confidence_distance": confidence_distance,
                    "masked_distance": best_masked_distance,
                },
                source=self.name,
            )
        ]


class EvidenceFusionHybridSelector(BaseSelector):
    """Cascade retrieval, rule, semantic, learned, and prototype selectors with support gating."""

    def __init__(
        self,
        *,
        retrieval_selector: BaseSelector,
        rule_selector: BaseSelector,
        prototype_selector: BaseSelector,
        registry: RegistrySpec | None = None,
        semantic_selector: BaseSelector | None = None,
        learned_selector: BaseSelector | None = None,
        unsupported_predicate: Callable[[dict[str, Any]], bool] | None = None,
        retrieval_confidence_threshold: float = 0.95,
        rule_confidence_threshold: float = 0.85,
        fallback_action_id: str = "request_human_review",
        support_gate_fallback_confidence: float = 0.92,
        name: str = "evidence_fusion_hybrid_selector",
    ):
        self.retrieval_selector = retrieval_selector
        self.rule_selector = rule_selector
        self.prototype_selector = prototype_selector
        self.registry = registry
        self.semantic_selector = semantic_selector
        self.learned_selector = learned_selector
        self.unsupported_predicate = unsupported_predicate
        self.retrieval_confidence_threshold = retrieval_confidence_threshold
        self.rule_confidence_threshold = rule_confidence_threshold
        self.fallback_action_id = fallback_action_id
        self.support_gate_fallback_confidence = support_gate_fallback_confidence
        self.name = name
        self._actions = {
            action.action_id: action
            for action in (registry.actions if registry is not None else [])
        }

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        """Fuse candidates from all sub-selectors, gate by support spec, and return survivors."""
        if self.unsupported_predicate and self.unsupported_predicate(decision_input.features):
            return self._emit_support_gate_fallback(reason="unsupported_context")

        candidates: list[DecisionCandidate] = []
        filtered: list[dict[str, Any]] = []

        self._extend_gated_candidates(
            emitted=candidates,
            filtered=filtered,
            stage="retrieval",
            stage_candidates=self.retrieval_selector.select(decision_input),
            features=decision_input.features,
            threshold=self.retrieval_confidence_threshold,
        )
        self._extend_gated_candidates(
            emitted=candidates,
            filtered=filtered,
            stage="rule",
            stage_candidates=self.rule_selector.select(decision_input),
            features=decision_input.features,
            threshold=self.rule_confidence_threshold,
        )

        if self.semantic_selector is not None:
            self._extend_gated_candidates(
                emitted=candidates,
                filtered=filtered,
                stage="semantic",
                stage_candidates=self.semantic_selector.select(decision_input),
                features=decision_input.features,
            )

        if self.learned_selector is not None:
            self._extend_gated_candidates(
                emitted=candidates,
                filtered=filtered,
                stage="learned",
                stage_candidates=self.learned_selector.select(decision_input),
                features=decision_input.features,
            )

        self._extend_gated_candidates(
            emitted=candidates,
            filtered=filtered,
            stage="prototype",
            stage_candidates=self.prototype_selector.select(decision_input),
            features=decision_input.features,
        )

        if candidates:
            if filtered:
                self._annotate_candidates_with_support_gate(candidates, filtered)
            return candidates
        if filtered:
            return self._emit_support_gate_fallback(
                reason="support_gate_exhausted",
                filtered=filtered,
            )

        return [
            DecisionCandidate(
                action_id=self.fallback_action_id,
                confidence=0.0,
                parameters={"reason": "no_candidate"},
                source=self.name,
            )
        ]

    def _extend_gated_candidates(
        self,
        *,
        emitted: list[DecisionCandidate],
        filtered: list[dict[str, Any]],
        stage: str,
        stage_candidates: list[DecisionCandidate],
        features: dict[str, Any],
        threshold: float | None = None,
    ) -> None:
        if not stage_candidates:
            return
        if threshold is not None and stage_candidates[0].confidence < threshold:
            return
        for tagged_candidate in self._tag_candidates(stage_candidates, stage):
            gated_candidate, filtered_entry = self._gate_candidate(tagged_candidate, features)
            if gated_candidate is not None:
                emitted.append(gated_candidate)
            elif filtered_entry is not None:
                filtered.append(filtered_entry)

    def _gate_candidate(
        self,
        candidate: DecisionCandidate,
        features: dict[str, Any],
    ) -> tuple[DecisionCandidate | None, dict[str, Any] | None]:
        if not self._actions:
            return (candidate, None)
        action = self._actions.get(candidate.action_id)
        if action is None:
            return (
                None,
                {
                    "action_id": candidate.action_id,
                    "source": candidate.source,
                    "reason": "unknown_action",
                },
            )

        gated_candidate = candidate.model_copy(deep=True)
        if "fallback" in action.tags:
            if gated_candidate.support_confidence is not None and gated_candidate.support_confidence <= 0.0:
                return (
                    None,
                    {
                        "action_id": candidate.action_id,
                        "source": candidate.source,
                        "reason": "selector_fallback_abstain",
                    },
                )
            if gated_candidate.support_confidence is None:
                gated_candidate.support_confidence = 1.0
            gated_candidate.evidence["support_gate"] = "fallback_action"
            gated_candidate.evidence["is_fallback_action"] = True
            return (gated_candidate, None)

        supported, reason = evaluate_support_spec(action.support_spec, features)
        if not supported:
            return (
                None,
                {
                    "action_id": candidate.action_id,
                    "source": candidate.source,
                    "reason": reason or "unsupported_action",
                },
            )

        if gated_candidate.support_confidence is None:
            gated_candidate.support_confidence = 1.0
        gated_candidate.evidence["support_gate"] = "passed"
        if action.support_spec and gated_candidate.evidence.get("support_leaf_count") is None:
            gated_candidate.evidence["support_leaf_count"] = support_spec_leaf_count(action.support_spec)
        return (gated_candidate, None)

    def _emit_support_gate_fallback(
        self,
        *,
        reason: str,
        filtered: list[dict[str, Any]] | None = None,
    ) -> list[DecisionCandidate]:
        evidence: dict[str, Any] = {"support_gate": reason}
        if filtered:
            evidence["support_gate_filtered_count"] = len(filtered)
            evidence["support_gate_filtered_actions"] = [entry["action_id"] for entry in filtered[:5]]
            evidence["support_gate_filtered_sources"] = [entry["source"] for entry in filtered[:5]]
            evidence["support_gate_filtered_reasons"] = [entry["reason"] for entry in filtered[:5]]
        return [
            DecisionCandidate(
                action_id=self.fallback_action_id,
                confidence=self.support_gate_fallback_confidence,
                support_confidence=1.0,
                parameters={"reason": reason},
                evidence=evidence,
                source=f"{self.name}:support_gate",
            )
        ]

    def _annotate_candidates_with_support_gate(
        self,
        candidates: list[DecisionCandidate],
        filtered: list[dict[str, Any]],
    ) -> None:
        filtered_count = len(filtered)
        filtered_actions = [entry["action_id"] for entry in filtered[:5]]
        filtered_sources = [entry["source"] for entry in filtered[:5]]
        filtered_reasons = [entry["reason"] for entry in filtered[:5]]
        for candidate in candidates:
            candidate.evidence["support_gate_filtered_count"] = filtered_count
            candidate.evidence["support_gate_filtered_actions"] = filtered_actions
            candidate.evidence["support_gate_filtered_sources"] = filtered_sources
            candidate.evidence["support_gate_filtered_reasons"] = filtered_reasons

    def _tag_candidates(self, candidates: list[DecisionCandidate], stage: str) -> list[DecisionCandidate]:
        tagged: list[DecisionCandidate] = []
        for candidate in candidates:
            tagged_candidate = candidate.model_copy(deep=True)
            tagged_candidate.source = f"{self.name}:{stage}"
            tagged.append(tagged_candidate)
        return tagged
