from __future__ import annotations

from typing import Any

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "sentiment",
    "issue_category",
    "customer_tier",
    "prior_contacts",
    "resolution_complexity",
    "account_age_days",
    "has_open_ticket",
    "escalation_history",
]

CATEGORICAL_VALUES = {
    "sentiment": ["positive", "neutral", "frustrated", "angry"],
    "issue_category": ["billing", "technical", "account", "shipping", "product_defect", "feature_request"],
    "customer_tier": ["free", "standard", "premium", "enterprise"],
    "prior_contacts": ["none", "one", "multiple", "excessive"],
    "resolution_complexity": ["simple", "moderate", "complex", "requires_engineering"],
    "account_age_days": ["new", "established", "veteran", "legacy"],
    "has_open_ticket": [True, False],
    "escalation_history": ["none", "previously_escalated", "multi_escalated"],
}


def _is_inconsistent_support_state(features: dict[str, Any]) -> bool:
    if features.get("has_open_ticket") is True and features.get("prior_contacts") == "none":
        return True
    if features.get("escalation_history") == "multi_escalated" and features.get("prior_contacts") == "none":
        return True
    if features.get("resolution_complexity") == "requires_engineering" and features.get("issue_category") == "feature_request":
        return True
    return False


RULES = {
    feature_key({
        "sentiment": "positive",
        "issue_category": "technical",
        "customer_tier": "standard",
        "prior_contacts": "none",
        "resolution_complexity": "simple",
        "account_age_days": "established",
        "has_open_ticket": False,
        "escalation_history": "none",
    }): ("send_knowledge_article", 0.95),
    feature_key({
        "sentiment": "neutral",
        "issue_category": "billing",
        "customer_tier": "standard",
        "prior_contacts": "none",
        "resolution_complexity": "simple",
        "account_age_days": "established",
        "has_open_ticket": False,
        "escalation_history": "none",
    }): ("auto_resolve_billing", 0.96),
    feature_key({
        "sentiment": "neutral",
        "issue_category": "technical",
        "customer_tier": "standard",
        "prior_contacts": "none",
        "resolution_complexity": "moderate",
        "account_age_days": "established",
        "has_open_ticket": False,
        "escalation_history": "none",
    }): ("assign_specialist", 0.92),
    feature_key({
        "sentiment": "frustrated",
        "issue_category": "technical",
        "customer_tier": "premium",
        "prior_contacts": "multiple",
        "resolution_complexity": "complex",
        "account_age_days": "veteran",
        "has_open_ticket": False,
        "escalation_history": "none",
    }): ("schedule_callback", 0.90),
    feature_key({
        "sentiment": "frustrated",
        "issue_category": "shipping",
        "customer_tier": "premium",
        "prior_contacts": "one",
        "resolution_complexity": "simple",
        "account_age_days": "established",
        "has_open_ticket": False,
        "escalation_history": "none",
    }): ("issue_refund", 0.94),
    feature_key({
        "sentiment": "angry",
        "issue_category": "billing",
        "customer_tier": "standard",
        "prior_contacts": "excessive",
        "resolution_complexity": "complex",
        "account_age_days": "established",
        "has_open_ticket": False,
        "escalation_history": "multi_escalated",
    }): ("escalate_to_manager", 0.97),
    feature_key({
        "sentiment": "frustrated",
        "issue_category": "product_defect",
        "customer_tier": "premium",
        "prior_contacts": "multiple",
        "resolution_complexity": "requires_engineering",
        "account_age_days": "established",
        "has_open_ticket": True,
        "escalation_history": "previously_escalated",
    }): ("escalate_to_manager", 0.95),
    feature_key({
        "sentiment": "angry",
        "issue_category": "billing",
        "customer_tier": "premium",
        "prior_contacts": "excessive",
        "resolution_complexity": "moderate",
        "account_age_days": "veteran",
        "has_open_ticket": True,
        "escalation_history": "previously_escalated",
    }): ("escalate_to_manager", 0.96),
    feature_key({
        "sentiment": "neutral",
        "issue_category": "technical",
        "customer_tier": "standard",
        "prior_contacts": "none",
        "resolution_complexity": "requires_engineering",
        "account_age_days": "established",
        "has_open_ticket": False,
        "escalation_history": "none",
    }): ("escalate_to_manager", 0.95),
    feature_key({
        "sentiment": "neutral",
        "issue_category": "feature_request",
        "customer_tier": "free",
        "prior_contacts": "none",
        "resolution_complexity": "moderate",
        "account_age_days": "new",
        "has_open_ticket": False,
        "escalation_history": "none",
    }): ("request_human_review", 0.85),
}

EXECUTOR_HANDLERS = {
    "send_knowledge_article": "send_knowledge_article",
    "auto_resolve_billing": "auto_resolve_billing",
    "assign_specialist": "assign_specialist",
    "schedule_callback": "schedule_callback",
    "issue_refund": "issue_refund",
    "escalate_to_manager": "escalate_to_manager",
    "request_human_review": "request_human_review",
}

CONFIG = DomainConfig(
    name="cs",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="workflow",
    reason_actions={"escalate_to_manager", "request_human_review"},
    fallback_action_id="request_human_review",
    unsupported_penalty=1.5,
    extra_predicate=_is_inconsistent_support_state,
    prototype_max_distance=4.5,
    prototype_raw_distance_floor_ratio=0.8,
    semantic_tags={"fallback"},
    semantic_min_leaf_count=4,
    semantic_base_confidence=0.80,
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
