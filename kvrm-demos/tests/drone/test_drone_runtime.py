from __future__ import annotations

from pathlib import Path

from kvrm_bench.ceiling import load_cases, support_overlap_cases
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.types import DecisionInput, FinalStatus
from kvrm_core.validation import DeterministicValidator
from drone_mission_router import build_executor
from drone_mission_router import build_rule_selector, build_retrieval_selector, build_prototype_selector, build_hybrid_selector

ROOT = Path(__file__).resolve().parents[2] / 'drone-mission-router'
REGISTRY_PATH = ROOT / 'data' / 'registry.json'
TRAIN_CASES_PATH = ROOT / 'data' / 'train_cases.jsonl'


def _drone_features(**overrides):
    features = {
        'airspace_deconfliction_status': 'clear',
        'rules_of_engagement_state': 'permissive',
        'operator_control_latency_budget': 'tight',
        'mission_replan_budget': 'limited',
        'pilot_response_eta': 'slow',
        'takeover_window_remaining': 'brief',
    }
    features.update(overrides)
    return features


def test_rule_selector_routes_critical_battery_case():
    selector = build_rule_selector()
    result = selector.select(DecisionInput(case_id='x', features=_drone_features(**{
        'battery': 'critical', 'comms': 'good', 'gps': 'good', 'wind': 'medium', 'obstacle_density': 'low', 'threat_level': 'low', 'mission_urgency': 'medium', 'payload_criticality': 'medium',
        'distance_to_home': 'far', 'estimated_energy_margin': 'negative', 'mission_progress': 'early', 'safe_landing_zone_available': False, 'autonomous_recovery_allowed': True, 'pilot_takeover_link_quality': 'unavailable', 'altitude_headroom': 'adequate', 'signal_recovery_confidence': 'low', 'terrain_occlusion_level': 'low',
    })))
    assert result[0].action_id == 'return_to_home'


def test_prototype_selector_generalizes_supported_ood_case():
    selector = build_prototype_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='ood', features=_drone_features(**{
        'battery': 'low', 'comms': 'good', 'gps': 'good', 'wind': 'medium', 'obstacle_density': 'medium', 'threat_level': 'low', 'mission_urgency': 'high', 'payload_criticality': 'medium',
        'distance_to_home': 'near', 'estimated_energy_margin': 'tight', 'mission_progress': 'late', 'safe_landing_zone_available': False, 'autonomous_recovery_allowed': True, 'pilot_takeover_link_quality': 'unavailable', 'altitude_headroom': 'adequate', 'signal_recovery_confidence': 'medium', 'terrain_occlusion_level': 'low',
    })))
    assert result[0].action_id == 'conserve_battery_mode'
    assert result[0].confidence >= 0.6


def test_hybrid_selector_uses_prototype_for_supported_ood_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='ood', features=_drone_features(**{
        'battery': 'low', 'comms': 'good', 'gps': 'good', 'wind': 'medium', 'obstacle_density': 'medium', 'threat_level': 'low', 'mission_urgency': 'high', 'payload_criticality': 'medium',
        'distance_to_home': 'near', 'estimated_energy_margin': 'tight', 'mission_progress': 'late', 'safe_landing_zone_available': False, 'autonomous_recovery_allowed': True, 'pilot_takeover_link_quality': 'unavailable', 'altitude_headroom': 'adequate', 'signal_recovery_confidence': 'medium', 'terrain_occlusion_level': 'low',
    })))
    assert result[0].action_id == 'conserve_battery_mode'
    assert any(label in result[0].source for label in ('prototype', 'semantic'))


def test_hybrid_selector_routes_supported_manual_handoff_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='manual_supported', features=_drone_features(**{
        'battery': 'medium',
        'comms': 'degraded',
        'gps': 'degraded',
        'wind': 'high',
        'obstacle_density': 'high',
        'threat_level': 'high',
        'mission_urgency': 'high',
        'payload_criticality': 'high',
        'distance_to_home': 'medium',
        'estimated_energy_margin': 'positive',
        'mission_progress': 'mid',
        'mission_replan_budget': 'limited',
        'safe_landing_zone_available': False,
        'airspace_deconfliction_status': 'contested',
        'rules_of_engagement_state': 'restricted',
        'operator_control_latency_budget': 'adequate',
        'autonomous_recovery_allowed': False,
        'pilot_takeover_link_quality': 'good',
        'pilot_response_eta': 'fast',
        'takeover_window_remaining': 'ample',
        'altitude_headroom': 'limited',
        'signal_recovery_confidence': 'low',
        'terrain_occlusion_level': 'medium',
    })))
    assert result[0].action_id == 'manual_handoff'


