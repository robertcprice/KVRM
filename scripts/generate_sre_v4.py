from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "kvrm-demos" / "sre-policy-router" / "data"
RESULTS_DIR = REPO_ROOT / "kvrm-bench" / "results"


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def base_v4_features(action_id: str | None) -> dict[str, object]:
    if action_id == "restart_service":
        return {
            "fault_scope": "service",
            "node_locality_score": 0.20,
            "recent_restart_attempts": 0.0,
            "failover_ready": False,
            "secondary_capacity_ready": False,
            "automation_policy_permits_failover": False,
            "operator_approval_required": False,
            "deploy_regression_suspected": False,
            "rollback_safe": False,
            "capacity_headroom": "moderate",
            "change_failure_blast_radius": "service",
            "telemetry_confidence": "high",
        }
    if action_id == "failover_region":
        return {
            "fault_scope": "region",
            "node_locality_score": 0.10,
            "recent_restart_attempts": 2.0,
            "failover_ready": True,
            "secondary_capacity_ready": True,
            "automation_policy_permits_failover": True,
            "operator_approval_required": False,
            "deploy_regression_suspected": False,
            "rollback_safe": False,
            "capacity_headroom": "high",
            "change_failure_blast_radius": "region",
            "telemetry_confidence": "high",
        }
    if action_id == "scale_out":
        return {
            "fault_scope": "service",
            "node_locality_score": 0.15,
            "recent_restart_attempts": 0.0,
            "failover_ready": False,
            "secondary_capacity_ready": False,
            "automation_policy_permits_failover": False,
            "operator_approval_required": False,
            "deploy_regression_suspected": False,
            "rollback_safe": False,
            "capacity_headroom": "low",
            "change_failure_blast_radius": "service",
            "telemetry_confidence": "high",
        }
    if action_id == "drain_node":
        return {
            "fault_scope": "node",
            "node_locality_score": 0.92,
            "recent_restart_attempts": 0.0,
            "failover_ready": False,
            "secondary_capacity_ready": False,
            "automation_policy_permits_failover": False,
            "operator_approval_required": False,
            "deploy_regression_suspected": False,
            "rollback_safe": False,
            "capacity_headroom": "moderate",
            "change_failure_blast_radius": "node",
            "telemetry_confidence": "high",
        }
    if action_id == "rollback_deploy":
        return {
            "fault_scope": "service",
            "node_locality_score": 0.18,
            "recent_restart_attempts": 0.0,
            "failover_ready": False,
            "secondary_capacity_ready": False,
            "automation_policy_permits_failover": False,
            "operator_approval_required": False,
            "deploy_regression_suspected": True,
            "rollback_safe": True,
            "capacity_headroom": "moderate",
            "change_failure_blast_radius": "cluster",
            "telemetry_confidence": "high",
        }
    if action_id == "enable_readonly_mode":
        return {
            "fault_scope": "service",
            "node_locality_score": 0.25,
            "recent_restart_attempts": 1.0,
            "failover_ready": False,
            "secondary_capacity_ready": False,
            "automation_policy_permits_failover": False,
            "operator_approval_required": False,
            "deploy_regression_suspected": False,
            "rollback_safe": False,
            "capacity_headroom": "low",
            "change_failure_blast_radius": "cluster",
            "telemetry_confidence": "high",
        }
    if action_id == "gather_more_telemetry":
        return {
            "fault_scope": "service",
            "node_locality_score": 0.20,
            "recent_restart_attempts": 0.0,
            "failover_ready": False,
            "secondary_capacity_ready": False,
            "automation_policy_permits_failover": False,
            "operator_approval_required": False,
            "deploy_regression_suspected": False,
            "rollback_safe": False,
            "capacity_headroom": "high",
            "change_failure_blast_radius": "service",
            "telemetry_confidence": "low",
        }
    if action_id == "page_human_operator":
        return {
            "fault_scope": "region",
            "node_locality_score": 0.10,
            "recent_restart_attempts": 3.0,
            "failover_ready": False,
            "secondary_capacity_ready": False,
            "automation_policy_permits_failover": False,
            "operator_approval_required": True,
            "deploy_regression_suspected": False,
            "rollback_safe": False,
            "capacity_headroom": "low",
            "change_failure_blast_radius": "region",
            "telemetry_confidence": "high",
        }
    return {
        "fault_scope": "unknown",
        "node_locality_score": 0.50,
        "recent_restart_attempts": 0.0,
        "failover_ready": False,
        "secondary_capacity_ready": False,
        "automation_policy_permits_failover": False,
        "operator_approval_required": True,
        "deploy_regression_suspected": False,
        "rollback_safe": False,
        "capacity_headroom": "moderate",
        "change_failure_blast_radius": "cluster",
        "telemetry_confidence": "low",
    }


