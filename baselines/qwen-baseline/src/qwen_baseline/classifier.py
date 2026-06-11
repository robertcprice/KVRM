"""Sklearn-based proxy for a fine-tuned Qwen 0.5-0.8B classifier.

Three variants matching the Qwen comparison protocol:
  A) DirectLabelClassifier: predicts one label (no rejection)
  B) JsonActionClassifier: predicts label + confidence (thresholded rejection)
  C) ConstrainedClassifier: forced-choice from allowed label set (no rejection)

These are intentionally strong baselines:
  - Random forest with enough capacity to memorize small train sets
  - Calibrated probability estimates for Variant B thresholding
  - No deliberate handicap

The point is to show that even a strong classifier baseline lacks the
systems-architecture properties KVRM provides.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV

from .feature_encoder import encode_features, encode_batch
from .domain_schemas import DOMAINS


@dataclass
class BaselineResult:
    case_id: str
    predicted_action_id: str | None
    confidence: float
    abstained: bool
    latency_ms: float
    variant: str
    valid: bool = True       # structural validity
    correct: bool = False
    fallback_used: bool = False
    final_status: str = "executed"


@dataclass
class DirectLabelClassifier:
    """Variant A: predict one label, never abstain."""
    domain: str
    model: RandomForestClassifier | None = None
    label_list: list[str] = field(default_factory=list)

    def train(self, train_cases: list[dict]):
        cfg = DOMAINS[self.domain]
        self.label_list = cfg["labels"]
        X = encode_batch(train_cases, cfg["feature_schema"], cfg["feature_order"])
        y = np.array([self.label_list.index(c["expected_action_id"]) for c in train_cases])
        self.model = RandomForestClassifier(
            n_estimators=100, max_depth=None, random_state=42
        )
        self.model.fit(X, y)

    def predict(self, case: dict) -> BaselineResult:
        cfg = DOMAINS[self.domain]
        t0 = time.perf_counter()
        x = encode_features(case["input_features"], cfg["feature_schema"], cfg["feature_order"]).reshape(1, -1)
        pred_class = self.model.predict(x)[0]
        proba = self.model.predict_proba(x)[0]
        # model.classes_ may be a subset of all labels if training set
        # doesn't cover every label. Map correctly.
        class_idx = list(self.model.classes_).index(pred_class)
        conf = float(proba[class_idx])
        action_id = self.label_list[pred_class]
        latency = (time.perf_counter() - t0) * 1000

        correct = case.get("expected_action_id") == action_id
        # Direct label: always predicts, never abstains
        # On unsupported cases, this means false-accept
        supported = case.get("supported", True)
        if not supported and case.get("expected_action_id") is None:
            # Any prediction on unsupported = false accept
            correct = False
            final_status = "executed"  # false accept
        else:
            final_status = "executed"

        return BaselineResult(
            case_id=case["case_id"],
            predicted_action_id=action_id,
            confidence=conf,
            abstained=False,
            latency_ms=latency,
            variant="direct_label",
            valid=action_id in self.label_list,
            correct=correct,
            fallback_used=False,
            final_status=final_status,
        )


@dataclass
class JsonActionClassifier:
    """Variant B: predict label + confidence, abstain if below threshold."""
    domain: str
    threshold: float = 0.60
    model: GradientBoostingClassifier | None = None
    calibrated_model: CalibratedClassifierCV | None = None
    label_list: list[str] = field(default_factory=list)

    def train(self, train_cases: list[dict]):
        cfg = DOMAINS[self.domain]
        self.label_list = cfg["labels"]
        X = encode_batch(train_cases, cfg["feature_schema"], cfg["feature_order"])
        y = np.array([self.label_list.index(c["expected_action_id"]) for c in train_cases])
        base = GradientBoostingClassifier(
            n_estimators=50, max_depth=3, random_state=42
        )
        # With very small datasets, calibration may not help much
        # but we include it for protocol compliance
        if len(train_cases) >= 5:
            self.calibrated_model = CalibratedClassifierCV(base, cv=min(3, len(train_cases)), method="isotonic")
            try:
                self.calibrated_model.fit(X, y)
            except ValueError:
                # fall back to uncalibrated if cv fails
                base.fit(X, y)
                self.model = base
                self.calibrated_model = None
        else:
            base.fit(X, y)
            self.model = base

    def predict(self, case: dict) -> BaselineResult:
        cfg = DOMAINS[self.domain]
        t0 = time.perf_counter()
        x = encode_features(case["input_features"], cfg["feature_schema"], cfg["feature_order"]).reshape(1, -1)

        m = self.calibrated_model or self.model
        pred_class = m.predict(x)[0]
        proba = m.predict_proba(x)[0]
        class_idx = list(m.classes_).index(pred_class)
        conf = float(proba[class_idx])
        latency = (time.perf_counter() - t0) * 1000

        fallback = cfg["fallback"]
        supported = case.get("supported", True)

        if conf < self.threshold:
            # Low confidence -> fallback
            action_id = fallback
            abstained = True
            fallback_used = True
            final_status = "fallback_executed"
        else:
            action_id = self.label_list[pred_class]
            abstained = False
            fallback_used = False
            final_status = "executed"

        if not supported and case.get("expected_action_id") is None:
            if not abstained:
                correct = False  # false accept
            else:
                correct = False  # correctly rejected (not "correct" per se)
        else:
            correct = case.get("expected_action_id") == action_id

        return BaselineResult(
            case_id=case["case_id"],
            predicted_action_id=action_id,
            confidence=conf,
            abstained=abstained,
            latency_ms=latency,
            variant="json_action",
            valid=action_id in self.label_list,
            correct=correct,
            fallback_used=fallback_used,
            final_status=final_status,
        )


@dataclass
class ConstrainedClassifier:
    """Variant C: forced-choice from allowed label set, never abstain."""
    domain: str
    model: RandomForestClassifier | None = None
    label_list: list[str] = field(default_factory=list)

    def train(self, train_cases: list[dict]):
        cfg = DOMAINS[self.domain]
        self.label_list = cfg["labels"]
        X = encode_batch(train_cases, cfg["feature_schema"], cfg["feature_order"])
        y = np.array([self.label_list.index(c["expected_action_id"]) for c in train_cases])
        self.model = RandomForestClassifier(
            n_estimators=200, max_depth=None, random_state=42
        )
        self.model.fit(X, y)

    def predict(self, case: dict) -> BaselineResult:
        cfg = DOMAINS[self.domain]
        t0 = time.perf_counter()
        x = encode_features(case["input_features"], cfg["feature_schema"], cfg["feature_order"]).reshape(1, -1)
        pred_class = self.model.predict(x)[0]
        proba = self.model.predict_proba(x)[0]
        class_idx = list(self.model.classes_).index(pred_class)
        conf = float(proba[class_idx])
        action_id = self.label_list[pred_class]
        latency = (time.perf_counter() - t0) * 1000

        supported = case.get("supported", True)
        if not supported and case.get("expected_action_id") is None:
            correct = False
            final_status = "executed"
        else:
            correct = case.get("expected_action_id") == action_id
            final_status = "executed"

        return BaselineResult(
            case_id=case["case_id"],
            predicted_action_id=action_id,
            confidence=conf,
            abstained=False,
            latency_ms=latency,
            variant="constrained",
            valid=True,  # always structurally valid by construction
            correct=correct,
            fallback_used=False,
            final_status=final_status,
        )