def test_hybrid_selector_prefers_climb_when_recovery_confidence_is_high():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='climb_supported', features=_drone_features(**{
        'battery': 'high',
        'comms': 'degraded',
        'gps': 'good',
        'wind': 'high',
        'obstacle_density': 'low',
        'threat_level': 'low',
        'mission_urgency': 'medium',
        'payload_criticality': 'medium',
        'distance_to_home': 'medium',
        'estimated_energy_margin': 'positive',
        'mission_progress': 'mid',
        'safe_landing_zone_available': False,
        'autonomous_recovery_allowed': True,
        'pilot_takeover_link_quality': 'unavailable',
        'altitude_headroom': 'ample',
        'signal_recovery_confidence': 'high',
        'terrain_occlusion_level': 'high',
    })))
    assert result[0].action_id == 'climb_for_signal_recovery'


def test_hybrid_selector_prefers_descend_when_safe_landing_is_available():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='descend_supported', features=_drone_features(**{
        'battery': 'high',
        'comms': 'degraded',
        'gps': 'poor',
        'wind': 'severe',
        'obstacle_density': 'high',
        'threat_level': 'low',
        'mission_urgency': 'medium',
        'payload_criticality': 'high',
        'distance_to_home': 'medium',
        'estimated_energy_margin': 'positive',
        'mission_progress': 'mid',
        'mission_replan_budget': 'none',
        'safe_landing_zone_available': True,
        'airspace_deconfliction_status': 'denied',
        'rules_of_engagement_state': 'hold',
        'autonomous_recovery_allowed': True,
        'pilot_takeover_link_quality': 'poor',
        'altitude_headroom': 'limited',
        'signal_recovery_confidence': 'low',
        'terrain_occlusion_level': 'low',
    })))
    assert result[0].action_id == 'descend_for_safety'


def test_drone_registry_has_no_supported_overlap_cases():
    registry = load_registry(REGISTRY_PATH)
    cases = load_cases(ROOT / 'data' / 'cases.jsonl')
    assert support_overlap_cases(registry, cases, supported_only=True) == []


def test_runtime_falls_back_for_unsupported_case():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(registry, build_rule_selector(), DeterministicValidator(registry), build_executor(), threshold=0.8, fallback_action_id='manual_handoff')
    result = runtime.decide_and_execute(DecisionInput(case_id='unsupported', features=_drone_features(**{
        'battery': 'critical', 'comms': 'lost', 'gps': 'lost', 'wind': 'severe', 'obstacle_density': 'high', 'threat_level': 'high', 'mission_urgency': 'high', 'payload_criticality': 'high',
        'distance_to_home': 'far', 'estimated_energy_margin': 'negative', 'mission_progress': 'early', 'safe_landing_zone_available': False, 'autonomous_recovery_allowed': False, 'pilot_takeover_link_quality': 'unavailable', 'altitude_headroom': 'limited', 'signal_recovery_confidence': 'low', 'terrain_occlusion_level': 'high',
    }), supported=False, ood=True))
    assert result.final_status in {FinalStatus.FALLBACK_EXECUTED, FinalStatus.FAIL_CLOSED}


def test_hybrid_selector_routes_return_to_home_on_critical_battery_transition():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='return_transition_from_continue', features=_drone_features(**{
        'altitude_headroom': 'adequate',
        'autonomous_recovery_allowed': True,
        'battery': 'critical',
        'comms': 'good',
        'distance_to_home': 'medium',
        'estimated_energy_margin': 'positive',
        'gps': 'good',
        'mission_progress': 'mid',
        'mission_urgency': 'high',
        'obstacle_density': 'medium',
        'payload_criticality': 'medium',
        'pilot_takeover_link_quality': 'unavailable',
        'safe_landing_zone_available': False,
        'signal_recovery_confidence': 'medium',
        'terrain_occlusion_level': 'low',
        'threat_level': 'low',
        'wind': 'medium',
    })))
    assert result[0].action_id == 'return_to_home'
    assert 'semantic' in result[0].source


def test_hybrid_selector_routes_return_to_home_from_signal_recovery_state():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='return_transition_from_climb', features=_drone_features(**{
        'altitude_headroom': 'ample',
        'autonomous_recovery_allowed': True,
        'battery': 'critical',
        'comms': 'degraded',
        'distance_to_home': 'medium',
        'estimated_energy_margin': 'positive',
        'gps': 'good',
        'mission_progress': 'mid',
        'mission_urgency': 'medium',
        'obstacle_density': 'medium',
        'payload_criticality': 'low',
        'pilot_takeover_link_quality': 'unavailable',
        'safe_landing_zone_available': False,
        'signal_recovery_confidence': 'medium',
        'terrain_occlusion_level': 'medium',
        'threat_level': 'low',
        'wind': 'medium',
    })))
    assert result[0].action_id == 'return_to_home'
    assert 'semantic' in result[0].source