def augment_case(case: dict) -> dict:
    row = dict(case)
    features = dict(row["input_features"])
    action_id = row.get("expected_action_id")
    features.update(base_v4_features(action_id))

    if action_id == "restart_service" and features.get("deployment_recency") == "recent":
        features["recent_restart_attempts"] = 1.0
    if action_id == "drain_node" and features.get("region_health") == "degraded":
        features["node_locality_score"] = 0.85
    if action_id == "rollback_deploy" and features.get("error_rate") == "severe":
        features["change_failure_blast_radius"] = "region"
    if action_id == "gather_more_telemetry" and features.get("latency") == "normal":
        features["telemetry_confidence"] = "medium"
    if action_id == "page_human_operator" and features.get("write_path_available") is False:
        features["secondary_capacity_ready"] = False

    if not row.get("supported", True) or action_id is None:
        features.update(base_v4_features(None))

    row["input_features"] = features
    return row


def synthetic_train_cases() -> list[dict]:
    rows = []
    base = {
        "dependency_health": "failing",
        "deployment_recency": "stale",
        "error_rate": "severe",
        "latency": "severe",
        "region_health": "degraded",
        "replication_lag": "high",
        "saturation": "critical",
        "write_path_available": True,
    }
    for index, override in enumerate(
        (
            {"region_health": "degraded"},
            {"region_health": "failing", "latency": "extreme"},
        ),
        start=1,
    ):
        features = dict(base)
        features.update(override)
        features.update(base_v4_features("page_human_operator"))
        rows.append(
            {
                "case_id": f"sre_v4_train_handoff_{index:03d}",
                "expected_action_id": "page_human_operator",
                "input_features": features,
                "supported": True,
                "ood": True,
            }
        )
    return rows


