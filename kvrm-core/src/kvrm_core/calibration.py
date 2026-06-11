from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean
from typing import Protocol, Sequence

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from .types import DecisionCandidate


# ---------------------------------------------------------------------------
# Post-hoc recalibration scalers
# ---------------------------------------------------------------------------


class PostHocScaler(Protocol):
    """Interface for post-hoc confidence recalibration."""

    def fit(self, confidences: Sequence[float], labels: Sequence[int]) -> "PostHocScaler": ...
    def transform(self, confidence: float) -> float: ...


@dataclass
class TemperatureScaler:
    """Temperature scaling: divide logits by learned temperature T before softmax.

    For a single-output confidence c, we map to logit space via log(c / (1-c)),
    divide by T, then convert back via sigmoid.  T > 1 reduces overconfidence,
    T < 1 increases it.

    Fitting minimizes the negative log-likelihood (NLL) on the held-out set.
    """

    temperature: float = 1.0
    _fitted: bool = field(default=False, repr=False)

    def fit(self, confidences: Sequence[float], labels: Sequence[int]) -> "TemperatureScaler":
        """Learn the optimal temperature by minimizing NLL on (confidences, labels)."""
        confs = np.asarray(confidences, dtype=np.float64)
        labs = np.asarray(labels, dtype=np.float64)

        if len(confs) < 2:
            self.temperature = 1.0
            self._fitted = True
            return self

        # Clamp to avoid log(0)
        eps = 1e-12
        confs = np.clip(confs, eps, 1.0 - eps)
        logits = np.log(confs / (1.0 - confs))

        def nll(t: float) -> float:
            scaled = logits / max(t, eps)
            probs = 1.0 / (1.0 + np.exp(-scaled))
            probs = np.clip(probs, eps, 1.0 - eps)
            return float(-np.mean(labs * np.log(probs) + (1.0 - labs) * np.log(1.0 - probs)))

        result = minimize_scalar(nll, bounds=(0.01, 20.0), method="bounded")
        self.temperature = float(result.x)
        self._fitted = True
        return self

    def transform(self, confidence: float) -> float:
        """Apply temperature scaling to a single confidence value."""
        eps = 1e-12
        c = max(eps, min(1.0 - eps, confidence))
        logit = math.log(c / (1.0 - c))
        scaled = logit / max(self.temperature, eps)
        return 1.0 / (1.0 + math.exp(-scaled))


@dataclass
class PlattScaler:
    """Platt scaling: logistic regression on raw confidence scores.

    calibrated = sigmoid(a * confidence + b)

    Fits a and b by maximum likelihood via sklearn LogisticRegression.
    """

    a: float = 1.0
    b: float = 0.0
    _fitted: bool = field(default=False, repr=False)

    def fit(self, confidences: Sequence[float], labels: Sequence[int]) -> "PlattScaler":
        """Fit Platt scaling parameters via logistic regression."""
        confs = np.asarray(confidences, dtype=np.float64).reshape(-1, 1)
        labs = np.asarray(labels, dtype=np.int64)

        if len(confs) < 2 or len(np.unique(labs)) < 2:
            self.a = 1.0
            self.b = 0.0
            self._fitted = True
            return self

        lr = LogisticRegression(solver="lbfgs", max_iter=10_000, C=1e10)
        lr.fit(confs, labs)

        self.a = float(lr.coef_[0, 0])
        self.b = float(lr.intercept_[0])
        self._fitted = True
        return self

    def transform(self, confidence: float) -> float:
        """Apply Platt scaling to a single confidence value."""
        z = self.a * confidence + self.b
        # Numerically stable sigmoid
        if z >= 0:
            return 1.0 / (1.0 + math.exp(-z))
        ez = math.exp(z)
        return ez / (1.0 + ez)


@dataclass
class IsotonicScaler:
    """Non-parametric monotone calibration via isotonic regression.

    Wraps sklearn's IsotonicRegression with y_min=0, y_max=1.
    """

    _model: IsotonicRegression = field(
        default_factory=lambda: IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip"),
        repr=False,
    )
    _fitted: bool = field(default=False, repr=False)

    def fit(self, confidences: Sequence[float], labels: Sequence[int]) -> "IsotonicScaler":
        """Fit isotonic regression on (confidences, labels)."""
        confs = np.asarray(confidences, dtype=np.float64)
        labs = np.asarray(labels, dtype=np.float64)

        if len(confs) < 2:
            self._fitted = True
            return self

        self._model.fit(confs, labs)
        self._fitted = True
        return self

    def transform(self, confidence: float) -> float:
        """Apply isotonic regression to a single confidence value."""
        if not self._fitted:
            return confidence
        result = self._model.predict(np.array([confidence]))[0]
        return float(result)


def _source_family(source: str) -> str:
    if ":" not in source:
        return source
    return source.rsplit(":", 1)[-1]


def _is_fallback_action(candidate: DecisionCandidate) -> bool:
    evidence = candidate.evidence or {}
    return bool(
        evidence.get("is_fallback_action")
        or evidence.get("support_gate") == "fallback_action"
        or candidate.source == "fallback"
    )