def test_hybrid_selector_routes_continue_mission_on_energy_recovery_boundary():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='continue_transition_from_energy_return', features=_drone_features(**{
        'altitude_headroom': 'adequate',
        'autonomous_recovery_allowed': True,
        'battery': 'high',
        'comms': 'good',
        'distance_to_home': 'far',
        'estimated_energy_margin': 'negative',
        'gps': 'good',
        'mission_progress': 'early',
        'mission_replan_budget': 'none',
        'mission_urgency': 'low',
        'obstacle_density': 'medium',
        'operator_control_latency_budget': 'tight',
        'payload_criticality': 'low',
        'pilot_response_eta': 'slow',
        'pilot_takeover_link_quality': 'unavailable',
        'rules_of_engagement_state': 'permissive',
        'safe_landing_zone_available': False,
        'signal_recovery_confidence': 'low',
        'takeover_window_remaining': 'brief',
        'terrain_occlusion_level': 'low',
        'threat_level': 'low',
        'wind': 'medium',
    })))
    assert result[0].action_id == 'continue_mission'
    assert 'semantic' in result[0].source


def test_runtime_fail_closes_when_manual_handoff_eta_is_too_slow():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(
        registry,
        build_hybrid_selector(TRAIN_CASES_PATH),
        DeterministicValidator(registry),
        build_executor(),
        threshold=0.60,
        fallback_action_id='manual_handoff',
    )
    result = runtime.decide_and_execute(DecisionInput(case_id='manual_eta_blocked', features=_drone_features(
        airspace_deconfliction_status='contested',
        altitude_headroom='limited',
        autonomous_recovery_allowed=False,
        battery='medium',
        comms='degraded',
        distance_to_home='medium',
        estimated_energy_margin='positive',
        gps='degraded',
        mission_progress='mid',
        mission_replan_budget='limited',
        mission_urgency='high',
        obstacle_density='high',
        operator_control_latency_budget='adequate',
        payload_criticality='high',
        pilot_takeover_link_quality='good',
        pilot_response_eta='slow',
        rules_of_engagement_state='restricted',
        safe_landing_zone_available=False,
        signal_recovery_confidence='low',
        takeover_window_remaining='ample',
        terrain_occlusion_level='medium',
        threat_level='high',
        wind='high',
    ), supported=False, ood=True))
    assert result.final_status == FinalStatus.FAIL_CLOSED
    assert result.selected_action_id == 'manual_handoff'


def test_hybrid_selector_rejects_low_observable_path_when_airspace_is_denied():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='low_observable_denied', features=_drone_features(**{
        'airspace_deconfliction_status': 'denied',
        'battery': 'high',
        'comms': 'good',
        'gps': 'good',
        'wind': 'medium',
        'obstacle_density': 'medium',
        'threat_level': 'high',
        'mission_urgency': 'high',
        'payload_criticality': 'high',
        'distance_to_home': 'far',
        'estimated_energy_margin': 'positive',
        'mission_progress': 'mid',
        'mission_replan_budget': 'ample',
        'safe_landing_zone_available': False,
        'autonomous_recovery_allowed': True,
        'pilot_takeover_link_quality': 'unavailable',
        'operator_control_latency_budget': 'adequate',
        'altitude_headroom': 'adequate',
        'signal_recovery_confidence': 'medium',
        'terrain_occlusion_level': 'medium',
    })))
    assert result[0].action_id == 'manual_handoff'
    assert result[0].evidence.get('support_gate') in {'fallback_action', 'unsupported_context', 'support_gate_exhausted'}


def test_runtime_fail_closes_when_manual_handoff_control_budget_is_too_tight():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(
        registry,
        build_hybrid_selector(TRAIN_CASES_PATH),
        DeterministicValidator(registry),
        build_executor(),
        threshold=0.60,
        fallback_action_id='manual_handoff',
    )
    result = runtime.decide_and_execute(DecisionInput(case_id='manual_control_budget_blocked', features=_drone_features(
        airspace_deconfliction_status='contested',
        altitude_headroom='limited',
        autonomous_recovery_allowed=False,
        battery='medium',
        comms='degraded',
        distance_to_home='medium',
        estimated_energy_margin='positive',
        gps='degraded',
        mission_progress='mid',
        mission_replan_budget='limited',
        mission_urgency='high',
        obstacle_density='high',
        operator_control_latency_budget='tight',
        payload_criticality='high',
        pilot_takeover_link_quality='good',
        pilot_response_eta='fast',
        rules_of_engagement_state='restricted',
        safe_landing_zone_available=False,
        signal_recovery_confidence='low',
        takeover_window_remaining='ample',
        terrain_occlusion_level='medium',
        threat_level='high',
        wind='high',
    ), supported=False, ood=True))
    assert result.final_status == FinalStatus.FAIL_CLOSED
    assert result.selected_action_id == 'manual_handoff'
