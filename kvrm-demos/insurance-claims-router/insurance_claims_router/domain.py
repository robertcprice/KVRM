from __future__ import annotations

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "claim_amount",
    "claim_type",
    "policy_status",
    "documentation_complete",
    "fraud_score",
    "prior_claims_count",
    "coverage_verified",
]

CATEGORICAL_VALUES = {
    "claim_type": ["auto", "property", "health", "life", "liability"],
    "policy_status": ["active", "lapsed", "pending"],
}

RULES = {
    feature_key({
        "claim_amount": 2000.0,
        "claim_type": "auto",
        "policy_status": "active",
        "documentation_complete": True,
        "fraud_score": 0.05,
        "prior_claims_count": 1.0,
        "coverage_verified": True,
    }): ("auto_approve_claim", 0.95),
    feature_key({
        "claim_amount": 15000.0,
        "claim_type": "property",
        "policy_status": "active",
        "documentation_complete": False,
        "fraud_score": 0.1,
        "prior_claims_count": 2.0,
        "coverage_verified": True,
    }): ("request_documentation", 0.90),
    feature_key({
        "claim_amount": 25000.0,
        "claim_type": "auto",
        "policy_status": "active",
        "documentation_complete": True,
        "fraud_score": 0.15,
        "prior_claims_count": 2.0,
        "coverage_verified": True,
    }): ("assign_adjuster", 0.88),
    feature_key({
        "claim_amount": 75000.0,
        "claim_type": "health",
        "policy_status": "active",
        "documentation_complete": True,
        "fraud_score": 0.1,
        "prior_claims_count": 1.0,
        "coverage_verified": True,
    }): ("escalate_medical_review", 0.92),
    feature_key({
        "claim_amount": 80000.0,
        "claim_type": "auto",
        "policy_status": "active",
        "documentation_complete": True,
        "fraud_score": 0.75,
        "prior_claims_count": 8.0,
        "coverage_verified": True,
    }): ("flag_fraud_investigation", 0.94),
    feature_key({
        "claim_amount": 10000.0,
        "claim_type": "property",
        "policy_status": "lapsed",
        "documentation_complete": True,
        "fraud_score": 0.2,
        "prior_claims_count": 3.0,
        "coverage_verified": False,
    }): ("deny_claim", 0.96),
    feature_key({
        "claim_amount": 200000.0,
        "claim_type": "liability",
        "policy_status": "active",
        "documentation_complete": True,
        "fraud_score": 0.3,
        "prior_claims_count": 2.0,
        "coverage_verified": True,
    }): ("escalate_to_supervisor", 0.85),
}

EXECUTOR_HANDLERS = {
    "auto_approve_claim": "auto_approval",
    "request_documentation": "documentation",
    "assign_adjuster": "adjuster_assignment",
    "escalate_medical_review": "medical_review",
    "flag_fraud_investigation": "fraud_investigation",
    "deny_claim": "denial",
    "escalate_to_supervisor": "supervisor_escalation",
}

CONFIG = DomainConfig(
    name="insurance",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="workflow",
    executor_include_action_key=True,
    reason_actions={"escalate_to_supervisor"},
    fallback_action_id="escalate_to_supervisor",
    custom_numeric_keys={
        "claim_amount": 10_000_000.0,
        "fraud_score": 1.0,
        "prior_claims_count": 50.0,
    },
    support_aware_retrieval=True,
    prototype_max_distance=10.0,
    prototype_raw_distance_floor_ratio=0.5,
    semantic_tags={"escalation", "fallback"},
    semantic_min_leaf_count=5,
    semantic_base_confidence=0.82,
    semantic_per_leaf_bonus=0.02,
    semantic_max_confidence=0.98,
    learned_min_confidence=0.45,
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
