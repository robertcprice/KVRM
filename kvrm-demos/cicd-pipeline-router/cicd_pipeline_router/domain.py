from __future__ import annotations

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "branch_type",
    "tests_passing",
    "coverage_delta",
    "dependency_changes",
    "security_scan_status",
    "change_size",
    "deployment_target",
]

CATEGORICAL_VALUES = {
    "branch_type": ["feature", "hotfix", "release", "main"],
    "security_scan_status": ["clean", "warning", "critical"],
    "change_size": ["small", "medium", "large", "xlarge"],
    "deployment_target": ["staging", "canary", "production"],
}

RULES = {
    feature_key({
        "branch_type": "feature",
        "tests_passing": True,
        "coverage_delta": 1.0,
        "dependency_changes": False,
        "security_scan_status": "clean",
        "change_size": "small",
        "deployment_target": "staging",
    }): ("auto_merge", 0.95),
    feature_key({
        "branch_type": "feature",
        "tests_passing": True,
        "coverage_delta": -3.0,
        "dependency_changes": True,
        "security_scan_status": "clean",
        "change_size": "medium",
        "deployment_target": "staging",
    }): ("require_code_review", 0.90),
    feature_key({
        "branch_type": "release",
        "tests_passing": True,
        "coverage_delta": 0.5,
        "dependency_changes": True,
        "security_scan_status": "warning",
        "change_size": "medium",
        "deployment_target": "canary",
    }): ("require_security_review", 0.92),
    feature_key({
        "branch_type": "feature",
        "tests_passing": False,
        "coverage_delta": -10.0,
        "dependency_changes": False,
        "security_scan_status": "clean",
        "change_size": "medium",
        "deployment_target": "staging",
    }): ("block_merge", 0.97),
    feature_key({
        "branch_type": "hotfix",
        "tests_passing": False,
        "coverage_delta": -1.0,
        "dependency_changes": False,
        "security_scan_status": "clean",
        "change_size": "small",
        "deployment_target": "production",
    }): ("auto_rollback", 0.94),
    feature_key({
        "branch_type": "release",
        "tests_passing": True,
        "coverage_delta": 0.0,
        "dependency_changes": False,
        "security_scan_status": "clean",
        "change_size": "large",
        "deployment_target": "production",
    }): ("manual_promotion", 0.88),
    feature_key({
        "branch_type": "main",
        "tests_passing": True,
        "coverage_delta": -2.0,
        "dependency_changes": True,
        "security_scan_status": "warning",
        "change_size": "xlarge",
        "deployment_target": "production",
    }): ("escalate_to_oncall", 0.85),
}

EXECUTOR_HANDLERS = {
    "auto_merge": "continuous_integration",
    "require_code_review": "code_review",
    "require_security_review": "security_review",
    "block_merge": "gate_block",
    "auto_rollback": "rollback",
    "manual_promotion": "release_promotion",
    "escalate_to_oncall": "escalation",
}

CONFIG = DomainConfig(
    name="cicd",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="pipeline",
    executor_include_action_key=True,
    reason_actions={"escalate_to_oncall"},
    fallback_action_id="escalate_to_oncall",
    custom_numeric_keys={"coverage_delta": 200.0},
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
