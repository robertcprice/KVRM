from __future__ import annotations

from pathlib import Path

from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.types import DecisionInput, FinalStatus
from kvrm_core.validation import DeterministicValidator
from kvrm_bench.ceiling import load_cases, support_overlap_cases
from sre_policy_router import build_executor
from sre_policy_router import build_rule_selector, build_retrieval_selector, build_prototype_selector, build_hybrid_selector

ROOT = Path(__file__).resolve().parents[2] / 'sre-policy-router'
REGISTRY_PATH = ROOT / 'data' / 'registry.json'
TRAIN_CASES_PATH = ROOT / 'data' / 'train_cases.jsonl'

def _sre_features(**overrides):
    features = {
        'quorum_health': 'healthy',
        'cross_region_read_staleness': 'low',
        'control_plane_availability': 'available',
        'runbook_coordination_required': False,
    }
    features.update(overrides)
    return features


SCALE_OUT_OOD_FEATURES = _sre_features(**{
    'latency': 'high',
    'error_rate': 'elevated',
    'deployment_recency': 'stale',
    'dependency_health': 'healthy',
    'region_health': 'healthy',
    'saturation': 'critical',
    'replication_lag': 'moderate',
    'write_path_available': True,
    'fault_scope': 'service',
    'node_locality_score': 0.33,
    'replica_skew': 0.18,
    'recent_restart_attempts': 0.0,
    'failover_ready': False,
    'secondary_capacity_ready': False,
    'automation_policy_permits_failover': False,
    'operator_approval_required': False,
    'operator_response_eta': 'slow',
    'mitigation_window_remaining': 'brief',
    'deploy_regression_suspected': False,
    'rollback_safe': False,
    'capacity_headroom': 'low',
    'change_failure_blast_radius': 'service',
    'telemetry_confidence': 'high',
})

DRAIN_NODE_OOD_FEATURES = _sre_features(**{
    'latency': 'elevated',
    'error_rate': 'elevated',
    'deployment_recency': 'stale',
    'dependency_health': 'degraded',
    'region_health': 'healthy',
    'saturation': 'normal',
    'replication_lag': 'moderate',
    'write_path_available': True,
    'fault_scope': 'node',
    'node_locality_score': 0.92,
    'replica_skew': 0.88,
    'recent_restart_attempts': 1.0,
    'failover_ready': False,
    'secondary_capacity_ready': False,
    'automation_policy_permits_failover': False,
    'operator_approval_required': False,
    'operator_response_eta': 'slow',
    'mitigation_window_remaining': 'brief',
    'deploy_regression_suspected': False,
    'rollback_safe': False,
    'capacity_headroom': 'moderate',
    'change_failure_blast_radius': 'node',
    'telemetry_confidence': 'high',
})

TELEMETRY_OOD_FEATURES = _sre_features(**{
    'latency': 'elevated',
    'error_rate': 'normal',
    'deployment_recency': 'stale',
    'dependency_health': 'healthy',
    'region_health': 'healthy',
    'saturation': 'normal',
    'replication_lag': 'low',
    'write_path_available': True,
    'fault_scope': 'service',
    'node_locality_score': 0.2,
    'replica_skew': 0.28,
    'recent_restart_attempts': 0.0,
    'failover_ready': False,
    'secondary_capacity_ready': False,
    'automation_policy_permits_failover': False,
    'operator_approval_required': False,
    'operator_response_eta': 'slow',
    'mitigation_window_remaining': 'brief',
    'deploy_regression_suspected': False,
    'rollback_safe': False,
    'capacity_headroom': 'high',
    'change_failure_blast_radius': 'service',
    'telemetry_confidence': 'medium',
})

READONLY_OOD_FEATURES = _sre_features(**{
    'latency': 'high',
    'error_rate': 'high',
    'deployment_recency': 'stale',
    'dependency_health': 'healthy',
    'region_health': 'degraded',
    'saturation': 'high',
    'replication_lag': 'high',
    'write_path_available': False,
    'fault_scope': 'service',
    'node_locality_score': 0.25,
    'replica_skew': 0.22,
    'recent_restart_attempts': 1.0,
    'failover_ready': False,
    'secondary_capacity_ready': False,
    'automation_policy_permits_failover': False,
    'operator_approval_required': False,
    'operator_response_eta': 'slow',
    'mitigation_window_remaining': 'brief',
    'quorum_health': 'degraded',
    'cross_region_read_staleness': 'high',
    'control_plane_availability': 'degraded',
    'runbook_coordination_required': False,
    'deploy_regression_suspected': False,
    'rollback_safe': False,
    'capacity_headroom': 'low',
    'change_failure_blast_radius': 'cluster',
    'telemetry_confidence': 'high',
})

