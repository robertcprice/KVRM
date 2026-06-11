from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FinalStatus(str, Enum):
    EXECUTED = "executed"
    ABSTAINED = "abstained"
    FALLBACK_EXECUTED = "fallback_executed"
    FAIL_CLOSED = "fail_closed"
    VALIDATION_FAILED = "validation_failed"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    HANDOFF = "handoff"
    BLOCKED = "blocked"
    FAILED = "failed"


class ActionSpec(BaseModel):
    """Specification of a single action in the registry, including its support constraints."""

    action_id: str
    name: str
    description: str
    parameters_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}, "required": []})
    support_spec: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class RegistrySpec(BaseModel):
    """Top-level registry containing versioned actions, required features, and context schema."""

    registry_name: str
    version: str
    actions: list[ActionSpec]
    required_features: list[str] = Field(default_factory=list)
    context_schema: dict[str, dict[str, Any]] = Field(default_factory=dict)
    digest: str | None = None


class DecisionInput(BaseModel):
    """Input to the decision pipeline: case identifier, features, and optional expected action."""

    case_id: str
    features: dict[str, Any]
    supported: bool = True
    ood: bool = False
    expected_action_id: str | None = None


class DecisionCandidate(BaseModel):
    """A scored candidate action emitted by a selector, with confidence and evidence signals."""

    action_id: str
    confidence: float
    parameters: dict[str, Any] = Field(default_factory=dict)
    source: str = "selector"
    action_confidence: float | None = None
    support_confidence: float | None = None
    distance: float | None = None
    agreement: float | None = None
    margin: float | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)

    def effective_confidence(self) -> float:
        score = self.confidence
        if self.action_confidence is not None:
            score = min(score, self.action_confidence)
        if self.support_confidence is not None:
            score = min(score, self.support_confidence)
        return score


class ValidationResult(BaseModel):
    """Outcome of candidate validation: valid flag and optional rejection reason."""

    valid: bool
    reason: str | None = None


class ExecutionResult(BaseModel):
    """Result of executing an action: status, output payload, and optional failure reason."""

    status: ExecutionStatus
    action_id: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class AuditRecord(BaseModel):
    """Full audit trail of a single decision: inputs, scores, selection, and execution outcome."""

    case_id: str
    registry_digest: str
    input_features: dict[str, Any]
    candidate_scores: list[dict[str, Any]] = Field(default_factory=list)
    selected_action_id: str | None = None
    confidence: float | None = None
    selected_evidence: dict[str, Any] = Field(default_factory=dict)
    abstained: bool = False
    fallback_used: bool = False
    validation_reason: str | None = None
    execution_status: str | None = None
    final_status: FinalStatus
    latency_ms: float


class DecisionResult(BaseModel):
    """Top-level result of the decision pipeline, including audit record and latency."""

    case_id: str
    selected_action_id: str | None = None
    confidence: float | None = None
    abstained: bool = False
    fallback_used: bool = False
    valid: bool = False
    correct: bool = False
    final_status: FinalStatus
    validation_reason: str | None = None
    execution_result: ExecutionResult | None = None
    audit_record: AuditRecord
    latency_ms: float


class CaseRecord(BaseModel):
    """A labeled training/evaluation case with input features and expected action."""

    case_id: str
    input_features: dict[str, Any]
    expected_action_id: str | None = None
    supported: bool = True
    ood: bool = False