@dataclass
class ThresholdCalibrator:
    """Choose the highest-confidence candidate and abstain if it falls below the threshold."""

    threshold: float = 0.5

    def choose(self, candidates: list[DecisionCandidate]) -> tuple[DecisionCandidate | None, bool]:
        if not candidates:
            return None, True
        best = max(candidates, key=lambda c: c.effective_confidence())
        return (best, best.effective_confidence() < self.threshold)


@dataclass
class EvidenceFusionCalibrator(ThresholdCalibrator):
    """Fuse candidates by action ID, apply source/agreement/margin bonuses, and penalize ambiguity."""

    source_bonus: float = 0.03
    agreement_bonus: float = 0.05
    margin_bonus: float = 0.03
    margin_scale: float = 1.5
    specificity_bonus: float = 0.02
    specificity_scale: float = 6.0
    fallback_competition_penalty: float = 0.12
    ambiguity_window: float = 0.05
    ambiguity_penalty: float = 0.08
    max_confidence: float = 0.999

    def choose(self, candidates: list[DecisionCandidate]) -> tuple[DecisionCandidate | None, bool]:
        if not candidates:
            return None, True

        fused = self._fuse_candidates(candidates)
        fused.sort(key=lambda candidate: candidate.effective_confidence(), reverse=True)
        chosen = fused[0]

        if len(fused) > 1:
            runner_up = fused[1]
            gap = chosen.effective_confidence() - runner_up.effective_confidence()
            ambiguity = self._ambiguity_penalty(chosen, runner_up, gap)
            if ambiguity > 0.0:
                chosen.confidence = max(0.0, chosen.confidence - ambiguity)
                chosen.evidence["ambiguity_penalty"] = ambiguity
                chosen.evidence["ambiguity_gap"] = gap
                chosen.evidence["runner_up_action_id"] = runner_up.action_id

        return (chosen, chosen.effective_confidence() < self.threshold)

    def _fuse_candidates(self, candidates: list[DecisionCandidate]) -> list[DecisionCandidate]:
        grouped: dict[str, list[DecisionCandidate]] = defaultdict(list)
        for candidate in candidates:
            grouped[candidate.action_id].append(candidate)

        has_non_fallback_group = any(not _is_fallback_action(candidate) for candidate in candidates)
        fused: list[DecisionCandidate] = []
        for action_id, group in grouped.items():
            representative = max(group, key=lambda candidate: candidate.effective_confidence())
            source_families = sorted({_source_family(candidate.source) for candidate in group})
            fallback_group = has_non_fallback_group and all(_is_fallback_action(candidate) for candidate in group)
            confidence = representative.effective_confidence()
            if not fallback_group:
                confidence += self.source_bonus * max(0, len(source_families) - 1)

                agreements = [candidate.agreement for candidate in group if candidate.agreement is not None]
                if agreements:
                    confidence += self.agreement_bonus * max(0.0, max(agreements) - 0.5) / 0.5

                margins = [candidate.margin for candidate in group if candidate.margin is not None]
                if margins:
                    confidence += self.margin_bonus * min(1.0, max(margins) / self.margin_scale)

                specificity = [
                    float(candidate.evidence.get("support_leaf_count", 0))
                    for candidate in group
                    if candidate.evidence.get("support_leaf_count") is not None
                ]
                if specificity:
                    confidence += self.specificity_bonus * min(1.0, max(specificity) / self.specificity_scale)
            else:
                confidence = max(0.0, confidence - self.fallback_competition_penalty)

            confidence = min(self.max_confidence, confidence)
            fused_candidate = representative.model_copy(deep=True)
            fused_candidate.confidence = confidence
            fused_candidate.source = "evidence_fusion_calibrator"
            fused_candidate.evidence.update(
                {
                    "fused_action_id": action_id,
                    "fused_from_sources": [candidate.source for candidate in group],
                    "fused_source_families": source_families,
                    "fused_candidate_count": len(group),
                    "fused_fallback_group": fallback_group,
                    "fused_raw_confidences": [candidate.effective_confidence() for candidate in group],
                    "fused_support_confidence_mean": mean(
                        candidate.support_confidence for candidate in group if candidate.support_confidence is not None
                    ) if any(candidate.support_confidence is not None for candidate in group) else None,
                }
            )
            fused.append(fused_candidate)
        return fused

    def _ambiguity_penalty(
        self,
        chosen: DecisionCandidate,
        runner_up: DecisionCandidate,
        gap: float,
    ) -> float:
        if _is_fallback_action(chosen) != _is_fallback_action(runner_up):
            return 0.0
        if gap >= self.ambiguity_window:
            return 0.0
        chosen_families = chosen.evidence.get("fused_source_families") or []
        runner_up_families = runner_up.evidence.get("fused_source_families") or []
        if len(chosen_families) < 2 and len(runner_up_families) < 2:
            return 0.0
        closeness = 1.0 - max(0.0, gap) / self.ambiguity_window
        return self.ambiguity_penalty * closeness


@dataclass
class DistanceRejector:
    """Reject candidates whose distance exceeds a configurable maximum."""

    max_distance: float = 0.25

    def reject(self, distance: float) -> bool:
        return distance > self.max_distance


def apply_abstention_policy(candidates: list[DecisionCandidate], threshold: float) -> tuple[DecisionCandidate | None, bool]:
    """Apply evidence-fusion calibration and return the chosen candidate with an abstain flag."""
    return EvidenceFusionCalibrator(threshold=threshold).choose(candidates)
