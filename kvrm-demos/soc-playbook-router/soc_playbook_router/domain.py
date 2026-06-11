from __future__ import annotations

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "severity",
    "threat_confidence",
    "asset_criticality",
    "lateral_movement",
    "blast_radius",
    "internet_exposed",
    "credential_exposure",
    "endpoint_type",
]

CATEGORICAL_VALUES = {
    "severity": ["informational", "low", "medium", "high", "critical"],
    "threat_confidence": ["low", "medium", "high"],
    "asset_criticality": ["tier3", "tier2", "tier1"],
    "blast_radius": ["none", "narrow", "contained", "wide", "massive"],
    "endpoint_type": ["host", "server", "cloud_identity", "edge"],
}

RULES = {
    feature_key({
        "severity": "critical",
        "threat_confidence": "high",
        "asset_criticality": "tier1",
        "lateral_movement": True,
        "blast_radius": "wide",
        "internet_exposed": True,
        "credential_exposure": True,
        "endpoint_type": "server",
    }): ("escalate_p1", 0.98),
    feature_key({
        "severity": "high",
        "threat_confidence": "high",
        "asset_criticality": "tier2",
        "lateral_movement": False,
        "blast_radius": "contained",
        "internet_exposed": True,
        "credential_exposure": False,
        "endpoint_type": "host",
    }): ("isolate_host", 0.94),
    feature_key({
        "severity": "medium",
        "threat_confidence": "high",
        "asset_criticality": "tier2",
        "lateral_movement": False,
        "blast_radius": "contained",
        "internet_exposed": True,
        "credential_exposure": True,
        "endpoint_type": "cloud_identity",
    }): ("rotate_credentials", 0.90),
    feature_key({
        "severity": "medium",
        "threat_confidence": "medium",
        "asset_criticality": "tier3",
        "lateral_movement": False,
        "blast_radius": "narrow",
        "internet_exposed": True,
        "credential_exposure": False,
        "endpoint_type": "edge",
    }): ("block_ip_temporarily", 0.82),
    feature_key({
        "severity": "medium",
        "threat_confidence": "medium",
        "asset_criticality": "tier3",
        "lateral_movement": False,
        "blast_radius": "narrow",
        "internet_exposed": False,
        "credential_exposure": False,
        "endpoint_type": "host",
    }): ("collect_forensics", 0.76),
    feature_key({
        "severity": "low",
        "threat_confidence": "medium",
        "asset_criticality": "tier3",
        "lateral_movement": False,
        "blast_radius": "narrow",
        "internet_exposed": False,
        "credential_exposure": False,
        "endpoint_type": "host",
    }): ("monitor_only", 0.73),
    feature_key({
        "severity": "informational",
        "threat_confidence": "low",
        "asset_criticality": "tier3",
        "lateral_movement": False,
        "blast_radius": "none",
        "internet_exposed": False,
        "credential_exposure": False,
        "endpoint_type": "host",
    }): ("do_nothing_validated", 0.88),
}

EXECUTOR_HANDLERS = {
    "isolate_host": "containment",
    "rotate_credentials": "identity_response",
    "collect_forensics": "investigation",
    "escalate_p1": "critical_incident",
    "block_ip_temporarily": "network_response",
    "monitor_only": "monitoring",
    "request_human_triage": "human_triage",
    "do_nothing_validated": "validated_noop",
}

CONFIG = DomainConfig(
    name="soc",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="playbook",
    executor_include_action_key=True,
    executor_action_overrides={"escalate_p1": "page_p1"},
    reason_actions={"request_human_triage"},
    fallback_action_id="request_human_triage",
    support_aware_retrieval=True,
    prototype_max_distance=10.0,
    prototype_raw_distance_floor_ratio=0.5,
    semantic_tags={"noop", "fallback"},
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
