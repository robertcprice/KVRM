#!/usr/bin/env python3
"""Expand all three demo datasets with correct feature vocabularies.

Feature value vocabularies (from selector CATEGORICAL_VALUES):

SRE:
  latency: normal, elevated, high, severe
  error_rate: normal, elevated, high, severe
  deployment_recency: stale, recent, fresh
  dependency_health: healthy, degraded, failing
  region_health: healthy, degraded, failing
  saturation: normal, high, critical
  replication_lag: low, moderate, high
  write_path_available: True/False (boolean)

SOC:
  severity: informational, low, medium, high, critical
  threat_confidence: low, medium, high
  asset_criticality: tier3, tier2, tier1
  lateral_movement: True/False (boolean)
  blast_radius: none, narrow, contained, wide
  internet_exposed: True/False (boolean)
  credential_exposure: True/False (boolean)
  endpoint_type: host, server, cloud_identity, edge

DRONE:
  battery: critical, low, medium, high
  comms: lost, poor, degraded, good
  gps: lost, poor, degraded, good
  wind: low, medium, high, severe
  obstacle_density: low, medium, high
  threat_level: none, low, medium, high
  mission_urgency: low, medium, high
  payload_criticality: low, medium, high
"""
from __future__ import annotations

import json
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parents[1] / "kvrm-demos"


# ═══════════════════════════════════════════════════════════════════
# SRE DOMAIN
# ═══════════════════════════════════════════════════════════════════

