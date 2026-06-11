from __future__ import annotations

from typing import Any

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "requested_privilege",
    "resource_sensitivity",
    "requester_risk",
    "mfa_state",
    "manager_approval",
    "security_review",
    "justification",
    "device_posture",
    "session_scope",
    "sod_risk",
    "on_call_role",
    "ticket_state",
]

CATEGORICAL_VALUES = {
    "requested_privilege": ["standard", "elevated", "admin"],
    "resource_sensitivity": ["low", "internal", "restricted", "critical"],
    "requester_risk": ["low", "medium", "high"],
    "mfa_state": ["verified", "missing", "bypassed"],
    "manager_approval": ["approved", "pending", "denied"],
    "security_review": ["not_required", "pending", "approved", "blocked"],
    "justification": ["routine", "project", "incident_response", "break_glass", "insufficient"],
    "device_posture": ["compliant", "unknown", "untrusted"],
    "session_scope": ["persistent", "timeboxed", "emergency"],
    "sod_risk": ["none", "potential", "confirmed"],
    "on_call_role": ["none", "secondary", "primary"],
    "ticket_state": ["linked", "missing", "expired"],
}


def _is_inconsistent_iam_state(features: dict[str, Any]) -> bool:
    if features.get("session_scope") == "emergency" and features.get("justification") != "break_glass":
        return True
    if features.get("justification") == "break_glass" and features.get("ticket_state") != "linked":
        return True
    if features.get("on_call_role") == "primary" and features.get("session_scope") != "emergency":
        return True
    if features.get("requested_privilege") == "standard" and features.get("session_scope") == "emergency":
        return True
    if features.get("requested_privilege") == "admin" and features.get("session_scope") == "persistent":
        return True
    return False


RULES = {
    feature_key({
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
    }): ("auto_approve_standard_access", 0.98),
    feature_key({
        "requested_privilege": "elevated",
        "resource_sensitivity": "restricted",
        "requester_risk": "medium",
        "mfa_state": "verified",
        "manager_approval": "pending",
        "security_review": "not_required",
        "justification": "project",
        "device_posture": "unknown",
        "session_scope": "timeboxed",
        "sod_risk": "none",
        "on_call_role": "none",
        "ticket_state": "linked",
    }): ("require_manager_approval", 0.92),
    feature_key({
        "requested_privilege": "admin",
        "resource_sensitivity": "critical",
        "requester_risk": "low",
        "mfa_state": "verified",
        "manager_approval": "approved",
        "security_review": "pending",
        "justification": "incident_response",
        "device_posture": "compliant",
        "session_scope": "timeboxed",
        "sod_risk": "potential",
        "on_call_role": "secondary",
        "ticket_state": "linked",
    }): ("require_security_review", 0.92),
    feature_key({
        "requested_privilege": "elevated",
        "resource_sensitivity": "restricted",
        "requester_risk": "low",
        "mfa_state": "verified",
        "manager_approval": "approved",
        "security_review": "approved",
        "justification": "project",
        "device_posture": "compliant",
        "session_scope": "timeboxed",
        "sod_risk": "none",
        "on_call_role": "none",
        "ticket_state": "linked",
    }): ("grant_timeboxed_privileged_access", 0.96),
    feature_key({
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
    }): ("grant_break_glass_access", 0.99),
    feature_key({
        "requested_privilege": "elevated",
        "resource_sensitivity": "restricted",
        "requester_risk": "high",
        "mfa_state": "verified",
        "manager_approval": "approved",
        "security_review": "approved",
        "justification": "project",
        "device_posture": "compliant",
        "session_scope": "timeboxed",
        "sod_risk": "none",
        "on_call_role": "none",
        "ticket_state": "linked",
    }): ("deny_request", 0.97),
    feature_key({
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
    }): ("escalate_identity_admin", 0.93),
}

EXECUTOR_HANDLERS = {
    "auto_approve_standard_access": "auto_approve_standard_access",
    "require_manager_approval": "require_manager_approval",
    "require_security_review": "require_security_review",
    "grant_timeboxed_privileged_access": "grant_timeboxed_privileged_access",
    "grant_break_glass_access": "grant_break_glass_access",
    "deny_request": "deny_request",
    "escalate_identity_admin": "escalate_identity_admin",
}

CONFIG = DomainConfig(
    name="iam",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="workflow",
    reason_actions={"deny_request", "escalate_identity_admin"},
    fallback_action_id="escalate_identity_admin",
    unsupported_penalty=1.5,
    extra_predicate=_is_inconsistent_iam_state,
    prototype_max_distance=5.5,
    prototype_raw_distance_floor_ratio=0.8,
    semantic_tags={"fallback"},
    semantic_min_leaf_count=4,
    semantic_base_confidence=0.82,
    semantic_per_leaf_bonus=0.02,
    semantic_max_confidence=0.96,
    learned_min_confidence=0.44,
    learned_candidate_floor=0.20,
)

(
    build_rule_selector,
    build_retrieval_selector,
    build_prototype_selector,
    build_semantic_selector,
    build_learned_selector,
    build_hybrid_selector,
) = build_domain_selectors(CONFIG)


def build_executor() -> DictionaryExecutor:
    return build_domain_executor(CONFIG)