CONFLICTING_SKEW_UNSUPPORTED_FEATURES = _sre_features(**{
    'latency': 'high',
    'error_rate': 'high',
    'deployment_recency': 'stale',
    'dependency_health': 'degraded',
    'region_health': 'degraded',
    'saturation': 'high',
    'replication_lag': 'high',
    'write_path_available': False,
    'fault_scope': 'service',
    'node_locality_score': 0.30,
    'replica_skew': 0.86,
    'recent_restart_attempts': 1.0,
    'failover_ready': False,
    'secondary_capacity_ready': False,
    'automation_policy_permits_failover': False,
    'operator_approval_required': False,
    'operator_response_eta': 'slow',
    'mitigation_window_remaining': 'brief',
    'deploy_regression_suspected': False,
    'rollback_safe': False,
    'capacity_headroom': 'low',
    'change_failure_blast_radius': 'cluster',
    'telemetry_confidence': 'high',
})


def test_rule_selector_routes_bad_deploy_case():
    selector = build_rule_selector()
    result = selector.select(DecisionInput(case_id='x', features={
        'latency': 'high', 'error_rate': 'high', 'deployment_recency': 'fresh', 'dependency_health': 'healthy', 'region_health': 'healthy', 'saturation': 'normal', 'replication_lag': 'low', 'write_path_available': True,
    }))
    assert result[0].action_id == 'rollback_deploy'


def test_prototype_selector_generalizes_supported_ood_case():
    selector = build_prototype_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='ood', features=SCALE_OUT_OOD_FEATURES))
    assert result[0].action_id == 'scale_out'
    assert result[0].confidence >= 0.9


def test_hybrid_selector_uses_prototype_for_supported_ood_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='ood', features=SCALE_OUT_OOD_FEATURES))
    assert result[0].action_id == 'scale_out'
    assert any(label in result[0].source for label in ('prototype', 'semantic'))


def test_hybrid_selector_routes_supported_drain_node_overlap_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='drain_supported', features=DRAIN_NODE_OOD_FEATURES))
    assert result[0].action_id == 'drain_node'
    assert 'prototype' in result[0].source


def test_hybrid_selector_routes_stable_telemetry_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='telemetry_supported', features=TELEMETRY_OOD_FEATURES))
    assert result[0].action_id == 'gather_more_telemetry'
    assert 'prototype' in result[0].source


def test_hybrid_selector_emits_semantic_readonly_candidate():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='readonly_supported', features=READONLY_OOD_FEATURES))
    assert result[0].action_id == 'enable_readonly_mode'
    assert 'semantic' in result[0].source


def test_runtime_falls_back_for_unsupported_case():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(registry, build_rule_selector(), DeterministicValidator(registry), build_executor(), threshold=0.8, fallback_action_id='page_human_operator')
    result = runtime.decide_and_execute(DecisionInput(case_id='unsupported', features=_sre_features(**{
        'latency': 'normal', 'error_rate': 'normal', 'deployment_recency': 'fresh', 'dependency_health': 'healthy', 'region_health': 'healthy', 'saturation': 'normal', 'replication_lag': 'low', 'write_path_available': True,
    }), supported=False, ood=True))
    assert result.final_status in {FinalStatus.FALLBACK_EXECUTED, FinalStatus.FAIL_CLOSED}


def test_sre_registry_has_no_supported_overlap_cases():
    registry = load_registry(REGISTRY_PATH)
    cases = load_cases(ROOT / 'data' / 'cases.jsonl')
    assert support_overlap_cases(registry, cases, supported_only=True) == []