SRE_NEW_TRAIN = [
    {"case_id": "sre_train_008", "input_features": {"latency": "severe", "error_rate": "high", "deployment_recency": "fresh", "dependency_health": "healthy", "region_health": "healthy", "saturation": "high", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "rollback_deploy", "supported": True, "ood": False},
    {"case_id": "sre_train_009", "input_features": {"latency": "elevated", "error_rate": "severe", "deployment_recency": "fresh", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "rollback_deploy", "supported": True, "ood": False},
    {"case_id": "sre_train_010", "input_features": {"latency": "severe", "error_rate": "severe", "deployment_recency": "stale", "dependency_health": "failing", "region_health": "failing", "saturation": "critical", "replication_lag": "high", "write_path_available": False}, "expected_action_id": "failover_region", "supported": True, "ood": False},
    {"case_id": "sre_train_011", "input_features": {"latency": "elevated", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "critical", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "scale_out", "supported": True, "ood": False},
    {"case_id": "sre_train_012", "input_features": {"latency": "severe", "error_rate": "high", "deployment_recency": "stale", "dependency_health": "degraded", "region_health": "healthy", "saturation": "high", "replication_lag": "moderate", "write_path_available": True}, "expected_action_id": "restart_service", "supported": True, "ood": False},
    {"case_id": "sre_train_013", "input_features": {"latency": "normal", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "degraded", "region_health": "healthy", "saturation": "normal", "replication_lag": "high", "write_path_available": True}, "expected_action_id": "drain_node", "supported": True, "ood": False},
    {"case_id": "sre_train_014", "input_features": {"latency": "elevated", "error_rate": "high", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "degraded", "saturation": "high", "replication_lag": "high", "write_path_available": False}, "expected_action_id": "enable_readonly_mode", "supported": True, "ood": False},
    {"case_id": "sre_train_015", "input_features": {"latency": "normal", "error_rate": "normal", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "high", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "gather_more_telemetry", "supported": True, "ood": False},
]

SRE_NEW_EVAL = [
    # In-distribution supported
    {"case_id": "sre_eval_017", "input_features": {"latency": "severe", "error_rate": "severe", "deployment_recency": "fresh", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "rollback_deploy", "supported": True, "ood": False},
    {"case_id": "sre_eval_018", "input_features": {"latency": "severe", "error_rate": "high", "deployment_recency": "stale", "dependency_health": "failing", "region_health": "degraded", "saturation": "critical", "replication_lag": "high", "write_path_available": False}, "expected_action_id": "failover_region", "supported": True, "ood": False},
    {"case_id": "sre_eval_019", "input_features": {"latency": "elevated", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "critical", "replication_lag": "moderate", "write_path_available": True}, "expected_action_id": "scale_out", "supported": True, "ood": False},
    {"case_id": "sre_eval_020", "input_features": {"latency": "high", "error_rate": "high", "deployment_recency": "stale", "dependency_health": "degraded", "region_health": "healthy", "saturation": "high", "replication_lag": "moderate", "write_path_available": True}, "expected_action_id": "restart_service", "supported": True, "ood": False},
    {"case_id": "sre_eval_021", "input_features": {"latency": "normal", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "degraded", "region_health": "healthy", "saturation": "normal", "replication_lag": "moderate", "write_path_available": True}, "expected_action_id": "drain_node", "supported": True, "ood": False},
    {"case_id": "sre_eval_022", "input_features": {"latency": "severe", "error_rate": "high", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "high", "replication_lag": "high", "write_path_available": False}, "expected_action_id": "enable_readonly_mode", "supported": True, "ood": False},
    {"case_id": "sre_eval_023", "input_features": {"latency": "elevated", "error_rate": "normal", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "gather_more_telemetry", "supported": True, "ood": False},
    {"case_id": "sre_eval_024", "input_features": {"latency": "severe", "error_rate": "elevated", "deployment_recency": "recent", "dependency_health": "healthy", "region_health": "healthy", "saturation": "high", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "rollback_deploy", "supported": True, "ood": False},
    {"case_id": "sre_eval_025", "input_features": {"latency": "high", "error_rate": "severe", "deployment_recency": "stale", "dependency_health": "failing", "region_health": "failing", "saturation": "critical", "replication_lag": "high", "write_path_available": False}, "expected_action_id": "failover_region", "supported": True, "ood": False},
    {"case_id": "sre_eval_026", "input_features": {"latency": "normal", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "critical", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "scale_out", "supported": True, "ood": False},

    # OOD supported (novel combos)
    {"case_id": "sre_eval_027", "input_features": {"latency": "normal", "error_rate": "severe", "deployment_recency": "fresh", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "rollback_deploy", "supported": True, "ood": True},
    {"case_id": "sre_eval_028", "input_features": {"latency": "severe", "error_rate": "severe", "deployment_recency": "stale", "dependency_health": "degraded", "region_health": "failing", "saturation": "high", "replication_lag": "high", "write_path_available": False}, "expected_action_id": "failover_region", "supported": True, "ood": True},
    {"case_id": "sre_eval_029", "input_features": {"latency": "severe", "error_rate": "normal", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "critical", "replication_lag": "moderate", "write_path_available": True}, "expected_action_id": "scale_out", "supported": True, "ood": True},
    {"case_id": "sre_eval_030", "input_features": {"latency": "severe", "error_rate": "severe", "deployment_recency": "stale", "dependency_health": "degraded", "region_health": "healthy", "saturation": "critical", "replication_lag": "moderate", "write_path_available": True}, "expected_action_id": "restart_service", "supported": True, "ood": True},
    {"case_id": "sre_eval_031", "input_features": {"latency": "elevated", "error_rate": "elevated", "deployment_recency": "recent", "dependency_health": "degraded", "region_health": "healthy", "saturation": "high", "replication_lag": "high", "write_path_available": True}, "expected_action_id": "drain_node", "supported": True, "ood": True},
    {"case_id": "sre_eval_032", "input_features": {"latency": "elevated", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "degraded", "saturation": "normal", "replication_lag": "high", "write_path_available": False}, "expected_action_id": "enable_readonly_mode", "supported": True, "ood": True},
    {"case_id": "sre_eval_033", "input_features": {"latency": "normal", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "degraded", "saturation": "high", "replication_lag": "low", "write_path_available": True}, "expected_action_id": "gather_more_telemetry", "supported": True, "ood": True},

    # Boundary (hard to classify)
    {"case_id": "sre_eval_034", "input_features": {"latency": "high", "error_rate": "high", "deployment_recency": "recent", "dependency_health": "degraded", "region_health": "healthy", "saturation": "high", "replication_lag": "moderate", "write_path_available": True}, "expected_action_id": "restart_service", "supported": True, "ood": True},
    {"case_id": "sre_eval_035", "input_features": {"latency": "severe", "error_rate": "high", "deployment_recency": "fresh", "dependency_health": "degraded", "region_health": "degraded", "saturation": "critical", "replication_lag": "high", "write_path_available": False}, "expected_action_id": "failover_region", "supported": True, "ood": True},

    # Unsupported / adversarial
    {"case_id": "sre_eval_036", "input_features": {"latency": "unknown", "error_rate": "high", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "sre_eval_037", "input_features": {"latency": "normal", "error_rate": "normal", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "sre_eval_038", "input_features": {"latency": "elevated", "error_rate": "elevated", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": "maybe"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "sre_eval_039", "input_features": {"latency": "cosmic", "error_rate": "infinite", "deployment_recency": "ancient", "dependency_health": "quantum", "region_health": "parallel", "saturation": "transcendent", "replication_lag": "temporal", "write_path_available": "superposition"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "sre_eval_040", "input_features": {"latency": "normal", "error_rate": "normal", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}, "expected_action_id": None, "supported": False, "ood": False},
    {"case_id": "sre_eval_041", "input_features": {"latency": "elevated", "error_rate": "normal", "deployment_recency": "stale", "dependency_health": "healthy", "region_health": "healthy", "saturation": "normal", "replication_lag": "low", "write_path_available": True}, "expected_action_id": None, "supported": False, "ood": False},
    {"case_id": "sre_eval_042", "input_features": {}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "sre_eval_043", "input_features": {"latency": "", "error_rate": "", "deployment_recency": "", "dependency_health": "", "region_health": "", "saturation": "", "replication_lag": "", "write_path_available": ""}, "expected_action_id": None, "supported": False, "ood": True},
]


# ═══════════════════════════════════════════════════════════════════
# SOC DOMAIN
# ═══════════════════════════════════════════════════════════════════

SOC_NEW_TRAIN = [
    {"case_id": "soc_train_008", "input_features": {"severity": "critical", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": True, "blast_radius": "contained", "internet_exposed": True, "credential_exposure": True, "endpoint_type": "cloud_identity"}, "expected_action_id": "escalate_p1", "supported": True, "ood": False},
    {"case_id": "soc_train_009", "input_features": {"severity": "high", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": False, "blast_radius": "contained", "internet_exposed": True, "credential_exposure": False, "endpoint_type": "server"}, "expected_action_id": "isolate_host", "supported": True, "ood": False},
    {"case_id": "soc_train_010", "input_features": {"severity": "medium", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": False, "credential_exposure": True, "endpoint_type": "server"}, "expected_action_id": "rotate_credentials", "supported": True, "ood": False},
    {"case_id": "soc_train_011", "input_features": {"severity": "high", "threat_confidence": "medium", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": True, "credential_exposure": False, "endpoint_type": "edge"}, "expected_action_id": "block_ip_temporarily", "supported": True, "ood": False},
    {"case_id": "soc_train_012", "input_features": {"severity": "medium", "threat_confidence": "low", "asset_criticality": "tier2", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "server"}, "expected_action_id": "collect_forensics", "supported": True, "ood": False},
    {"case_id": "soc_train_013", "input_features": {"severity": "low", "threat_confidence": "low", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "server"}, "expected_action_id": "monitor_only", "supported": True, "ood": False},
    {"case_id": "soc_train_014", "input_features": {"severity": "informational", "threat_confidence": "low", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "none", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "server"}, "expected_action_id": "do_nothing_validated", "supported": True, "ood": False},
]

SOC_NEW_EVAL = [
    # In-distribution supported
    {"case_id": "soc_eval_017", "input_features": {"severity": "critical", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": True, "blast_radius": "wide", "internet_exposed": True, "credential_exposure": True, "endpoint_type": "server"}, "expected_action_id": "escalate_p1", "supported": True, "ood": False},
    {"case_id": "soc_eval_018", "input_features": {"severity": "high", "threat_confidence": "high", "asset_criticality": "tier2", "lateral_movement": False, "blast_radius": "contained", "internet_exposed": True, "credential_exposure": False, "endpoint_type": "server"}, "expected_action_id": "isolate_host", "supported": True, "ood": False},
    {"case_id": "soc_eval_019", "input_features": {"severity": "high", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": True, "credential_exposure": True, "endpoint_type": "server"}, "expected_action_id": "rotate_credentials", "supported": True, "ood": False},
    {"case_id": "soc_eval_020", "input_features": {"severity": "medium", "threat_confidence": "medium", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": True, "credential_exposure": False, "endpoint_type": "edge"}, "expected_action_id": "block_ip_temporarily", "supported": True, "ood": False},
    {"case_id": "soc_eval_021", "input_features": {"severity": "low", "threat_confidence": "medium", "asset_criticality": "tier2", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "host"}, "expected_action_id": "collect_forensics", "supported": True, "ood": False},
    {"case_id": "soc_eval_022", "input_features": {"severity": "low", "threat_confidence": "low", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "server"}, "expected_action_id": "monitor_only", "supported": True, "ood": False},
    {"case_id": "soc_eval_023", "input_features": {"severity": "informational", "threat_confidence": "low", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "none", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "edge"}, "expected_action_id": "do_nothing_validated", "supported": True, "ood": False},
    {"case_id": "soc_eval_024", "input_features": {"severity": "critical", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": True, "blast_radius": "wide", "internet_exposed": True, "credential_exposure": False, "endpoint_type": "cloud_identity"}, "expected_action_id": "escalate_p1", "supported": True, "ood": False},
    {"case_id": "soc_eval_025", "input_features": {"severity": "high", "threat_confidence": "medium", "asset_criticality": "tier1", "lateral_movement": False, "blast_radius": "contained", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "host"}, "expected_action_id": "isolate_host", "supported": True, "ood": False},
    {"case_id": "soc_eval_026", "input_features": {"severity": "medium", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": True, "credential_exposure": True, "endpoint_type": "host"}, "expected_action_id": "rotate_credentials", "supported": True, "ood": False},

    # OOD supported
    {"case_id": "soc_eval_027", "input_features": {"severity": "critical", "threat_confidence": "medium", "asset_criticality": "tier1", "lateral_movement": True, "blast_radius": "contained", "internet_exposed": False, "credential_exposure": True, "endpoint_type": "host"}, "expected_action_id": "escalate_p1", "supported": True, "ood": True},
    {"case_id": "soc_eval_028", "input_features": {"severity": "medium", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": True, "blast_radius": "wide", "internet_exposed": True, "credential_exposure": False, "endpoint_type": "cloud_identity"}, "expected_action_id": "isolate_host", "supported": True, "ood": True},
    {"case_id": "soc_eval_029", "input_features": {"severity": "high", "threat_confidence": "medium", "asset_criticality": "tier2", "lateral_movement": False, "blast_radius": "contained", "internet_exposed": True, "credential_exposure": True, "endpoint_type": "edge"}, "expected_action_id": "rotate_credentials", "supported": True, "ood": True},
    {"case_id": "soc_eval_030", "input_features": {"severity": "low", "threat_confidence": "medium", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": True, "credential_exposure": False, "endpoint_type": "cloud_identity"}, "expected_action_id": "block_ip_temporarily", "supported": True, "ood": True},
    {"case_id": "soc_eval_031", "input_features": {"severity": "medium", "threat_confidence": "low", "asset_criticality": "tier1", "lateral_movement": False, "blast_radius": "contained", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "cloud_identity"}, "expected_action_id": "collect_forensics", "supported": True, "ood": True},
    {"case_id": "soc_eval_032", "input_features": {"severity": "low", "threat_confidence": "low", "asset_criticality": "tier2", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": True, "credential_exposure": False, "endpoint_type": "edge"}, "expected_action_id": "monitor_only", "supported": True, "ood": True},
    {"case_id": "soc_eval_033", "input_features": {"severity": "informational", "threat_confidence": "low", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "none", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "server"}, "expected_action_id": "do_nothing_validated", "supported": True, "ood": True},

    # Boundary
    {"case_id": "soc_eval_034", "input_features": {"severity": "high", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": True, "blast_radius": "contained", "internet_exposed": True, "credential_exposure": True, "endpoint_type": "server"}, "expected_action_id": "escalate_p1", "supported": True, "ood": True},
    {"case_id": "soc_eval_035", "input_features": {"severity": "medium", "threat_confidence": "medium", "asset_criticality": "tier2", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": True, "credential_exposure": True, "endpoint_type": "host"}, "expected_action_id": "rotate_credentials", "supported": True, "ood": True},

    # Unsupported
    {"case_id": "soc_eval_036", "input_features": {"severity": "low", "threat_confidence": "low", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "saas"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "soc_eval_037", "input_features": {"severity": "low", "threat_confidence": "low", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "iot"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "soc_eval_038", "input_features": {"severity": "unknown", "threat_confidence": "unknown", "asset_criticality": "unknown", "lateral_movement": "unknown", "blast_radius": "unknown", "internet_exposed": "unknown", "credential_exposure": "unknown", "endpoint_type": "unknown"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "soc_eval_039", "input_features": {}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "soc_eval_040", "input_features": {"severity": "critical", "threat_confidence": "high", "asset_criticality": "tier1", "lateral_movement": True, "blast_radius": "wide", "internet_exposed": True, "credential_exposure": True, "endpoint_type": "quantum_computer"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "soc_eval_041", "input_features": {"severity": "", "threat_confidence": "", "asset_criticality": "", "lateral_movement": "", "blast_radius": "", "internet_exposed": "", "credential_exposure": "", "endpoint_type": ""}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "soc_eval_042", "input_features": {"severity": "low", "threat_confidence": "low", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "hybrid"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "soc_eval_043", "input_features": {"severity": "low", "threat_confidence": "low", "asset_criticality": "tier3", "lateral_movement": False, "blast_radius": "narrow", "internet_exposed": False, "credential_exposure": False, "endpoint_type": "serverless"}, "expected_action_id": None, "supported": False, "ood": True},
]


# ═══════════════════════════════════════════════════════════════════
# DRONE DOMAIN
# ═══════════════════════════════════════════════════════════════════

DRONE_NEW_TRAIN = [
    {"case_id": "drone_train_008", "input_features": {"battery": "high", "comms": "good", "gps": "good", "wind": "medium", "obstacle_density": "medium", "threat_level": "none", "mission_urgency": "high", "payload_criticality": "high"}, "expected_action_id": "continue_mission", "supported": True, "ood": False},
    {"case_id": "drone_train_009", "input_features": {"battery": "low", "comms": "good", "gps": "good", "wind": "medium", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "low", "payload_criticality": "medium"}, "expected_action_id": "return_to_home", "supported": True, "ood": False},
    {"case_id": "drone_train_010", "input_features": {"battery": "medium", "comms": "poor", "gps": "poor", "wind": "high", "obstacle_density": "high", "threat_level": "low", "mission_urgency": "high", "payload_criticality": "high"}, "expected_action_id": "hold_position", "supported": True, "ood": False},
    {"case_id": "drone_train_011", "input_features": {"battery": "high", "comms": "good", "gps": "good", "wind": "low", "obstacle_density": "medium", "threat_level": "high", "mission_urgency": "high", "payload_criticality": "high"}, "expected_action_id": "switch_to_low_observable_path", "supported": True, "ood": False},
    {"case_id": "drone_train_012", "input_features": {"battery": "low", "comms": "degraded", "gps": "good", "wind": "low", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "low", "payload_criticality": "low"}, "expected_action_id": "conserve_battery_mode", "supported": True, "ood": False},
    {"case_id": "drone_train_013", "input_features": {"battery": "medium", "comms": "lost", "gps": "good", "wind": "low", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "medium", "payload_criticality": "medium"}, "expected_action_id": "climb_for_signal_recovery", "supported": True, "ood": False},
    {"case_id": "drone_train_014", "input_features": {"battery": "high", "comms": "good", "gps": "poor", "wind": "severe", "obstacle_density": "high", "threat_level": "low", "mission_urgency": "low", "payload_criticality": "high"}, "expected_action_id": "descend_for_safety", "supported": True, "ood": False},
]

DRONE_NEW_EVAL = [
    # In-distribution supported
    {"case_id": "drone_eval_017", "input_features": {"battery": "high", "comms": "good", "gps": "good", "wind": "low", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "medium", "payload_criticality": "high"}, "expected_action_id": "continue_mission", "supported": True, "ood": False},
    {"case_id": "drone_eval_018", "input_features": {"battery": "critical", "comms": "good", "gps": "good", "wind": "low", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "low", "payload_criticality": "medium"}, "expected_action_id": "return_to_home", "supported": True, "ood": False},
    {"case_id": "drone_eval_019", "input_features": {"battery": "medium", "comms": "poor", "gps": "degraded", "wind": "high", "obstacle_density": "medium", "threat_level": "medium", "mission_urgency": "medium", "payload_criticality": "high"}, "expected_action_id": "hold_position", "supported": True, "ood": False},
    {"case_id": "drone_eval_020", "input_features": {"battery": "medium", "comms": "good", "gps": "good", "wind": "medium", "obstacle_density": "medium", "threat_level": "high", "mission_urgency": "medium", "payload_criticality": "high"}, "expected_action_id": "switch_to_low_observable_path", "supported": True, "ood": False},
    {"case_id": "drone_eval_021", "input_features": {"battery": "low", "comms": "good", "gps": "good", "wind": "low", "obstacle_density": "low", "threat_level": "low", "mission_urgency": "low", "payload_criticality": "medium"}, "expected_action_id": "conserve_battery_mode", "supported": True, "ood": False},
    {"case_id": "drone_eval_022", "input_features": {"battery": "high", "comms": "lost", "gps": "good", "wind": "medium", "obstacle_density": "medium", "threat_level": "none", "mission_urgency": "medium", "payload_criticality": "high"}, "expected_action_id": "climb_for_signal_recovery", "supported": True, "ood": False},
    {"case_id": "drone_eval_023", "input_features": {"battery": "medium", "comms": "good", "gps": "lost", "wind": "severe", "obstacle_density": "high", "threat_level": "medium", "mission_urgency": "low", "payload_criticality": "high"}, "expected_action_id": "descend_for_safety", "supported": True, "ood": False},
    {"case_id": "drone_eval_024", "input_features": {"battery": "high", "comms": "good", "gps": "good", "wind": "high", "obstacle_density": "high", "threat_level": "none", "mission_urgency": "high", "payload_criticality": "medium"}, "expected_action_id": "continue_mission", "supported": True, "ood": False},
    {"case_id": "drone_eval_025", "input_features": {"battery": "critical", "comms": "degraded", "gps": "good", "wind": "medium", "obstacle_density": "medium", "threat_level": "low", "mission_urgency": "low", "payload_criticality": "low"}, "expected_action_id": "return_to_home", "supported": True, "ood": False},
    {"case_id": "drone_eval_026", "input_features": {"battery": "low", "comms": "good", "gps": "good", "wind": "medium", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "medium", "payload_criticality": "medium"}, "expected_action_id": "conserve_battery_mode", "supported": True, "ood": False},

    # OOD supported
    {"case_id": "drone_eval_027", "input_features": {"battery": "medium", "comms": "good", "gps": "good", "wind": "severe", "obstacle_density": "high", "threat_level": "high", "mission_urgency": "high", "payload_criticality": "high"}, "expected_action_id": "hold_position", "supported": True, "ood": True},
    {"case_id": "drone_eval_028", "input_features": {"battery": "critical", "comms": "poor", "gps": "degraded", "wind": "high", "obstacle_density": "high", "threat_level": "medium", "mission_urgency": "low", "payload_criticality": "high"}, "expected_action_id": "return_to_home", "supported": True, "ood": True},
    {"case_id": "drone_eval_029", "input_features": {"battery": "medium", "comms": "good", "gps": "good", "wind": "low", "obstacle_density": "low", "threat_level": "high", "mission_urgency": "low", "payload_criticality": "low"}, "expected_action_id": "switch_to_low_observable_path", "supported": True, "ood": True},
    {"case_id": "drone_eval_030", "input_features": {"battery": "low", "comms": "lost", "gps": "good", "wind": "low", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "low", "payload_criticality": "medium"}, "expected_action_id": "climb_for_signal_recovery", "supported": True, "ood": True},
    {"case_id": "drone_eval_031", "input_features": {"battery": "high", "comms": "good", "gps": "poor", "wind": "high", "obstacle_density": "medium", "threat_level": "low", "mission_urgency": "high", "payload_criticality": "high"}, "expected_action_id": "descend_for_safety", "supported": True, "ood": True},
    {"case_id": "drone_eval_032", "input_features": {"battery": "medium", "comms": "degraded", "gps": "good", "wind": "medium", "obstacle_density": "low", "threat_level": "low", "mission_urgency": "high", "payload_criticality": "high"}, "expected_action_id": "continue_mission", "supported": True, "ood": True},
    {"case_id": "drone_eval_033", "input_features": {"battery": "low", "comms": "good", "gps": "good", "wind": "high", "obstacle_density": "medium", "threat_level": "none", "mission_urgency": "low", "payload_criticality": "high"}, "expected_action_id": "conserve_battery_mode", "supported": True, "ood": True},

    # Boundary
    {"case_id": "drone_eval_034", "input_features": {"battery": "low", "comms": "poor", "gps": "degraded", "wind": "high", "obstacle_density": "high", "threat_level": "medium", "mission_urgency": "high", "payload_criticality": "high"}, "expected_action_id": "hold_position", "supported": True, "ood": True},
    {"case_id": "drone_eval_035", "input_features": {"battery": "critical", "comms": "good", "gps": "good", "wind": "high", "obstacle_density": "medium", "threat_level": "high", "mission_urgency": "medium", "payload_criticality": "high"}, "expected_action_id": "return_to_home", "supported": True, "ood": True},

    # Unsupported / adversarial
    {"case_id": "drone_eval_036", "input_features": {"battery": "critical", "comms": "lost", "gps": "lost", "wind": "severe", "obstacle_density": "high", "threat_level": "high", "mission_urgency": "high", "payload_criticality": "high"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "drone_eval_037", "input_features": {"battery": "unknown", "comms": "good", "gps": "good", "wind": "low", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "low", "payload_criticality": "low"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "drone_eval_038", "input_features": {"battery": "medium", "comms": "lost", "gps": "lost", "wind": "low", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "low", "payload_criticality": "low"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "drone_eval_039", "input_features": {}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "drone_eval_040", "input_features": {"battery": "", "comms": "", "gps": "", "wind": "", "obstacle_density": "", "threat_level": "", "mission_urgency": "", "payload_criticality": ""}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "drone_eval_041", "input_features": {"battery": "high", "comms": "lost", "gps": "lost", "wind": "medium", "obstacle_density": "medium", "threat_level": "low", "mission_urgency": "medium", "payload_criticality": "medium"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "drone_eval_042", "input_features": {"battery": "antimatter", "comms": "quantum", "gps": "temporal", "wind": "solar", "obstacle_density": "hyperdense", "threat_level": "existential", "mission_urgency": "retroactive", "payload_criticality": "classified"}, "expected_action_id": None, "supported": False, "ood": True},
    {"case_id": "drone_eval_043", "input_features": {"battery": "medium", "comms": "good", "gps": "good", "wind": "low", "obstacle_density": "low", "threat_level": "none", "mission_urgency": "low", "payload_criticality": "low"}, "expected_action_id": None, "supported": False, "ood": False},
]


def append_jsonl(path: Path, new_cases: list[dict]):
    existing_ids = set()
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    existing_ids.add(json.loads(line).get("case_id"))
    added = 0
    with open(path, "a") as f:
        for case in new_cases:
            if case["case_id"] not in existing_ids:
                f.write(json.dumps(case, separators=(",", ":")) + "\n")
                added += 1
    return added


def main():
    domains = {
        "sre": {"dir": "sre-policy-router", "new_train": SRE_NEW_TRAIN, "new_eval": SRE_NEW_EVAL},
        "soc": {"dir": "soc-playbook-router", "new_train": SOC_NEW_TRAIN, "new_eval": SOC_NEW_EVAL},
        "drone": {"dir": "drone-mission-router", "new_train": DRONE_NEW_TRAIN, "new_eval": DRONE_NEW_EVAL},
    }
    for domain, cfg in domains.items():
        demo_dir = DEMO_ROOT / cfg["dir"] / "data"
        train_added = append_jsonl(demo_dir / "train_cases.jsonl", cfg["new_train"])
        eval_added = append_jsonl(demo_dir / "cases.jsonl", cfg["new_eval"])
        with open(demo_dir / "train_cases.jsonl") as f:
            train_total = sum(1 for line in f if line.strip())
        with open(demo_dir / "cases.jsonl") as f:
            eval_total = sum(1 for line in f if line.strip())
        print(f"{domain}: +{train_added} train, +{eval_added} eval -> train={train_total}, eval={eval_total}")


if __name__ == "__main__":
    main()
