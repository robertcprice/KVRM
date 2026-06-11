from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np

from .registry import compute_registry_digest
from .selectors import BaseSelector
from .support import evaluate_support_spec, support_spec_leaf_count
from .types import DecisionCandidate, DecisionInput, RegistrySpec

NUMERIC_SCHEMA = "numeric"
BOOLEAN_SCHEMA = "boolean"


def infer_feature_schema(cases: list[dict[str, Any]]) -> tuple[dict[str, str | list[str]], list[str]]:
    """Infer a feature schema (numeric, boolean, or categorical) from training cases."""
    values_by_feature: dict[str, list[Any]] = {}
    for case in cases:
        for key, value in case.get("input_features", {}).items():
            values_by_feature.setdefault(key, []).append(value)

    feature_order = sorted(values_by_feature)
    schema: dict[str, str | list[str]] = {}
    for feature_name in feature_order:
        values = [value for value in values_by_feature[feature_name] if value is not None]
        if values and all(isinstance(value, bool) for value in values):
            schema[feature_name] = BOOLEAN_SCHEMA
            continue
        if values and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            schema[feature_name] = NUMERIC_SCHEMA
            continue
        categorical_values = sorted({str(value) for value in values})
        schema[feature_name] = categorical_values
    return (schema, feature_order)


def encode_features(
    features: dict[str, Any],
    schema: dict[str, str | list[str]],
    feature_order: list[str],
) -> np.ndarray:
    """Encode a feature dict into a flat numeric vector using the given schema."""
    parts: list[float] = []
    for feature_name in feature_order:
        spec = schema[feature_name]
        value = features.get(feature_name)
        if spec == NUMERIC_SCHEMA:
            try:
                parts.append(float(value))
            except (TypeError, ValueError):
                parts.append(0.0)
            continue
        if spec == BOOLEAN_SCHEMA:
            if value is True:
                parts.append(1.0)
            elif value is False:
                parts.append(0.0)
            else:
                parts.append(-1.0)
            continue
        one_hot = [0.0] * (len(spec) + 1)
        text_value = str(value) if value is not None else None
        if text_value in spec:
            one_hot[spec.index(text_value)] = 1.0
        else:
            one_hot[-1] = 1.0
        parts.extend(one_hot)
    return np.array(parts, dtype=np.float64)


def encode_batch(
    cases: list[dict[str, Any]],
    schema: dict[str, str | list[str]],
    feature_order: list[str],
) -> np.ndarray:
    """Encode a list of case dicts into a 2-D feature matrix."""
    return np.array(
        [encode_features(case["input_features"], schema, feature_order) for case in cases],
        dtype=np.float64,
    )


def train_compact_model(
    *,
    train_cases: list[dict[str, Any]],
    registry: RegistrySpec,
    random_state: int = 42,
    n_estimators: int = 256,
) -> dict[str, Any]:
    """Train a RandomForest classifier on labeled cases and return a serializable artifact."""
    from sklearn.ensemble import RandomForestClassifier

    supported_rows = [
        case
        for case in train_cases
        if case.get("expected_action_id") is not None and case.get("supported", True)
    ]
    if len(supported_rows) < 2:
        raise ValueError("need at least two supported training rows with expected_action_id")

    schema, feature_order = infer_feature_schema(supported_rows)
    registry_order = [action.action_id for action in registry.actions]
    observed_labels = {case["expected_action_id"] for case in supported_rows}
    label_list = [action_id for action_id in registry_order if action_id in observed_labels]

    matrix = encode_batch(supported_rows, schema, feature_order)
    labels = np.array([case["expected_action_id"] for case in supported_rows], dtype=object)

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        class_weight="balanced_subsample",
        min_samples_leaf=1,
    )
    model.fit(matrix, labels)

    train_accuracy = float((model.predict(matrix) == labels).mean())
    return {
        "artifact_version": "1.0",
        "model_type": "random_forest",
        "model": model,
        "feature_schema": schema,
        "feature_order": feature_order,
        "label_list": label_list,
        "metadata": {
            "train_case_count": len(supported_rows),
            "registry_name": registry.registry_name,
            "registry_digest": compute_registry_digest(registry),
            "random_state": random_state,
            "n_estimators": n_estimators,
            "train_accuracy": train_accuracy,
        },
    }


