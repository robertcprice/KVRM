from __future__ import annotations

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "transaction_amount",
    "jurisdiction_risk",
    "anomaly_score",
    "account_history",
    "kyc_completeness",
    "velocity_indicator",
    "sanctions_hit",
    "document_mismatch",
    "device_trust",
]

CATEGORICAL_VALUES = {
    "transaction_amount": ["low", "medium", "high", "very_high"],
    "jurisdiction_risk": ["low", "medium", "high"],
    "anomaly_score": ["low", "medium", "high", "severe"],
    "account_history": ["clean", "watch", "prior_incident"],
    "kyc_completeness": ["complete", "partial", "missing"],
    "velocity_indicator": ["normal", "elevated", "high"],
    "device_trust": ["trusted", "new", "anonymous"],
}

RULES = {
    feature_key({
        "transaction_amount": "low",
        "jurisdiction_risk": "low",
        "anomaly_score": "low",
        "account_history": "clean",
        "kyc_completeness": "complete",
        "velocity_indicator": "normal",
        "sanctions_hit": False,
        "document_mismatch": False,
        "device_trust": "trusted",
    }): ("approve_low_risk", 0.97),
    feature_key({
        "transaction_amount": "medium",
        "jurisdiction_risk": "medium",
        "anomaly_score": "medium",
        "account_history": "watch",
        "kyc_completeness": "complete",
        "velocity_indicator": "normal",
        "sanctions_hit": False,
        "document_mismatch": False,
        "device_trust": "trusted",
    }): ("allow_with_monitoring", 0.89),
    feature_key({
        "transaction_amount": "high",
        "jurisdiction_risk": "high",
        "anomaly_score": "low",
        "account_history": "clean",
        "kyc_completeness": "complete",
        "velocity_indicator": "normal",
        "sanctions_hit": False,
        "document_mismatch": False,
        "device_trust": "new",
    }): ("enhanced_due_diligence", 0.93),
    feature_key({
        "transaction_amount": "medium",
        "jurisdiction_risk": "medium",
        "anomaly_score": "low",
        "account_history": "clean",
        "kyc_completeness": "partial",
        "velocity_indicator": "normal",
        "sanctions_hit": False,
        "document_mismatch": True,
        "device_trust": "trusted",
    }): ("require_additional_docs", 0.92),
    feature_key({
        "transaction_amount": "medium",
        "jurisdiction_risk": "low",
        "anomaly_score": "high",
        "account_history": "clean",
        "kyc_completeness": "complete",
        "velocity_indicator": "high",
        "sanctions_hit": False,
        "document_mismatch": False,
        "device_trust": "trusted",
    }): ("lower_limit_temporarily", 0.91),
    feature_key({
        "transaction_amount": "high",
        "jurisdiction_risk": "medium",
        "anomaly_score": "severe",
        "account_history": "prior_incident",
        "kyc_completeness": "complete",
        "velocity_indicator": "high",
        "sanctions_hit": False,
        "document_mismatch": False,
        "device_trust": "anonymous",
    }): ("freeze_for_investigation", 0.98),
    feature_key({
        "transaction_amount": "high",
        "jurisdiction_risk": "high",
        "anomaly_score": "high",
        "account_history": "watch",
        "kyc_completeness": "missing",
        "velocity_indicator": "elevated",
        "sanctions_hit": True,
        "document_mismatch": True,
        "device_trust": "anonymous",
    }): ("escalate_compliance", 0.99),
    feature_key({
        "transaction_amount": "high",
        "jurisdiction_risk": "medium",
        "anomaly_score": "medium",
        "account_history": "watch",
        "kyc_completeness": "partial",
        "velocity_indicator": "elevated",
        "sanctions_hit": False,
        "document_mismatch": False,
        "device_trust": "anonymous",
    }): ("manual_review", 0.87),
}

EXECUTOR_HANDLERS = {
    "approve_low_risk": "approve_low_risk",
    "allow_with_monitoring": "allow_with_monitoring",
    "enhanced_due_diligence": "enhanced_due_diligence",
    "require_additional_docs": "require_additional_docs",
    "lower_limit_temporarily": "lower_limit_temporarily",
    "freeze_for_investigation": "freeze_for_investigation",
    "escalate_compliance": "escalate_compliance",
    "manual_review": "manual_review",
}

CONFIG = DomainConfig(
    name="finance",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="workflow",
    reason_actions={"escalate_compliance", "manual_review"},
    fallback_action_id="manual_review",
    prototype_max_distance=4.5,
    prototype_raw_distance_floor_ratio=0.8,
    semantic_min_leaf_count=4,
    semantic_base_confidence=0.78,
    semantic_per_leaf_bonus=0.02,
    semantic_max_confidence=0.96,
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
