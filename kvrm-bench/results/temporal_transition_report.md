# KVRM Temporal Transition Report

Generated: 2026-04-10T20:23:45.682468+00:00

This benchmark lifts the cached single-step counterfactual pack into deterministic two-step temporal transitions. It measures whether each strategy stays safe when a supported state slides into unsupported territory, recovers cleanly when support returns, and switches actions correctly when the supported target changes across time.

Hybrid comparison summary: wins=3, ties=4, losses=0.

| Domain | Sequences | Recovery | Fail-Closed | Switch | Hybrid Success | Hybrid Seq Regret | Best Non-Hybrid | Baseline Seq Regret | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| soc | 775 | 341 | 341 | 93 | 0.9987 | 0.0003 | prototype | 0.0003 | 0.0000 |
Transitions `soc`: supported_action_switch=93, supported_to_unsupported_fail_closed=341, unsupported_to_supported_recovery=341
Features `soc`: asset_criticality=71, blast_radius=70, credential_exposure=108, endpoint_type=135, internet_exposed=71, lateral_movement=103, severity=154, threat_confidence=63

| sre | 1537 | 765 | 765 | 7 | 1.0000 | 0.0000 | prototype | 0.0009 | 0.0009 |
Transitions `sre`: supported_action_switch=7, supported_to_unsupported_fail_closed=765, unsupported_to_supported_recovery=765
Features `sre`: automation_policy_permits_failover=26, capacity_headroom=38, change_failure_blast_radius=34, control_plane_availability=44, cross_region_read_staleness=44, dependency_health=90, deploy_regression_suspected=100, deployment_recency=32, error_rate=78, failover_ready=26, fault_scope=144, latency=114, mitigation_window_remaining=16, node_locality_score=58, operator_approval_required=26, operator_response_eta=16, quorum_health=44, recent_restart_attempts=58, region_health=24, replica_skew=146, replication_lag=44, rollback_safe=36, runbook_coordination_required=44, saturation=84, secondary_capacity_ready=26, telemetry_confidence=32, write_path_available=113

| drone | 1656 | 788 | 788 | 80 | 1.0000 | 0.0000 | prototype | 0.0053 | 0.0053 |
Transitions `drone`: supported_action_switch=80, supported_to_unsupported_fail_closed=788, unsupported_to_supported_recovery=788
Features `drone`: airspace_deconfliction_status=70, altitude_headroom=44, autonomous_recovery_allowed=44, battery=196, comms=183, distance_to_home=22, estimated_energy_margin=35, gps=178, mission_progress=22, mission_replan_budget=46, mission_urgency=48, obstacle_density=124, operator_control_latency_budget=48, payload_criticality=46, pilot_response_eta=22, pilot_takeover_link_quality=22, rules_of_engagement_state=70, safe_landing_zone_available=64, signal_recovery_confidence=51, takeover_window_remaining=22, terrain_occlusion_level=44, threat_level=165, wind=90

| grid | 292 | 140 | 140 | 12 | 1.0000 | 0.0000 | prototype | 0.0000 | 0.0000 |
Transitions `grid`: supported_action_switch=12, supported_to_unsupported_fail_closed=140, unsupported_to_supported_recovery=140
Features `grid`: blackstart_required=22, crew_availability=11, customer_impact=36, fault_isolation_ready=8, frequency_deviation=28, outage_scope=36, relay_state=24, reserve_margin=24, switching_authorized=23, transfer_path_available=33, voltage_stability=32, weather_risk=15

| finance | 212 | 82 | 82 | 48 | 1.0000 | 0.0000 | semantic | 0.0019 | 0.0019 |
Transitions `finance`: supported_action_switch=48, supported_to_unsupported_fail_closed=82, unsupported_to_supported_recovery=82
Features `finance`: account_history=25, anomaly_score=40, device_trust=27, document_mismatch=23, jurisdiction_risk=15, kyc_completeness=23, sanctions_hit=16, transaction_amount=15, velocity_indicator=28

| medical | 184 | 79 | 79 | 26 | 1.0000 | 0.0000 | semantic | 0.0000 | 0.0000 |
Transitions `medical`: supported_action_switch=26, supported_to_unsupported_fail_closed=79, unsupported_to_supported_recovery=79
Features `medical`: acuity_score=38, age_bracket=6, chest_pain=22, clinician_note_flag=16, fever_bucket=15, focal_neuro_deficit=29, hypotension=20, infection_risk=14, respiratory_distress=15, symptom_onset=9

| iam | 376 | 187 | 187 | 2 | 1.0000 | 0.0000 | prototype | 0.0000 | 0.0000 |
Transitions `iam`: supported_action_switch=2, supported_to_unsupported_fail_closed=187, unsupported_to_supported_recovery=187
Features `iam`: device_posture=32, justification=28, manager_approval=31, mfa_state=32, on_call_role=32, requested_privilege=32, requester_risk=31, resource_sensitivity=30, security_review=32, session_scope=32, sod_risk=32, ticket_state=32

