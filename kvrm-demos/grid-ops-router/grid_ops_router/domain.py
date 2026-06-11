from __future__ import annotations

from typing import Any

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "outage_scope",
    "relay_state",
    "customer_impact",
    "reserve_margin",
    "frequency_deviation",
    "voltage_stability",
    "crew_availability",
    "weather_risk",
    "fault_isolation_ready",
    "switching_authorized",
    "transfer_path_available",
    "blackstart_required",
]

CATEGORICAL_VALUES = {
    "outage_scope": ["none", "feeder", "substation", "regional"],
    "relay_state": ["normal", "tripped", "reclose_lockout"],
    "customer_impact": ["low", "medium", "high", "critical"],
    "reserve_margin": ["low", "adequate", "high"],
    "frequency_deviation": ["normal", "mild", "severe"],
    "voltage_stability": ["stable", "degraded", "unstable"],
    "crew_availability": ["limited", "available", "surge"],
    "weather_risk": ["low", "elevated", "severe"],
}


def _is_inconsistent_grid_state(features: dict[str, Any]) -> bool:
    if features.get("outage_scope") == "none" and features.get("customer_impact") in {"high", "critical"}:
        return True
    if features.get("outage_scope") == "none" and features.get("relay_state") != "normal":
        return True
    if features.get("blackstart_required") and features.get("outage_scope") != "regional":
        return True
    if features.get("fault_isolation_ready") and features.get("relay_state") == "normal":
        return True
    return False


RULES = {
    feature_key({
        "outage_scope": "none",
        "relay_state": "normal",
        "customer_impact": "low",
        "reserve_margin": "adequate",
        "frequency_deviation": "normal",
        "voltage_stability": "stable",
        "crew_availability": "available",
        "weather_risk": "low",
        "fault_isolation_ready": False,
        "switching_authorized": True,
        "transfer_path_available": False,
        "blackstart_required": False,
    }): ("continue_monitoring", 0.96),
    feature_key({
        "outage_scope": "feeder",
        "relay_state": "tripped",
        "customer_impact": "high",
        "reserve_margin": "adequate",
        "frequency_deviation": "mild",
        "voltage_stability": "degraded",
        "crew_availability": "available",
        "weather_risk": "low",
        "fault_isolation_ready": True,
        "switching_authorized": True,
        "transfer_path_available": False,
        "blackstart_required": False,
    }): ("isolate_faulted_feeder", 0.96),
    feature_key({
        "outage_scope": "substation",
        "relay_state": "reclose_lockout",
        "customer_impact": "critical",
        "reserve_margin": "adequate",
        "frequency_deviation": "mild",
        "voltage_stability": "degraded",
        "crew_availability": "available",
        "weather_risk": "elevated",
        "fault_isolation_ready": False,
        "switching_authorized": True,
        "transfer_path_available": True,
        "blackstart_required": False,
    }): ("transfer_load", 0.93),
    feature_key({
        "outage_scope": "feeder",
        "relay_state": "tripped",
        "customer_impact": "medium",
        "reserve_margin": "adequate",
        "frequency_deviation": "normal",
        "voltage_stability": "stable",
        "crew_availability": "available",
        "weather_risk": "low",
        "fault_isolation_ready": False,
        "switching_authorized": True,
        "transfer_path_available": False,
        "blackstart_required": False,
    }): ("dispatch_field_crew", 0.90),
    feature_key({
        "outage_scope": "regional",
        "relay_state": "normal",
        "customer_impact": "high",
        "reserve_margin": "low",
        "frequency_deviation": "severe",
        "voltage_stability": "degraded",
        "crew_availability": "limited",
        "weather_risk": "low",
        "fault_isolation_ready": False,
        "switching_authorized": True,
        "transfer_path_available": False,
        "blackstart_required": False,
    }): ("shed_noncritical_load", 0.95),
    feature_key({
        "outage_scope": "regional",
        "relay_state": "normal",
        "customer_impact": "critical",
        "reserve_margin": "low",
        "frequency_deviation": "severe",
        "voltage_stability": "unstable",
        "crew_availability": "available",
        "weather_risk": "elevated",
        "fault_isolation_ready": False,
        "switching_authorized": False,
        "transfer_path_available": False,
        "blackstart_required": True,
    }): ("prepare_blackstart", 0.98),
    feature_key({
        "outage_scope": "feeder",
        "relay_state": "tripped",
        "customer_impact": "medium",
        "reserve_margin": "adequate",
        "frequency_deviation": "normal",
        "voltage_stability": "stable",
        "crew_availability": "available",
        "weather_risk": "severe",
        "fault_isolation_ready": True,
        "switching_authorized": False,
        "transfer_path_available": False,
        "blackstart_required": False,
    }): ("defer_switching_due_weather", 0.94),
}

EXECUTOR_HANDLERS = {
    "continue_monitoring": "continue_monitoring",
    "isolate_faulted_feeder": "isolate_faulted_feeder",
    "transfer_load": "transfer_load",
    "dispatch_field_crew": "dispatch_field_crew",
    "shed_noncritical_load": "shed_noncritical_load",
    "prepare_blackstart": "prepare_blackstart",
    "defer_switching_due_weather": "defer_switching_due_weather",
    "escalate_grid_supervisor": "escalate_grid_supervisor",
}

CONFIG = DomainConfig(
    name="grid",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="workflow",
    reason_actions={"escalate_grid_supervisor"},
    fallback_action_id="escalate_grid_supervisor",
    extra_predicate=_is_inconsistent_grid_state,
    prototype_max_distance=6.0,
    prototype_raw_distance_floor_ratio=0.8,
    semantic_tags={"fallback"},
    semantic_min_leaf_count=4,
    semantic_base_confidence=0.82,
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