def save_compact_model_artifact(path: str | Path, artifact: dict[str, Any]) -> None:
    """Persist a trained model artifact to disk via joblib."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, path)


def load_compact_model_artifact(path: str | Path) -> dict[str, Any]:
    """Load a previously saved model artifact from disk."""
    return joblib.load(Path(path))


@dataclass
class CompactLearnedSelector(BaseSelector):
    """Select actions using a trained RandomForest model, gated by support spec compatibility."""

    registry: RegistrySpec | None = None
    model: Any | None = None
    feature_schema: dict[str, str | list[str]] | None = None
    feature_order: list[str] | None = None
    unsupported_predicate: Callable[[dict[str, Any]], bool] | None = None
    min_confidence: float = 0.45
    candidate_floor: float = 0.20
    top_k: int = 3
    only_supported_actions: bool = True
    name: str = "compact_learned_selector"

    def __post_init__(self) -> None:
        self._actions = {
            action.action_id: action
            for action in (self.registry.actions if self.registry is not None else [])
        }

    @classmethod
    def from_artifact(
        cls,
        *,
        artifact_path: str | Path,
        registry: RegistrySpec,
        unsupported_predicate: Callable[[dict[str, Any]], bool] | None = None,
        min_confidence: float = 0.45,
        candidate_floor: float = 0.20,
        top_k: int = 3,
        only_supported_actions: bool = True,
        name: str = "compact_learned_selector",
    ) -> "CompactLearnedSelector":
        artifact = load_compact_model_artifact(artifact_path)
        return cls(
            registry=registry,
            model=artifact["model"],
            feature_schema=artifact["feature_schema"],
            feature_order=artifact["feature_order"],
            unsupported_predicate=unsupported_predicate,
            min_confidence=min_confidence,
            candidate_floor=candidate_floor,
            top_k=top_k,
            only_supported_actions=only_supported_actions,
            name=name,
        )

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        """Predict action probabilities with the model and return top-k supported candidates."""
        if self.model is None or self.feature_schema is None or self.feature_order is None:
            return []
        if self.unsupported_predicate and self.unsupported_predicate(decision_input.features):
            return []

        vector = encode_features(
            decision_input.features,
            self.feature_schema,
            self.feature_order,
        ).reshape(1, -1)
        probabilities = self.model.predict_proba(vector)[0]
        ranked = sorted(
            zip(self.model.classes_, probabilities),
            key=lambda item: float(item[1]),
            reverse=True,
        )

        compatible: list[tuple[str, float]] = []
        for action_id, probability in ranked:
            probability = float(probability)
            if probability < self.candidate_floor:
                continue
            action = self._actions.get(str(action_id))
            if action is None:
                continue
            supported, _ = evaluate_support_spec(action.support_spec, decision_input.features)
            if self.only_supported_actions and not supported:
                continue
            compatible.append((action.action_id, probability))

        if not compatible or compatible[0][1] < self.min_confidence:
            return []

        selected = compatible[: max(1, self.top_k)]
        emitted: list[DecisionCandidate] = []
        for index, (action_id, probability) in enumerate(selected):
            next_probability = selected[index + 1][1] if index + 1 < len(selected) else 0.0
            action = self._actions[action_id]
            emitted.append(
                DecisionCandidate(
                    action_id=action_id,
                    confidence=probability,
                    action_confidence=probability,
                    support_confidence=1.0,
                    margin=max(0.0, probability - next_probability),
                    evidence={
                        "model_probability": probability,
                        "support_leaf_count": support_spec_leaf_count(action.support_spec),
                        "compatible_rank": index + 1,
                        "compatible_action_count": len(compatible),
                    },
                    source=self.name,
                )
            )
        return emitted