def test_hybrid_selector_routes_failover_when_policy_allows_it():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='failover_v4', features=_sre_features(**{
        'latency': 'severe',
        'error_rate': 'severe',
        'deployment_recency': 'stale',
        'dependency_health': 'failing',
        'region_health': 'failing',
        'saturation': 'critical',
        'replication_lag': 'high',
        'write_path_available': False,
        'fault_scope': 'region',
        'node_locality_score': 0.10,
        'replica_skew': 0.18,
        'recent_restart_attempts': 2.0,
        'failover_ready': True,
        'secondary_capacity_ready': True,
        'automation_policy_permits_failover': True,
        'operator_approval_required': False,
        'operator_response_eta': 'slow',
        'mitigation_window_remaining': 'brief',
        'quorum_health': 'degraded',
        'cross_region_read_staleness': 'elevated',
        'control_plane_availability': 'available',
        'runbook_coordination_required': False,
        'deploy_regression_suspected': False,
        'rollback_safe': False,
        'capacity_headroom': 'high',
        'change_failure_blast_radius': 'region',
        'telemetry_confidence': 'high',
    })))
    assert result[0].action_id == 'failover_region'


def test_hybrid_selector_keeps_restart_service_case_with_write_path_loss():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='restart_v4', features=_sre_features(**{
        'latency': 'high',
        'error_rate': 'high',
        'deployment_recency': 'stale',
        'dependency_health': 'degraded',
        'region_health': 'healthy',
        'saturation': 'high',
        'replication_lag': 'moderate',
        'write_path_available': False,
        'fault_scope': 'service',
        'node_locality_score': 0.20,
        'replica_skew': 0.52,
        'recent_restart_attempts': 0.0,
        'failover_ready': False,
        'secondary_capacity_ready': False,
        'automation_policy_permits_failover': False,
        'operator_approval_required': False,
        'operator_response_eta': 'slow',
        'mitigation_window_remaining': 'brief',
        'deploy_regression_suspected': False,
        'rollback_safe': False,
        'capacity_headroom': 'moderate',
        'change_failure_blast_radius': 'service',
        'telemetry_confidence': 'high',
    })))
    assert result[0].action_id == 'restart_service'


def test_hybrid_selector_rejects_conflicting_replica_skew_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='conflicting_skew', features=CONFLICTING_SKEW_UNSUPPORTED_FEATURES))
    assert result[0].action_id == 'page_human_operator'
    assert result[0].evidence.get('support_gate') in {'fallback_action', 'unsupported_context', 'support_gate_exhausted'}


def test_hybrid_selector_routes_handoff_when_failover_is_blocked():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='handoff_v4', features=_sre_features(**{
        'latency': 'severe',
        'error_rate': 'severe',
        'deployment_recency': 'stale',
        'dependency_health': 'failing',
        'region_health': 'degraded',
        'saturation': 'critical',
        'replication_lag': 'high',
        'write_path_available': True,
        'fault_scope': 'region',
        'node_locality_score': 0.10,
        'replica_skew': 0.60,
        'recent_restart_attempts': 3.0,
        'failover_ready': False,
        'secondary_capacity_ready': False,
        'automation_policy_permits_failover': False,
        'operator_approval_required': True,
        'operator_response_eta': 'fast',
        'mitigation_window_remaining': 'ample',
        'quorum_health': 'lost',
        'cross_region_read_staleness': 'high',
        'control_plane_availability': 'unavailable',
        'runbook_coordination_required': True,
        'deploy_regression_suspected': False,
        'rollback_safe': False,
        'capacity_headroom': 'low',
        'change_failure_blast_radius': 'region',
        'telemetry_confidence': 'high',
    })))
    assert result[0].action_id == 'page_human_operator'


def test_hybrid_selector_routes_scale_out_when_write_path_recovers():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='scale_out_transition', features=_sre_features(**{
        'automation_policy_permits_failover': False,
        'capacity_headroom': 'low',
        'change_failure_blast_radius': 'cluster',
        'dependency_health': 'healthy',
        'deploy_regression_suspected': False,
        'deployment_recency': 'stale',
        'error_rate': 'high',
        'failover_ready': False,
        'fault_scope': 'service',
        'latency': 'high',
        'node_locality_score': 0.25,
        'operator_approval_required': False,
        'operator_response_eta': 'slow',
        'mitigation_window_remaining': 'brief',
        'recent_restart_attempts': 1.0,
        'region_health': 'healthy',
        'replica_skew': 0.22,
        'replication_lag': 'high',
        'rollback_safe': False,
        'saturation': 'high',
        'secondary_capacity_ready': False,
        'telemetry_confidence': 'high',
        'write_path_available': True,
    })))
    assert result[0].action_id == 'scale_out'
    assert 'semantic' in result[0].source