def build_registry_v4() -> dict:
    return {
        "registry_name": "sre-policy-router",
        "version": "1.1.0",
        "actions": [
            {
                "action_id": "restart_service",
                "name": "Restart Service",
                "description": "Restart unhealthy service when the fault looks service-local and automation remains viable.",
                "parameters_schema": {"type": "object", "properties": {}, "required": []},
                "support_spec": {
                    "all": [
                        {"feature": "dependency_health", "op": "eq", "value": "degraded"},
                        {"feature": "fault_scope", "op": "eq", "value": "service"},
                        {"feature": "node_locality_score", "op": "lte", "value": 0.35},
                        {"feature": "recent_restart_attempts", "op": "lte", "value": 1.0},
                        {"feature": "deploy_regression_suspected", "op": "eq", "value": False},
                        {"feature": "latency", "op": "in", "value": ["elevated", "high", "severe", "extreme"]},
                        {"feature": "saturation", "op": "eq", "value": "high"},
                    ]
                },
                "tags": ["service"],
            },
            {
                "action_id": "failover_region",
                "name": "Failover Region",
                "description": "Shift traffic to a healthy region when failover is safe and permitted.",
                "parameters_schema": {"type": "object", "properties": {}, "required": []},
                "support_spec": {
                    "all": [
                        {"feature": "dependency_health", "op": "eq", "value": "failing"},
                        {"feature": "region_health", "op": "eq", "value": "failing"},
                        {"feature": "write_path_available", "op": "eq", "value": False},
                        {"feature": "error_rate", "op": "eq", "value": "severe"},
                        {"feature": "replication_lag", "op": "eq", "value": "high"},
                        {"feature": "saturation", "op": "in", "value": ["high", "critical"]},
                        {"feature": "latency", "op": "in", "value": ["high", "severe", "extreme"]},
                        {"feature": "fault_scope", "op": "eq", "value": "region"},
                        {"feature": "failover_ready", "op": "eq", "value": True},
                        {"feature": "secondary_capacity_ready", "op": "eq", "value": True},
                        {"feature": "automation_policy_permits_failover", "op": "eq", "value": True},
                        {"feature": "operator_approval_required", "op": "eq", "value": False},
                    ]
                },
                "tags": ["region"],
            },
            {
                "action_id": "scale_out",
                "name": "Scale Out",
                "description": "Add capacity when latency is demand-driven rather than deploy-driven.",
                "parameters_schema": {"type": "object", "properties": {}, "required": []},
                "support_spec": {
                    "all": [
                        {"feature": "dependency_health", "op": "eq", "value": "healthy"},
                        {"feature": "write_path_available", "op": "eq", "value": True},
                        {"feature": "saturation", "op": "in", "value": ["high", "critical"]},
                        {"feature": "latency", "op": "in", "value": ["elevated", "high"]},
                        {"feature": "capacity_headroom", "op": "eq", "value": "low"},
                        {"feature": "deploy_regression_suspected", "op": "eq", "value": False},
                        {"feature": "fault_scope", "op": "eq", "value": "service"},
                    ]
                },
                "tags": ["capacity"],
            },
            {
                "action_id": "drain_node",
                "name": "Drain Node",
                "description": "Drain one unhealthy node when failure is concentrated to a local replica.",
                "parameters_schema": {"type": "object", "properties": {}, "required": []},
                "support_spec": {
                    "all": [
                        {"feature": "dependency_health", "op": "eq", "value": "degraded"},
                        {"feature": "write_path_available", "op": "eq", "value": True},
                        {"feature": "fault_scope", "op": "eq", "value": "node"},
                        {"feature": "node_locality_score", "op": "gte", "value": 0.65},
                        {"feature": "recent_restart_attempts", "op": "lte", "value": 1.0},
                        {"feature": "deploy_regression_suspected", "op": "eq", "value": False},
                    ]
                },
                "tags": ["node"],
            },
            {
                "action_id": "rollback_deploy",
                "name": "Rollback Deploy",
                "description": "Rollback a suspected bad deployment when rollback is safe.",
                "parameters_schema": {"type": "object", "properties": {}, "required": []},
                "support_spec": {
                    "all": [
                        {"feature": "write_path_available", "op": "eq", "value": True},
                        {"feature": "deployment_recency", "op": "in", "value": ["fresh", "recent"]},
                        {"feature": "error_rate", "op": "in", "value": ["elevated", "high", "severe"]},
                        {"feature": "latency", "op": "in", "value": ["elevated", "high", "severe", "extreme"]},
                        {"feature": "deploy_regression_suspected", "op": "eq", "value": True},
                        {"feature": "rollback_safe", "op": "eq", "value": True},
                        {"feature": "fault_scope", "op": "eq", "value": "service"},
                    ]
                },
                "tags": ["deploy"],
            },
            {
                "action_id": "enable_readonly_mode",
                "name": "Enable Readonly Mode",
                "description": "Preserve the service by disabling writes when consistency is at risk.",
                "parameters_schema": {"type": "object", "properties": {}, "required": []},
                "support_spec": {
                    "all": [
                        {"feature": "write_path_available", "op": "eq", "value": False},
                        {"feature": "replication_lag", "op": "eq", "value": "high"},
                        {"feature": "saturation", "op": "in", "value": ["high", "critical"]},
                        {"feature": "error_rate", "op": "in", "value": ["high", "severe"]},
                        {"feature": "latency", "op": "in", "value": ["elevated", "high", "severe", "extreme"]},
                        {"feature": "fault_scope", "op": "eq", "value": "service"},
                        {"feature": "change_failure_blast_radius", "op": "in", "value": ["cluster", "region"]},
                    ]
                },
                "tags": ["safety"],
            },
            {
                "action_id": "gather_more_telemetry",
                "name": "Gather More Telemetry",
                "description": "Collect more evidence before taking disruptive action.",
                "parameters_schema": {"type": "object", "properties": {}, "required": []},
                "support_spec": {
                    "all": [
                        {"feature": "write_path_available", "op": "eq", "value": True},
                        {"feature": "telemetry_confidence", "op": "in", "value": ["low", "medium"]},
                        {"feature": "fault_scope", "op": "eq", "value": "service"},
                        {"feature": "error_rate", "op": "in", "value": ["normal", "elevated"]},
                        {"feature": "latency", "op": "in", "value": ["normal", "elevated"]},
                    ]
                },
                "tags": ["telemetry"],
            },
            {
                "action_id": "page_human_operator",
                "name": "Page Human Operator",
                "description": "Escalate to a human operator when the blast radius is severe but automated failover is blocked.",
                "parameters_schema": {
                    "type": "object",
                    "properties": {"reason": {"type": "string"}},
                    "required": ["reason"],
                },
                "support_spec": {
                    "all": [
                        {"feature": "dependency_health", "op": "eq", "value": "failing"},
                        {"feature": "error_rate", "op": "eq", "value": "severe"},
                        {"feature": "saturation", "op": "eq", "value": "critical"},
                        {"feature": "latency", "op": "in", "value": ["severe", "extreme"]},
                        {"feature": "fault_scope", "op": "eq", "value": "region"},
                        {
                            "any": [
                                {"feature": "failover_ready", "op": "eq", "value": False},
                                {"feature": "secondary_capacity_ready", "op": "eq", "value": False},
                                {"feature": "automation_policy_permits_failover", "op": "eq", "value": False},
                                {"feature": "operator_approval_required", "op": "eq", "value": True},
                            ]
                        },
                    ]
                },
                "tags": ["fallback", "safe", "safety"],
            },
        ],
    }


def main() -> None:
    train_rows = load_jsonl(DATA_DIR / "train_cases.jsonl")
    eval_rows = load_jsonl(DATA_DIR / "cases_v3.jsonl")

    train_v4 = [augment_case(row) for row in train_rows]
    train_v4.extend(synthetic_train_cases())
    eval_v4 = [augment_case(row) for row in eval_rows]
    registry_v4 = build_registry_v4()

    train_path = DATA_DIR / "train_cases_v4.jsonl"
    eval_path = DATA_DIR / "cases_v4.jsonl"
    registry_path = DATA_DIR / "registry_v4.json"
    summary_path = RESULTS_DIR / "sre_v4_generation_summary.json"

    write_jsonl(train_path, train_v4)
    write_jsonl(eval_path, eval_v4)
    registry_path.write_text(json.dumps(registry_v4, indent=2), encoding="utf-8")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "train_cases_v4": len(train_v4),
                "eval_cases_v4": len(eval_v4),
                "registry_path": str(registry_path),
                "train_path": str(train_path),
                "eval_path": str(eval_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"wrote {train_path}")
    print(f"wrote {eval_path}")
    print(f"wrote {registry_path}")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
