from __future__ import annotations

from pathlib import Path

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "latency",
    "error_rate",
    "deployment_recency",
    "dependency_health",
    "region_health",
    "saturation",
    "replication_lag",
    "write_path_available",
    "fault_scope",
    "node_locality_score",
    "replica_skew",
    "recent_restart_attempts",
    "failover_ready",
    "secondary_capacity_ready",
    "automation_policy_permits_failover",
    "operator_approval_required",
    "operator_response_eta",
    "mitigation_window_remaining",
    "quorum_health",
    "cross_region_read_staleness",
    "control_plane_availability",
    "runbook_coordination_required",
    "deploy_regression_suspected",
    "rollback_safe",
    "capacity_headroom",
    "change_failure_blast_radius",
    "telemetry_confidence",
]

CATEGORICAL_VALUES = {
    "latency": ["normal", "elevated", "high", "severe", "extreme"],
    "error_rate": ["normal", "elevated", "high", "severe"],
    "deployment_recency": ["stale", "recent", "fresh"],
    "dependency_health": ["healthy", "degraded", "failing"],
    "region_health": ["healthy", "degraded", "failing"],
    "saturation": ["normal", "high", "critical"],
    "replication_lag": ["low", "moderate", "high"],
    "fault_scope": ["service", "node", "region"],
    "capacity_headroom": ["low", "moderate", "high"],
    "change_failure_blast_radius": ["service", "node", "cluster", "region"],
    "telemetry_confidence": ["low", "medium", "high"],
    "operator_response_eta": ["fast", "moderate", "slow"],
    "mitigation_window_remaining": ["brief", "limited", "ample"],
    "quorum_health": ["healthy", "degraded", "lost"],
    "cross_region_read_staleness": ["low", "elevated", "high"],
    "control_plane_availability": ["available", "degraded", "unavailable"],
}

NUMERIC_FEATURE_RANGES = {
    "node_locality_score": (0.0, 1.0),
    "replica_skew": (0.0, 1.0),
    "recent_restart_attempts": (0.0, 5.0),
}


def _resolve_registry_path(cases_path: str | Path) -> Path:
    """SRE-specific legacy resolver for v4 data packs that still use registry_v4.json."""
    cases_path = Path(cases_path)
    if "_v4" in cases_path.name:
        candidate = cases_path.with_name("registry_v4.json")
        if candidate.exists():
            return candidate
    return cases_path.with_name("registry.json")


RULES = {
    feature_key({"latency": "high", "error_rate": "high", "deployment_recency": "fresh", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}): ("rollback_deploy", 0.96),
    feature_key({"latency": "severe", "error_rate": "severe", "deployment_recency": "stale", "dependency_health": "failing", "region_health": "failing", "saturation": "critical", "replication_lag": "high", "write_path_available": False}): ("failover_region", 0.99),
    feature_key({"latency": "high", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "critical", "replication_lag": "moderate", "write_path_available": True}): ("scale_out", 0.90),
    feature_key({"latency": "elevated", "error_rate": "high", "deployment_recency": "stale", "dependency_health": "degraded", "region_health": "healthy", "saturation": "high", "replication_lag": "moderate", "write_path_available": True}): ("restart_service", 0.86),
    feature_key({"latency": "elevated", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "degraded", "region_health": "healthy", "saturation": "normal", "replication_lag": "moderate", "write_path_available": True}): ("drain_node", 0.80),
    feature_key({"latency": "high", "error_rate": "high", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "high", "replication_lag": "high", "write_path_available": False}): ("enable_readonly_mode", 0.88),
    feature_key({"latency": "elevated", "error_rate": "normal", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}): ("gather_more_telemetry", 0.77),
}

EXECUTOR_HANDLERS = {
    "restart_service": "restart_service",
    "failover_region": "failover_region",
    "scale_out": "scale_out",
    "drain_node": "drain_node",
    "rollback_deploy": "rollback_deploy",
    "enable_readonly_mode": "enable_readonly_mode",
    "gather_more_telemetry": "gather_more_telemetry",
    "page_human_operator": "page_human_operator",
}

CONFIG = DomainConfig(
    name="sre",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    reason_actions={"page_human_operator"},
    fallback_action_id="page_human_operator",
    numeric_feature_ranges=NUMERIC_FEATURE_RANGES,
    registry_resolver=_resolve_registry_path,
    semantic_tags={"safety", "capacity", "service"},
    semantic_min_leaf_count=6,
    semantic_base_confidence=0.78,
    semantic_per_leaf_bonus=0.03,
    semantic_max_confidence=0.96,
    learned_min_confidence=0.42,
    learned_candidate_floor=0.18,
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