def test_hybrid_selector_routes_restart_service_when_replica_skew_crosses_boundary():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='restart_transition', features=_sre_features(**{
        'automation_policy_permits_failover': False,
        'capacity_headroom': 'low',
        'change_failure_blast_radius': 'cluster',
        'dependency_health': 'degraded',
        'deploy_regression_suspected': False,
        'deployment_recency': 'stale',
        'error_rate': 'high',
        'failover_ready': False,
        'fault_scope': 'service',
        'latency': 'high',
        'node_locality_score': 0.25,
        'operator_approval_required': False,
        'operator_response_eta': 'slow',
        'mitigation_window_remaining': 'brief',
        'recent_restart_attempts': 1.0,
        'region_health': 'degraded',
        'replica_skew': 0.4,
        'replication_lag': 'high',
        'rollback_safe': False,
        'saturation': 'high',
        'secondary_capacity_ready': False,
        'telemetry_confidence': 'high',
        'write_path_available': False,
    })))
    assert result[0].action_id == 'restart_service'
    assert 'semantic' in result[0].source


def test_runtime_fail_closes_when_handoff_eta_is_too_slow():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(
        registry,
        build_hybrid_selector(TRAIN_CASES_PATH),
        DeterministicValidator(registry),
        build_executor(),
        threshold=0.60,
        fallback_action_id='page_human_operator',
    )
    result = runtime.decide_and_execute(DecisionInput(case_id='handoff_eta_blocked', features=_sre_features(**{
        'latency': 'severe',
        'error_rate': 'severe',
        'deployment_recency': 'stale',
        'dependency_health': 'failing',
        'region_health': 'degraded',
        'saturation': 'critical',
        'replication_lag': 'high',
        'write_path_available': True,
        'fault_scope': 'region',
        'node_locality_score': 0.10,
        'replica_skew': 0.60,
        'recent_restart_attempts': 3.0,
        'failover_ready': False,
        'secondary_capacity_ready': False,
        'automation_policy_permits_failover': False,
        'operator_approval_required': True,
        'operator_response_eta': 'slow',
        'mitigation_window_remaining': 'ample',
        'quorum_health': 'lost',
        'cross_region_read_staleness': 'high',
        'control_plane_availability': 'unavailable',
        'runbook_coordination_required': True,
        'deploy_regression_suspected': False,
        'rollback_safe': False,
        'capacity_headroom': 'low',
        'change_failure_blast_radius': 'region',
        'telemetry_confidence': 'high',
    }), supported=False, ood=True))
    assert result.final_status == FinalStatus.FAIL_CLOSED
    assert result.selected_action_id == 'page_human_operator'


def test_hybrid_selector_rejects_failover_when_control_plane_is_unavailable():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='failover_control_plane_blocked', features=_sre_features(**{
        'latency': 'severe',
        'error_rate': 'severe',
        'deployment_recency': 'stale',
        'dependency_health': 'failing',
        'region_health': 'failing',
        'saturation': 'critical',
        'replication_lag': 'high',
        'write_path_available': False,
        'fault_scope': 'region',
        'node_locality_score': 0.08,
        'replica_skew': 0.24,
        'recent_restart_attempts': 2.0,
        'failover_ready': True,
        'secondary_capacity_ready': True,
        'automation_policy_permits_failover': True,
        'operator_approval_required': False,
        'operator_response_eta': 'slow',
        'mitigation_window_remaining': 'brief',
        'quorum_health': 'degraded',
        'cross_region_read_staleness': 'elevated',
        'control_plane_availability': 'unavailable',
        'runbook_coordination_required': False,
        'deploy_regression_suspected': False,
        'rollback_safe': False,
        'capacity_headroom': 'high',
        'change_failure_blast_radius': 'region',
        'telemetry_confidence': 'high',
    })))
    assert result[0].action_id == 'page_human_operator'
    assert result[0].evidence.get('support_gate') in {'fallback_action', 'unsupported_context', 'support_gate_exhausted'}
