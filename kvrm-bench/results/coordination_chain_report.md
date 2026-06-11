# KVRM Coordination Chain Report

Generated: 2026-04-10T20:23:45.659426+00:00

This benchmark composes the cached counterfactual packs into deterministic three-step chains that stress fail-closed behavior, recovery, and action switching in one sequence rather than in isolated adjacent transitions.

Hybrid comparison summary: wins=3, ties=4, losses=0.

| Domain | Chains | Fail->Recover | Switch->Fail | Recover->Switch | Hybrid Success | Hybrid Chain Regret | Best Non-Hybrid | Baseline Chain Regret | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| soc | 214 | 80 | 67 | 67 | 0.9907 | 0.0019 | prototype | 0.0019 | 0.0000 |
Chains `soc`: supported_fail_closed_recovery=80, supported_switch_fail_closed=67, fail_closed_recovery_switch=67
Features `soc`: asset_criticality=103, blast_radius=66, credential_exposure=43, endpoint_type=65, internet_exposed=30, lateral_movement=4, severity=33, threat_confidence=4

| sre | 86 | 72 | 7 | 7 | 1.0000 | 0.0000 | prototype | 0.0326 | 0.0326 |
Chains `sre`: supported_fail_closed_recovery=72, supported_switch_fail_closed=7, fail_closed_recovery_switch=7
Features `sre`: automation_policy_permits_failover=13, capacity_headroom=11, change_failure_blast_radius=23, dependency_health=21, deploy_regression_suspected=10, error_rate=8, replica_skew=4, write_path_available=10

| drone | 198 | 92 | 53 | 53 | 1.0000 | 0.0000 | prototype | 0.0606 | 0.0606 |
Chains `drone`: supported_fail_closed_recovery=92, supported_switch_fail_closed=53, fail_closed_recovery_switch=53
Features `drone`: airspace_deconfliction_status=61, altitude_headroom=29, battery=184, comms=4, obstacle_density=4, safe_landing_zone_available=4, threat_level=18

| grid | 40 | 18 | 11 | 11 | 1.0000 | 0.0000 | prototype | 0.0000 | 0.0000 |
Chains `grid`: supported_fail_closed_recovery=18, supported_switch_fail_closed=11, fail_closed_recovery_switch=11
Features `grid`: blackstart_required=22, crew_availability=14, customer_impact=10, fault_isolation_ready=8, switching_authorized=2, transfer_path_available=4, weather_risk=2

| finance | 49 | 17 | 16 | 16 | 1.0000 | 0.0000 | semantic | 0.0082 | 0.0082 |
Chains `finance`: supported_fail_closed_recovery=17, supported_switch_fail_closed=16, fail_closed_recovery_switch=16
Features `finance`: account_history=39, anomaly_score=26, document_mismatch=2, sanctions_hit=14

| medical | 50 | 18 | 16 | 16 | 1.0000 | 0.0000 | semantic | 0.0000 | 0.0000 |
Chains `medical`: supported_fail_closed_recovery=18, supported_switch_fail_closed=16, fail_closed_recovery_switch=16
Features `medical`: acuity_score=58, chest_pain=11, clinician_note_flag=3, fever_bucket=4, focal_neuro_deficit=4, respiratory_distress=2

| iam | 20 | 16 | 2 | 2 | 1.0000 | 0.0000 | prototype | 0.0000 | 0.0000 |
Chains `iam`: supported_fail_closed_recovery=16, supported_switch_fail_closed=2, fail_closed_recovery_switch=2
Features `iam`: device_posture=20, manager_approval=2, requester_risk=2

