from __future__ import annotations

from pathlib import Path

from iam_access_router import build_executor
from iam_access_router import build_hybrid_selector, build_rule_selector
from kvrm_bench.ceiling import load_cases, support_overlap_cases
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.types import DecisionInput, FinalStatus
from kvrm_core.validation import DeterministicValidator

ROOT = Path(__file__).resolve().parents[2] / "iam-access-router"
REGISTRY_PATH = ROOT / "data" / "registry.json"
TRAIN_CASES_PATH = ROOT / "data" / "train_cases.jsonl"


def test_rule_selector_routes_standard_access_case() -> None:
    selector = build_rule_selector()
    result = selector.select(
        DecisionInput(
            case_id="approve",
            features={
                "requested_privilege": "standard",
                "resource_sensitivity": "low",
                "requester_risk": "low",
                "mfa_state": "verified",
                "manager_approval": "approved",
                "security_review": "not_required",
                "justification": "routine",
                "device_posture": "compliant",
                "session_scope": "persistent",
                "sod_risk": "none",
                "on_call_role": "none",
                "ticket_state": "missing",
            },
        )
    )
    assert result[0].action_id == "auto_approve_standard_access"


def test_hybrid_selector_routes_break_glass_case() -> None:
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(
        DecisionInput(
            case_id="break-glass",
            features={
                "requested_privilege": "admin",
                "resource_sensitivity": "critical",
                "requester_risk": "low",
                "mfa_state": "verified",
                "manager_approval": "approved",
                "security_review": "pending",
                "justification": "break_glass",
                "device_posture": "compliant",
                "session_scope": "emergency",
                "sod_risk": "potential",
                "on_call_role": "primary",
                "ticket_state": "linked",
            },
        )
    )
    assert result[0].action_id == "grant_break_glass_access"


def test_hybrid_selector_routes_unknown_device_admin_case_to_escalation() -> None:
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(
        DecisionInput(
            case_id="escalate",
            features={
                "requested_privilege": "admin",
                "resource_sensitivity": "critical",
                "requester_risk": "medium",
                "mfa_state": "verified",
                "manager_approval": "approved",
                "security_review": "approved",
                "justification": "incident_response",
                "device_posture": "unknown",
                "session_scope": "timeboxed",
                "sod_risk": "none",
                "on_call_role": "secondary",
                "ticket_state": "linked",
            },
        )
    )
    assert result[0].action_id == "escalate_identity_admin"


def test_runtime_fails_closed_for_emergency_without_break_glass_envelope() -> None:
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(
        registry,
        build_hybrid_selector(TRAIN_CASES_PATH),
        DeterministicValidator(registry),
        build_executor(),
        threshold=0.6,
        fallback_action_id="escalate_identity_admin",
    )
    result = runtime.decide_and_execute(
        DecisionInput(
            case_id="unsupported-emergency",
            features={
                "requested_privilege": "elevated",
                "resource_sensitivity": "restricted",
                "requester_risk": "low",
                "mfa_state": "verified",
                "manager_approval": "approved",
                "security_review": "approved",
                "justification": "routine",
                "device_posture": "compliant",
                "session_scope": "emergency",
                "sod_risk": "none",
                "on_call_role": "none",
                "ticket_state": "linked",
            },
            supported=False,
            ood=True,
        )
    )
    assert result.final_status in {FinalStatus.FAIL_CLOSED, FinalStatus.FALLBACK_EXECUTED}
    assert result.selected_action_id == "escalate_identity_admin"


def test_iam_registry_has_no_supported_overlap_cases() -> None:
    registry = load_registry(REGISTRY_PATH)
    cases = load_cases(ROOT / "data" / "cases.jsonl")
    assert support_overlap_cases(registry, cases, supported_only=True) == []
