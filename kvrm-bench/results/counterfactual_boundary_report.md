# KVRM Counterfactual Boundary Report

Generated: 2026-04-10T20:23:45.628056+00:00

This benchmark mutates one feature at a time from supported canonical cases, keeping only schema-valid counterfactuals that the registry maps to either exactly one supported non-fallback action or to safe rejection.

Candidate mutation values are derived from the live registry context schema and support-spec boundary values, so the slice stays architecture-native instead of relying on synthetic text prompts.

Generated case packs are cached under `counterfactual_boundary_case_cache/` and reused until the live registry, canonical eval pack, or case-pack version changes.

Hybrid comparison summary: wins=2, ties=5, losses=0.

| Domain | Cases | Supported | Unsupported | Hybrid Correctness | Hybrid Cost | Hybrid Regret | Best Non-Hybrid | Baseline Correctness | Baseline Regret | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| soc | 698 | 110 | 588 | 0.9909 | 0.0005 | 0.0003 | prototype | 0.9909 | 0.0003 | 0.0000 |
Features `soc`: asset_criticality=53, blast_radius=115, credential_exposure=59, endpoint_type=137, internet_exposed=44, lateral_movement=53, severity=198, threat_confidence=39
Expected `soc`: __unsupported__=588, block_ip_temporarily=7, collect_forensics=34, do_nothing_validated=4, escalate_p1=11, isolate_host=19, monitor_only=31, rotate_credentials=4

| sre | 1976 | 21 | 1955 | 1.0000 | 0.0000 | 0.0000 | semantic | 1.0000 | 0.0000 | 0.0000 |
Features `sre`: automation_policy_permits_failover=13, capacity_headroom=38, change_failure_blast_radius=42, control_plane_availability=44, cross_region_read_staleness=39, dependency_health=90, deploy_regression_suspected=50, deployment_recency=22, error_rate=82, failover_ready=13, fault_scope=144, latency=121, mitigation_window_remaining=15, node_locality_score=198, operator_approval_required=13, operator_response_eta=15, quorum_health=44, recent_restart_attempts=111, region_health=24, replica_skew=617, replication_lag=44, rollback_safe=18, runbook_coordination_required=22, saturation=61, secondary_capacity_ready=13, telemetry_confidence=24, write_path_available=59
Expected `sre`: __unsupported__=1955, restart_service=16, scale_out=5

| drone | 1518 | 120 | 1398 | 1.0000 | 0.0000 | 0.0000 | semantic | 0.8250 | 0.0028 | 0.0028 |
Features `drone`: airspace_deconfliction_status=70, altitude_headroom=33, autonomous_recovery_allowed=22, battery=197, comms=193, distance_to_home=22, estimated_energy_margin=35, gps=198, mission_progress=22, mission_replan_budget=34, mission_urgency=35, obstacle_density=89, operator_control_latency_budget=34, payload_criticality=34, pilot_response_eta=21, pilot_takeover_link_quality=32, rules_of_engagement_state=70, safe_landing_zone_available=33, signal_recovery_confidence=43, takeover_window_remaining=21, terrain_occlusion_level=33, threat_level=157, wind=90
Expected `drone`: __unsupported__=1398, conserve_battery_mode=28, continue_mission=21, hold_position=25, return_to_home=46

| grid | 236 | 14 | 222 | 1.0000 | 0.0000 | 0.0000 | prototype | 1.0000 | 0.0000 | 0.0000 |
Features `grid`: blackstart_required=12, crew_availability=8, customer_impact=40, fault_isolation_ready=6, frequency_deviation=24, outage_scope=44, relay_state=16, reserve_margin=18, switching_authorized=12, transfer_path_available=18, voltage_stability=26, weather_risk=12
Expected `grid`: __unsupported__=222, dispatch_field_crew=6, isolate_faulted_feeder=2, prepare_blackstart=2, shed_noncritical_load=3, transfer_load=1

| finance | 191 | 58 | 133 | 1.0000 | 0.0000 | 0.0000 | semantic | 0.9655 | 0.0021 | 0.0021 |
Features `finance`: account_history=19, anomaly_score=41, device_trust=16, document_mismatch=13, jurisdiction_risk=13, kyc_completeness=26, sanctions_hit=16, transaction_amount=22, velocity_indicator=25
Expected `finance`: __unsupported__=133, allow_with_monitoring=8, enhanced_due_diligence=16, escalate_compliance=16, freeze_for_investigation=2, lower_limit_temporarily=7, require_additional_docs=9

| medical | 160 | 36 | 124 | 1.0000 | 0.0000 | 0.0000 | semantic | 1.0000 | 0.0000 | 0.0000 |
Features `medical`: acuity_score=40, age_bracket=5, chest_pain=12, clinician_note_flag=29, fever_bucket=15, focal_neuro_deficit=16, hypotension=10, infection_risk=15, respiratory_distress=10, symptom_onset=8
Expected `medical`: __unsupported__=124, cardiac_chest_pain_pathway=1, lab_panel_priority_order=4, respiratory_support_pathway=12, routine_review=2, sepsis_screen_pathway=1, stroke_alert_pathway=3, urgent_clinician_review=13

| iam | 419 | 3 | 416 | 1.0000 | 0.0000 | 0.0000 | prototype | 1.0000 | 0.0000 | 0.0000 |
Features `iam`: device_posture=32, justification=50, manager_approval=31, mfa_state=32, on_call_role=28, requested_privilege=32, requester_risk=28, resource_sensitivity=42, security_review=48, session_scope=32, sod_risk=32, ticket_state=32
Expected `iam`: __unsupported__=416, auto_approve_standard_access=1, grant_timeboxed_privileged_access=2

