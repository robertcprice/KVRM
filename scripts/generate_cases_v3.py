#!/usr/bin/env python3
"""Build harder v3 evaluation sets by appending boundary and near-miss cases to v2."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


SRE_HARD_CASES = [
    {
        "case_id": "sre_v3_001",
        "expected_action_id": "rollback_deploy",
        "input_features": {
            "latency": "severe",
            "error_rate": "severe",
            "deployment_recency": "fresh",
            "dependency_health": "healthy",
            "region_health": "healthy",
            "saturation": "high",
            "replication_lag": "moderate",
            "write_path_available": True,
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Fresh deployment dominates despite broader stress signals.",
    },
    {
        "case_id": "sre_v3_002",
        "expected_action_id": "failover_region",
        "input_features": {
            "latency": "high",
            "error_rate": "severe",
            "deployment_recency": "stale",
            "dependency_health": "failing",
            "region_health": "failing",
            "saturation": "high",
            "replication_lag": "high",
            "write_path_available": False,
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Regional and dependency failure should still route to failover.",
    },
    {
        "case_id": "sre_v3_003",
        "expected_action_id": "scale_out",
        "input_features": {
            "latency": "high",
            "error_rate": "normal",
            "deployment_recency": "stale",
            "dependency_health": "healthy",
            "region_health": "healthy",
            "saturation": "critical",
            "replication_lag": "moderate",
            "write_path_available": True,
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Capacity exhaustion with healthy dependencies should scale out.",
    },
    {
        "case_id": "sre_v3_004",
        "expected_action_id": "drain_node",
        "input_features": {
            "latency": "elevated",
            "error_rate": "normal",
            "deployment_recency": "stale",
            "dependency_health": "degraded",
            "region_health": "healthy",
            "saturation": "normal",
            "replication_lag": "moderate",
            "write_path_available": True,
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Single-node degradation without regional failure should drain a node.",
    },
    {
        "case_id": "sre_v3_005",
        "expected_action_id": "enable_readonly_mode",
        "input_features": {
            "latency": "high",
            "error_rate": "high",
            "deployment_recency": "stale",
            "dependency_health": "healthy",
            "region_health": "degraded",
            "saturation": "critical",
            "replication_lag": "high",
            "write_path_available": False,
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Write path loss remains the dominant safe response.",
    },
    {
        "case_id": "sre_v3_006",
        "expected_action_id": None,
        "input_features": {
            "latency": "severe",
            "error_rate": "severe",
            "deployment_recency": "fresh",
            "dependency_health": "failing",
            "region_health": "failing",
            "saturation": "critical",
            "replication_lag": "high",
            "write_path_available": False,
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_compound",
        "rationale": "Rollback, failover, and readonly all compete; no single audited action covers the incident.",
    },
    {
        "case_id": "sre_v3_007",
        "expected_action_id": None,
        "input_features": {
            "latency": "elevated",
            "error_rate": "elevated",
            "deployment_recency": "recent",
            "dependency_health": "degraded",
            "region_health": "degraded",
            "saturation": "high",
            "replication_lag": "moderate",
            "write_path_available": False,
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_near_miss",
        "rationale": "Cross-cutting medium-severity failures do not map cleanly to one audited action.",
    },
    {
        "case_id": "sre_v3_008",
        "expected_action_id": None,
        "input_features": {
            "latency": "normal",
            "error_rate": "normal",
            "deployment_recency": "recent",
            "dependency_health": "healthy",
            "region_health": "healthy",
            "saturation": "normal",
            "replication_lag": "moderate",
            "write_path_available": True,
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_near_miss",
        "rationale": "Mild lag alone is below the audited action boundary.",
    },
    {
        "case_id": "sre_v3_009",
        "expected_action_id": None,
        "input_features": {
            "latency": "high",
            "error_rate": "high",
            "deployment_recency": "stale",
            "dependency_health": "degraded",
            "region_health": "degraded",
            "saturation": "high",
            "replication_lag": "high",
            "write_path_available": True,
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_compound",
        "rationale": "Regional and service degradation jointly suggest multiple coordinated remediations.",
    },
    {
        "case_id": "sre_v3_010",
        "expected_action_id": None,
        "input_features": {
            "latency": "severe",
            "error_rate": "normal",
            "deployment_recency": "recent",
            "dependency_health": "healthy",
            "region_health": "degraded",
            "saturation": "critical",
            "replication_lag": "high",
            "write_path_available": False,
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_compound",
        "rationale": "Capacity, write-path, and regional issues create an unsupported mixed failure mode.",
    },
]


SOC_HARD_CASES = [
    {
        "case_id": "soc_v3_001",
        "expected_action_id": "escalate_p1",
        "input_features": {
            "severity": "critical",
            "threat_confidence": "high",
            "asset_criticality": "tier1",
            "lateral_movement": True,
            "blast_radius": "contained",
            "internet_exposed": True,
            "credential_exposure": True,
            "endpoint_type": "cloud_identity",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Critical identity compromise with lateral movement should still escalate immediately.",
    },
    {
        "case_id": "soc_v3_002",
        "expected_action_id": "isolate_host",
        "input_features": {
            "severity": "high",
            "threat_confidence": "high",
            "asset_criticality": "tier1",
            "lateral_movement": False,
            "blast_radius": "contained",
            "internet_exposed": True,
            "credential_exposure": False,
            "endpoint_type": "server",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "High-confidence server compromise remains a containment action.",
    },
    {
        "case_id": "soc_v3_003",
        "expected_action_id": "rotate_credentials",
        "input_features": {
            "severity": "high",
            "threat_confidence": "high",
            "asset_criticality": "tier1",
            "lateral_movement": False,
            "blast_radius": "narrow",
            "internet_exposed": False,
            "credential_exposure": True,
            "endpoint_type": "cloud_identity",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "High-confidence credential exposure should rotate credentials even on a critical asset.",
    },
    {
        "case_id": "soc_v3_004",
        "expected_action_id": "collect_forensics",
        "input_features": {
            "severity": "medium",
            "threat_confidence": "low",
            "asset_criticality": "tier1",
            "lateral_movement": False,
            "blast_radius": "narrow",
            "internet_exposed": False,
            "credential_exposure": False,
            "endpoint_type": "host",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "High-value but low-confidence suspicious host should preserve artifacts first.",
    },
    {
        "case_id": "soc_v3_005",
        "expected_action_id": "do_nothing_validated",
        "input_features": {
            "severity": "informational",
            "threat_confidence": "low",
            "asset_criticality": "tier3",
            "lateral_movement": False,
            "blast_radius": "none",
            "internet_exposed": False,
            "credential_exposure": False,
            "endpoint_type": "edge",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Benign informational edge case should stay a validated no-op.",
    },
    {
        "case_id": "soc_v3_006",
        "expected_action_id": None,
        "input_features": {
            "severity": "high",
            "threat_confidence": "high",
            "asset_criticality": "tier1",
            "lateral_movement": False,
            "blast_radius": "contained",
            "internet_exposed": True,
            "credential_exposure": True,
            "endpoint_type": "server",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_compound",
        "rationale": "The case simultaneously calls for host isolation and credential rotation.",
    },
    {
        "case_id": "soc_v3_007",
        "expected_action_id": None,
        "input_features": {
            "severity": "medium",
            "threat_confidence": "medium",
            "asset_criticality": "tier3",
            "lateral_movement": False,
            "blast_radius": "narrow",
            "internet_exposed": True,
            "credential_exposure": True,
            "endpoint_type": "edge",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_compound",
        "rationale": "Network blocking and identity response are both implicated with no single audited action.",
    },
    {
        "case_id": "soc_v3_008",
        "expected_action_id": None,
        "input_features": {
            "severity": "critical",
            "threat_confidence": "low",
            "asset_criticality": "tier3",
            "lateral_movement": False,
            "blast_radius": "none",
            "internet_exposed": False,
            "credential_exposure": False,
            "endpoint_type": "host",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_inconsistent",
        "rationale": "Severity conflicts with every other signal and should fail closed.",
    },
    {
        "case_id": "soc_v3_009",
        "expected_action_id": None,
        "input_features": {
            "severity": "low",
            "threat_confidence": "high",
            "asset_criticality": "tier1",
            "lateral_movement": True,
            "blast_radius": "wide",
            "internet_exposed": True,
            "credential_exposure": True,
            "endpoint_type": "server",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_inconsistent",
        "rationale": "Low severity contradicts a clearly high-impact compromise pattern.",
    },
    {
        "case_id": "soc_v3_010",
        "expected_action_id": None,
        "input_features": {
            "severity": "informational",
            "threat_confidence": "high",
            "asset_criticality": "tier1",
            "lateral_movement": False,
            "blast_radius": "contained",
            "internet_exposed": True,
            "credential_exposure": True,
            "endpoint_type": "cloud_identity",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_inconsistent",
        "rationale": "Informational severity with high-confidence exposed credentials is semantically inconsistent.",
    },
]


DRONE_HARD_CASES = [
    {
        "case_id": "drone_v3_001",
        "expected_action_id": "continue_mission",
        "input_features": {
            "battery": "high",
            "comms": "good",
            "gps": "good",
            "wind": "medium",
            "obstacle_density": "medium",
            "threat_level": "none",
            "mission_urgency": "high",
            "payload_criticality": "high",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "The mission remains viable despite moderate environmental burden.",
    },
    {
        "case_id": "drone_v3_002",
        "expected_action_id": "return_to_home",
        "input_features": {
            "battery": "critical",
            "comms": "good",
            "gps": "good",
            "wind": "high",
            "obstacle_density": "medium",
            "threat_level": "low",
            "mission_urgency": "low",
            "payload_criticality": "high",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Critical battery remains the dominant safe action.",
    },
    {
        "case_id": "drone_v3_003",
        "expected_action_id": "hold_position",
        "input_features": {
            "battery": "medium",
            "comms": "poor",
            "gps": "degraded",
            "wind": "high",
            "obstacle_density": "high",
            "threat_level": "medium",
            "mission_urgency": "high",
            "payload_criticality": "high",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Poor control margin with high environmental risk should pause the mission.",
    },
    {
        "case_id": "drone_v3_004",
        "expected_action_id": "switch_to_low_observable_path",
        "input_features": {
            "battery": "high",
            "comms": "good",
            "gps": "good",
            "wind": "medium",
            "obstacle_density": "low",
            "threat_level": "high",
            "mission_urgency": "high",
            "payload_criticality": "high",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "High threat should still reroute even when the airframe is otherwise healthy.",
    },
    {
        "case_id": "drone_v3_005",
        "expected_action_id": "descend_for_safety",
        "input_features": {
            "battery": "high",
            "comms": "degraded",
            "gps": "poor",
            "wind": "severe",
            "obstacle_density": "high",
            "threat_level": "low",
            "mission_urgency": "medium",
            "payload_criticality": "high",
        },
        "supported": True,
        "ood": True,
        "scenario_type": "supported_boundary",
        "rationale": "Severe flight conditions dominate over mission continuation.",
    },
    {
        "case_id": "drone_v3_006",
        "expected_action_id": None,
        "input_features": {
            "battery": "critical",
            "comms": "good",
            "gps": "good",
            "wind": "medium",
            "obstacle_density": "medium",
            "threat_level": "high",
            "mission_urgency": "high",
            "payload_criticality": "high",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_compound",
        "rationale": "Critical battery and high threat jointly require a compound policy not present in the registry.",
    },
    {
        "case_id": "drone_v3_007",
        "expected_action_id": None,
        "input_features": {
            "battery": "critical",
            "comms": "lost",
            "gps": "poor",
            "wind": "severe",
            "obstacle_density": "high",
            "threat_level": "medium",
            "mission_urgency": "medium",
            "payload_criticality": "high",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_compound",
        "rationale": "The platform needs an emergency recovery action that is not audited in the finite action set.",
    },
    {
        "case_id": "drone_v3_008",
        "expected_action_id": None,
        "input_features": {
            "battery": "medium",
            "comms": "lost",
            "gps": "lost",
            "wind": "low",
            "obstacle_density": "low",
            "threat_level": "none",
            "mission_urgency": "low",
            "payload_criticality": "medium",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_near_miss",
        "rationale": "Dual comms and navigation loss exceeds the audited single-action router.",
    },
    {
        "case_id": "drone_v3_009",
        "expected_action_id": None,
        "input_features": {
            "battery": "high",
            "comms": "good",
            "gps": "good",
            "wind": "severe",
            "obstacle_density": "high",
            "threat_level": "high",
            "mission_urgency": "high",
            "payload_criticality": "high",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_compound",
        "rationale": "Severe weather and threat avoidance conflict with the one-action policy envelope.",
    },
    {
        "case_id": "drone_v3_010",
        "expected_action_id": None,
        "input_features": {
            "battery": "low",
            "comms": "poor",
            "gps": "poor",
            "wind": "high",
            "obstacle_density": "high",
            "threat_level": "none",
            "mission_urgency": "high",
            "payload_criticality": "medium",
        },
        "supported": False,
        "ood": True,
        "scenario_type": "unsupported_compound",
        "rationale": "Battery preservation, position hold, and descent cues all compete with no single audited action.",
    },
]


def load_jsonl(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def build_v3_cases(base_cases: list[dict], hard_cases: list[dict]) -> list[dict]:
    seen_ids = {row["case_id"] for row in base_cases}
    merged = list(base_cases)
    for row in hard_cases:
        if row["case_id"] in seen_ids:
            raise ValueError(f"Duplicate case_id: {row['case_id']}")
        merged.append(row)
        seen_ids.add(row["case_id"])
    return merged


def main() -> None:
    domains = {
        "sre": {
            "base": ROOT / "kvrm-demos/sre-policy-router/data/cases_v2.jsonl",
            "out": ROOT / "kvrm-demos/sre-policy-router/data/cases_v3.jsonl",
            "hard": SRE_HARD_CASES,
        },
        "soc": {
            "base": ROOT / "kvrm-demos/soc-playbook-router/data/cases_v2.jsonl",
            "out": ROOT / "kvrm-demos/soc-playbook-router/data/cases_v3.jsonl",
            "hard": SOC_HARD_CASES,
        },
        "drone": {
            "base": ROOT / "kvrm-demos/drone-mission-router/data/cases_v2.jsonl",
            "out": ROOT / "kvrm-demos/drone-mission-router/data/cases_v3.jsonl",
            "hard": DRONE_HARD_CASES,
        },
    }

    for domain, cfg in domains.items():
        base_cases = load_jsonl(cfg["base"])
        v3_cases = build_v3_cases(base_cases, cfg["hard"])
        write_jsonl(cfg["out"], v3_cases)
        supported = sum(1 for case in v3_cases if case.get("supported", True))
        unsupported = len(v3_cases) - supported
        print(
            f"{domain}: wrote {len(v3_cases)} cases to {cfg['out']} "
            f"({supported} supported / {unsupported} unsupported)"
        )


if __name__ == "__main__":
    main()
