from __future__ import annotations

from typing import Any

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "battery",
    "comms",
    "gps",
    "wind",
    "obstacle_density",
    "threat_level",
    "mission_urgency",
    "payload_criticality",
    "distance_to_home",
    "estimated_energy_margin",
    "mission_progress",
    "safe_landing_zone_available",
    "autonomous_recovery_allowed",
    "pilot_takeover_link_quality",
    "pilot_response_eta",
    "takeover_window_remaining",
    "altitude_headroom",
    "signal_recovery_confidence",
    "terrain_occlusion_level",
    "airspace_deconfliction_status",
    "rules_of_engagement_state",
    "operator_control_latency_budget",
    "mission_replan_budget",
]

CATEGORICAL_VALUES = {
    "battery": ["critical", "low", "medium", "high"],
    "comms": ["lost", "poor", "degraded", "good"],
    "gps": ["lost", "poor", "degraded", "good"],
    "wind": ["low", "medium", "high", "severe"],
    "obstacle_density": ["low", "medium", "high"],
    "threat_level": ["none", "low", "medium", "high"],
    "mission_urgency": ["low", "medium", "high"],
    "payload_criticality": ["low", "medium", "high"],
    "distance_to_home": ["near", "medium", "far"],
    "estimated_energy_margin": ["negative", "tight", "positive"],
    "mission_progress": ["early", "mid", "late"],
    "pilot_takeover_link_quality": ["unavailable", "poor", "degraded", "good"],
    "pilot_response_eta": ["fast", "moderate", "slow"],
    "takeover_window_remaining": ["brief", "limited", "ample"],
    "altitude_headroom": ["limited", "adequate", "ample"],
    "signal_recovery_confidence": ["low", "medium", "high"],
    "terrain_occlusion_level": ["low", "medium", "high"],
    "airspace_deconfliction_status": ["clear", "contested", "denied"],
    "rules_of_engagement_state": ["permissive", "restricted", "hold"],
    "operator_control_latency_budget": ["tight", "adequate", "ample"],
    "mission_replan_budget": ["none", "limited", "ample"],
}


def _is_invalid_dual_outage(features: dict[str, Any]) -> bool:
    if features.get("comms") == "lost" and features.get("gps") == "lost":
        return True
    return False


def _rule_features(**overrides: Any) -> dict[str, Any]:
    features = {
        "distance_to_home": "medium",
        "estimated_energy_margin": "positive",
        "mission_progress": "mid",
        "safe_landing_zone_available": False,
        "autonomous_recovery_allowed": True,
        "pilot_takeover_link_quality": "unavailable",
        "pilot_response_eta": "slow",
        "takeover_window_remaining": "brief",
        "altitude_headroom": "adequate",
        "signal_recovery_confidence": "medium",
        "terrain_occlusion_level": "low",
        "airspace_deconfliction_status": "clear",
        "rules_of_engagement_state": "permissive",
        "operator_control_latency_budget": "tight",
        "mission_replan_budget": "limited",
    }
    features.update(overrides)
    return features


RULES = {
    feature_key(_rule_features(
        battery="high",
        comms="good",
        gps="good",
        wind="low",
        obstacle_density="low",
        threat_level="none",
        mission_urgency="high",
        payload_criticality="high",
    )): ("continue_mission", 0.95),
    feature_key(_rule_features(
        battery="critical",
        comms="good",
        gps="good",
        wind="medium",
        obstacle_density="low",
        threat_level="low",
        mission_urgency="medium",
        payload_criticality="medium",
        distance_to_home="far",
        estimated_energy_margin="negative",
        mission_progress="early",
        signal_recovery_confidence="low",
    )): ("return_to_home", 0.97),
    feature_key(_rule_features(
        battery="medium",
        comms="poor",
        gps="degraded",
        wind="high",
        obstacle_density="high",
        threat_level="medium",
        mission_urgency="high",
        payload_criticality="high",
        estimated_energy_margin="tight",
        safe_landing_zone_available=False,
        pilot_takeover_link_quality="poor",
        altitude_headroom="limited",
        signal_recovery_confidence="low",
        terrain_occlusion_level="medium",
    )): ("hold_position", 0.90),
    feature_key(_rule_features(
        battery="medium",
        comms="good",
        gps="good",
        wind="medium",
        obstacle_density="medium",
        threat_level="high",
        mission_urgency="high",
        payload_criticality="high",
        distance_to_home="far",
        operator_control_latency_budget="adequate",
        mission_replan_budget="ample",
        terrain_occlusion_level="medium",
    )): ("switch_to_low_observable_path", 0.91),
    feature_key(_rule_features(
        battery="low",
        comms="good",
        gps="good",
        wind="medium",
        obstacle_density="low",
        threat_level="low",
        mission_urgency="medium",
        payload_criticality="medium",
        distance_to_home="near",
        estimated_energy_margin="tight",
        mission_progress="late",
    )): ("conserve_battery_mode", 0.88),
    feature_key(_rule_features(
        battery="medium",
        comms="lost",
        gps="good",
        wind="medium",
        obstacle_density="low",
        threat_level="low",
        mission_urgency="medium",
        payload_criticality="medium",
        estimated_energy_margin="tight",
        altitude_headroom="ample",
        signal_recovery_confidence="high",
        terrain_occlusion_level="high",
    )): ("climb_for_signal_recovery", 0.89),
    feature_key(_rule_features(
        battery="medium",
        comms="good",
        gps="poor",
        wind="severe",
        obstacle_density="high",
        threat_level="medium",
        mission_urgency="medium",
        payload_criticality="high",
        estimated_energy_margin="tight",
        safe_landing_zone_available=True,
        autonomous_recovery_allowed=True,
        airspace_deconfliction_status="denied",
        rules_of_engagement_state="hold",
        pilot_takeover_link_quality="poor",
        altitude_headroom="limited",
        signal_recovery_confidence="low",
    )): ("descend_for_safety", 0.92),
    feature_key(_rule_features(
        battery="medium",
        comms="degraded",
        gps="good",
        wind="high",
        obstacle_density="high",
        threat_level="high",
        mission_urgency="high",
        payload_criticality="high",
        safe_landing_zone_available=False,
        autonomous_recovery_allowed=False,
        airspace_deconfliction_status="contested",
        rules_of_engagement_state="restricted",
        operator_control_latency_budget="adequate",
        mission_replan_budget="limited",
        pilot_takeover_link_quality="good",
        altitude_headroom="limited",
        signal_recovery_confidence="low",
        terrain_occlusion_level="medium",
    )): ("manual_handoff", 0.95),
}

EXECUTOR_HANDLERS = {
    "continue_mission": "continue_mission",
    "return_to_home": "return_to_home",
    "hold_position": "hold_position",
    "switch_to_low_observable_path": "switch_to_low_observable_path",
    "conserve_battery_mode": "conserve_battery_mode",
    "climb_for_signal_recovery": "climb_for_signal_recovery",
    "descend_for_safety": "descend_for_safety",
    "manual_handoff": "manual_handoff",
}

CONFIG = DomainConfig(
    name="drone",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="policy",
    reason_actions={"manual_handoff"},
    fallback_action_id="manual_handoff",
    extra_predicate=_is_invalid_dual_outage,
    prototype_max_distance=5.0,
    prototype_raw_distance_floor_ratio=1.0,
    prototype_confidence_masked_distance_weight=0.7,
    semantic_tags={"safe", "battery", "weather", "comms"},
    hybrid_semantic_tags={"safe", "battery", "weather", "comms", "normal", "threat"},
    semantic_min_leaf_count=4,
    semantic_base_confidence=0.90,
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
