# KVRM Incident Replay Report

Generated: 2026-04-10T20:23:45.598770+00:00

This replay-style benchmark converts live counterfactual boundary cases into timestamped event-log episodes so the runtime is evaluated as an incident progresses rather than only on isolated snapshots.

Each episode contains baseline operation, a possible supported action switch, an unsupported checkpoint that should fail closed, and a recovery or stabilization checkpoint.

Hybrid comparison summary: wins=3, ties=4, losses=0.

| Domain | Episodes | Switch->Fail->Recover | Fail->Recover->Stabilize | Hybrid Episode Success | Hybrid Episode Regret | Best Non-Hybrid | Baseline Episode Regret | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| drone | 96 | 56 | 40 | 1.0000 | 0.0000 | prototype | 0.0646 | 0.0646 |
Events `drone`: baseline=96, deescalation_switch=1, degradation_switch=53, energy_degradation=1, obstacle_spike=1, recovery=96, stabilize=40, unsupported_checkpoint=96
Sources `drone`: authored=4, counterfactual_derived=92
Hybrid Replay Slices `drone`: authored success=1.0000 regret=0.0000 fail_closed=1.0000; counterfactual_derived success=1.0000 regret=0.0000 fail_closed=1.0000
Features `drone`: airspace_deconfliction_status=37, altitude_headroom=12, autonomous_recovery_allowed=1, battery=85, comms=3, estimated_energy_margin=1, obstacle_density=3, pilot_takeover_link_quality=1, safe_landing_zone_available=3, signal_recovery_confidence=1, threat_level=10

| finance | 21 | 19 | 2 | 1.0000 | 0.0000 | semantic | 0.0095 | 0.0095 |
Events `finance`: baseline=21, compliance_escalation=1, degradation_switch=16, freeze_escalation=1, monitoring_gate=1, recovery=21, stabilize=2, unsupported_checkpoint=21
Sources `finance`: authored=4, counterfactual_derived=17
Hybrid Replay Slices `finance`: authored success=1.0000 regret=0.0000 fail_closed=1.0000; counterfactual_derived success=1.0000 regret=0.0000 fail_closed=1.0000
Features `finance`: account_history=14, anomaly_score=14, document_mismatch=1, kyc_completeness=2, sanctions_hit=8, transaction_amount=1

| grid | 18 | 11 | 7 | 1.0000 | 0.0000 | prototype | 0.0000 | 0.0000 |
Events `grid`: baseline=18, degradation_switch=11, recovery=18, stabilize=7, unsupported_checkpoint=18
Sources `grid`: counterfactual_derived=18
Hybrid Replay Slices `grid`: counterfactual_derived success=1.0000 regret=0.0000 fail_closed=1.0000
Features `grid`: blackstart_required=12, crew_availability=5, customer_impact=4, fault_isolation_ready=4, switching_authorized=1, transfer_path_available=2, weather_risk=1

| iam | 20 | 4 | 16 | 1.0000 | 0.0000 | prototype | 0.0000 | 0.0000 |
Events `iam`: baseline=20, degradation_switch=2, recovery=20, review_gate=1, review_reopen=1, stabilize=16, unsupported_checkpoint=20
Sources `iam`: authored=4, counterfactual_derived=16
Hybrid Replay Slices `iam`: authored success=1.0000 regret=0.0000 fail_closed=1.0000; counterfactual_derived success=1.0000 regret=0.0000 fail_closed=1.0000
Features `iam`: device_posture=16, justification=2, manager_approval=3, requested_privilege=1, requester_risk=1, resource_sensitivity=1, security_review=1, session_scope=4, ticket_state=1

| medical | 18 | 16 | 2 | 1.0000 | 0.0000 | semantic | 0.0000 | 0.0000 |
Events `medical`: baseline=18, degradation_switch=16, recovery=18, stabilize=2, unsupported_checkpoint=18
Sources `medical`: counterfactual_derived=18
Hybrid Replay Slices `medical`: counterfactual_derived success=1.0000 regret=0.0000 fail_closed=1.0000
Features `medical`: acuity_score=24, chest_pain=4, clinician_note_flag=1, fever_bucket=2, focal_neuro_deficit=2, respiratory_distress=1

| soc | 80 | 67 | 13 | 0.9875 | 0.0025 | prototype | 0.0025 | 0.0000 |
Events `soc`: baseline=80, degradation_switch=67, recovery=80, stabilize=13, unsupported_checkpoint=80
Sources `soc`: counterfactual_derived=80
Hybrid Replay Slices `soc`: counterfactual_derived success=0.9875 regret=0.0025 fail_closed=1.0000
Features `soc`: asset_criticality=36, blast_radius=26, credential_exposure=21, endpoint_type=30, internet_exposed=14, lateral_movement=2, severity=16, threat_confidence=2

| sre | 76 | 9 | 67 | 1.0000 | 0.0000 | prototype | 0.0211 | 0.0211 |
Events `sre`: baseline=76, degradation_switch=7, recovery=76, recovery_switch=1, rollback_switch=1, stabilize=67, unsupported_checkpoint=76
Sources `sre`: authored=4, counterfactual_derived=72
Hybrid Replay Slices `sre`: authored success=1.0000 regret=0.0000 fail_closed=1.0000; counterfactual_derived success=1.0000 regret=0.0000 fail_closed=1.0000
Features `sre`: automation_policy_permits_failover=13, capacity_headroom=11, change_failure_blast_radius=9, control_plane_availability=2, dependency_health=21, deploy_regression_suspected=11, deployment_recency=1, error_rate=8, node_locality_score=1, replica_skew=2, rollback_safe=1, write_path_available=6

