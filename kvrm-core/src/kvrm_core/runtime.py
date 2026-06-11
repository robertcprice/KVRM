from __future__ import annotations

import time

from .calibration import EvidenceFusionCalibrator, PostHocScaler
from .types import AuditRecord, DecisionInput, DecisionResult, ExecutionResult, ExecutionStatus, FinalStatus


class KVRMRuntime:
    """End-to-end decision runtime: select, calibrate, validate, and execute actions."""

    def __init__(self, registry, selector, validator, executor, threshold: float = 0.5, fallback_action_id: str | None = "request_human_review", post_hoc_scaler: PostHocScaler | None = None):
        self.registry = registry
        self.selector = selector
        self.validator = validator
        self.executor = executor
        self.calibrator = EvidenceFusionCalibrator(threshold=threshold)
        self.threshold = threshold
        self.fallback_action_id = fallback_action_id
        self.post_hoc_scaler = post_hoc_scaler
        self._actions = {action.action_id: action for action in registry.actions}

    def _validate_candidate(self, candidate, features):
        try:
            return self.validator.validate(candidate, features)
        except TypeError:
            return self.validator.validate(candidate)

    def _is_handoff_action(self, action_id: str | None) -> bool:
        if not action_id:
            return False
        action = self._actions.get(action_id)
        return bool(action and "fallback" in action.tags)

    def decide_and_execute(self, decision_input: DecisionInput) -> DecisionResult:
        """Run the full decide-validate-execute pipeline and return an auditable result."""
        started = time.perf_counter()
        candidates = self.selector.select(decision_input)
        chosen, abstain = self.calibrator.choose(candidates)
        if chosen and self.post_hoc_scaler is not None:
            chosen.confidence = self.post_hoc_scaler.transform(chosen.effective_confidence())
            abstain = chosen.effective_confidence() < self.threshold
        fallback_used = False
        validation_reason = None
        execution_result = None
        selected_action_id = chosen.action_id if chosen else None
        confidence = chosen.effective_confidence() if chosen else None
        selected_evidence = dict(chosen.evidence) if chosen else {}

        if abstain or chosen is None:
            final_status = FinalStatus.ABSTAINED
            if self.fallback_action_id:
                from .types import DecisionCandidate
                fallback_used = True
                chosen = DecisionCandidate(action_id=self.fallback_action_id, confidence=1.0, parameters={"reason": "low_confidence"}, source="fallback")
                selected_action_id = chosen.action_id
                confidence = chosen.effective_confidence()
                selected_evidence = dict(chosen.evidence)
                validation = self._validate_candidate(chosen, decision_input.features)
                validation_reason = validation.reason
                execution_result = self.executor.execute(chosen) if validation.valid else ExecutionResult(status=ExecutionStatus.BLOCKED, action_id=chosen.action_id, reason=validation.reason)
                final_status = FinalStatus.FALLBACK_EXECUTED if validation.valid else FinalStatus.FAIL_CLOSED
            else:
                execution_result = ExecutionResult(status=ExecutionStatus.BLOCKED, action_id=None, reason="abstained")
        else:
            validation = self._validate_candidate(chosen, decision_input.features)
            validation_reason = validation.reason
            if not validation.valid:
                if self.fallback_action_id:
                    from .types import DecisionCandidate
                    fallback_used = True
                    fallback = DecisionCandidate(action_id=self.fallback_action_id, confidence=1.0, parameters={"reason": validation.reason or "validation_failed"}, source="fallback")
                    fallback_validation = self._validate_candidate(fallback, decision_input.features)
                    if fallback_validation.valid:
                        execution_result = self.executor.execute(fallback)
                        selected_action_id = fallback.action_id
                        confidence = fallback.effective_confidence()
                        selected_evidence = dict(fallback.evidence)
                        final_status = FinalStatus.FALLBACK_EXECUTED
                    else:
                        execution_result = ExecutionResult(status=ExecutionStatus.BLOCKED, action_id=fallback.action_id, reason=fallback_validation.reason)
                        final_status = FinalStatus.FAIL_CLOSED
                else:
                    execution_result = ExecutionResult(status=ExecutionStatus.BLOCKED, action_id=chosen.action_id, reason=validation.reason)
                    final_status = FinalStatus.VALIDATION_FAILED
            else:
                execution_result = self.executor.execute(chosen)
                if self._is_handoff_action(chosen.action_id):
                    execution_result.status = ExecutionStatus.HANDOFF
                    final_status = FinalStatus.FALLBACK_EXECUTED
                else:
                    final_status = FinalStatus.EXECUTED

        latency_ms = (time.perf_counter() - started) * 1000
        correct = bool(decision_input.expected_action_id and selected_action_id == decision_input.expected_action_id)
        valid = selected_action_id is None or any(a.action_id == selected_action_id for a in self.registry.actions)
        audit = AuditRecord(
            case_id=decision_input.case_id,
            registry_digest=self.registry.digest or "",
            input_features=decision_input.features,
            candidate_scores=[],
            selected_action_id=selected_action_id,
            confidence=confidence,
            selected_evidence=selected_evidence,
            abstained=abstain,
            fallback_used=fallback_used,
            validation_reason=validation_reason,
            execution_status=execution_result.status.value if execution_result else None,
            final_status=final_status,
            latency_ms=latency_ms,
        )
        # simplify candidate scores structure
        audit.candidate_scores = [
            {
                "action_id": c.action_id,
                "confidence": c.confidence,
                "effective_confidence": c.effective_confidence(),
                "source": c.source,
                **({"action_confidence": c.action_confidence} if c.action_confidence is not None else {}),
                **({"support_confidence": c.support_confidence} if c.support_confidence is not None else {}),
                **({"distance": c.distance} if c.distance is not None else {}),
                **({"agreement": c.agreement} if c.agreement is not None else {}),
                **({"margin": c.margin} if c.margin is not None else {}),
                **({"evidence": c.evidence} if c.evidence else {}),
            }
            for c in candidates
        ]
        return DecisionResult(
            case_id=decision_input.case_id,
            selected_action_id=selected_action_id,
            confidence=confidence,
            abstained=abstain,
            fallback_used=fallback_used,
            valid=valid,
            correct=correct,
            final_status=final_status,
            validation_reason=validation_reason,
            execution_result=execution_result,
            audit_record=audit,
            latency_ms=latency_ms,
        )
