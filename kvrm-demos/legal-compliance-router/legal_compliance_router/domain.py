from __future__ import annotations

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "contract_value",
    "jurisdiction",
    "document_type",
    "risk_tier",
    "prior_counsel_approval",
    "legal_hold_active",
    "counterparty_reputation",
]

CATEGORICAL_VALUES = {
    "jurisdiction": ["domestic", "international", "restricted"],
    "document_type": ["nda", "msa", "sow", "amendment", "license"],
    "risk_tier": ["low", "medium", "high", "critical"],
    "counterparty_reputation": ["trusted", "neutral", "unknown", "flagged"],
}

RULES = {
    feature_key({
        "contract_value": 50000.0,
        "jurisdiction": "domestic",
        "document_type": "nda",
        "risk_tier": "low",
        "prior_counsel_approval": False,
        "legal_hold_active": False,
        "counterparty_reputation": "trusted",
    }): ("approve_contract", 0.95),
    feature_key({
        "contract_value": 500000.0,
        "jurisdiction": "international",
        "document_type": "msa",
        "risk_tier": "medium",
        "prior_counsel_approval": False,
        "legal_hold_active": False,
        "counterparty_reputation": "neutral",
    }): ("request_legal_review", 0.90),
    feature_key({
        "contract_value": 200000.0,
        "jurisdiction": "domestic",
        "document_type": "sow",
        "risk_tier": "low",
        "prior_counsel_approval": False,
        "legal_hold_active": True,
        "counterparty_reputation": "trusted",
    }): ("flag_compliance_audit", 0.88),
    feature_key({
        "contract_value": 500000.0,
        "jurisdiction": "domestic",
        "document_type": "msa",
        "risk_tier": "medium",
        "prior_counsel_approval": False,
        "legal_hold_active": False,
        "counterparty_reputation": "unknown",
    }): ("require_redline", 0.86),
    feature_key({
        "contract_value": 8000000.0,
        "jurisdiction": "restricted",
        "document_type": "license",
        "risk_tier": "high",
        "prior_counsel_approval": False,
        "legal_hold_active": False,
        "counterparty_reputation": "flagged",
    }): ("escalate_to_counsel", 0.94),
    feature_key({
        "contract_value": 25000000.0,
        "jurisdiction": "international",
        "document_type": "msa",
        "risk_tier": "critical",
        "prior_counsel_approval": False,
        "legal_hold_active": True,
        "counterparty_reputation": "flagged",
    }): ("escalate_to_general_counsel", 0.97),
    feature_key({
        "contract_value": 5000000.0,
        "jurisdiction": "international",
        "document_type": "license",
        "risk_tier": "high",
        "prior_counsel_approval": True,
        "legal_hold_active": False,
        "counterparty_reputation": "unknown",
    }): ("request_external_opinion", 0.85),
}

EXECUTOR_HANDLERS = {
    "approve_contract": "auto_approval",
    "request_legal_review": "legal_review",
    "flag_compliance_audit": "compliance",
    "require_redline": "negotiation",
    "escalate_to_counsel": "escalation",
    "escalate_to_general_counsel": "critical_escalation",
    "request_external_opinion": "external_advisory",
}

CONFIG = DomainConfig(
    name="legal",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="workflow",
    executor_include_action_key=True,
    reason_actions={"escalate_to_counsel", "escalate_to_general_counsel"},
    fallback_action_id="escalate_to_counsel",
    custom_numeric_keys={"contract_value": 100_000_000.0},
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
