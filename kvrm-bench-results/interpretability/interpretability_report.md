# KVRM Feature Interpretability Report

Generated: 2026-04-13T02:07:02.861108+00:00

This report shows RandomForest feature importances (mean decrease in impurity) for each domain's compact learned selector.  Features are ranked by their contribution to decision-making.  Per-action importances show which features matter most for routing to each specific action.

**Analyzed domains**: 9 / 9  
**Skipped**: 0

## content_moderation

**Features**: 8 | **Actions**: 7 | **Estimators**: 256 | **Train cases**: 31 | **Train accuracy**: 1.0000

### Global Feature Importances

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | toxicity_level | 0.2037 |
| 2 | user_trust_score | 0.1317 |
| 3 | recidivism_risk | 0.1195 |
| 4 | reporter_credibility | 0.1192 |
| 5 | context_sensitivity | 0.1176 |
| 6 | content_type | 0.1172 |
| 7 | audience_reach | 0.1120 |
| 8 | content_age_hours | 0.0791 |

### Per-Action Top Features

| Action | Top Features |
| --- | --- |
| auto_approve | toxicity_level (0.272), user_trust_score (0.139), audience_reach (0.114), content_type (0.108), recidivism_risk (0.105) |
| escalate_trust_safety | toxicity_level (0.163), content_type (0.155), user_trust_score (0.137), context_sensitivity (0.136), recidivism_risk (0.118) |
| flag_for_human_review | toxicity_level (0.179), recidivism_risk (0.141), context_sensitivity (0.137), user_trust_score (0.128), reporter_credibility (0.118) |
| reduce_visibility | toxicity_level (0.202), user_trust_score (0.147), audience_reach (0.140), reporter_credibility (0.116), recidivism_risk (0.116) |
| remove_content | toxicity_level (0.176), content_type (0.159), reporter_credibility (0.122), context_sensitivity (0.120), recidivism_risk (0.117) |
| request_human_review | toxicity_level (0.212), user_trust_score (0.172), reporter_credibility (0.126), audience_reach (0.124), context_sensitivity (0.110) |
| suspend_account | toxicity_level (0.178), recidivism_risk (0.158), content_type (0.124), context_sensitivity (0.121), user_trust_score (0.119) |

## customer_support

**Features**: 8 | **Actions**: 7 | **Estimators**: 256 | **Train cases**: 25 | **Train accuracy**: 1.0000

### Global Feature Importances

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | resolution_complexity | 0.2044 |
| 2 | issue_category | 0.1877 |
| 3 | sentiment | 0.1622 |
| 4 | prior_contacts | 0.1367 |
| 5 | customer_tier | 0.1282 |
| 6 | account_age_days | 0.0902 |
| 7 | escalation_history | 0.0671 |
| 8 | has_open_ticket | 0.0234 |

### Per-Action Top Features

| Action | Top Features |
| --- | --- |
| assign_specialist | resolution_complexity (0.222), issue_category (0.189), sentiment (0.147), customer_tier (0.118), prior_contacts (0.113) |
| auto_resolve_billing | issue_category (0.203), resolution_complexity (0.183), sentiment (0.146), prior_contacts (0.145), customer_tier (0.134) |
| escalate_to_manager | resolution_complexity (0.243), issue_category (0.166), sentiment (0.143), customer_tier (0.125), prior_contacts (0.109) |
| issue_refund | resolution_complexity (0.258), prior_contacts (0.165), sentiment (0.159), issue_category (0.154), customer_tier (0.103) |
| request_human_review | issue_category (0.229), resolution_complexity (0.184), sentiment (0.171), customer_tier (0.142), account_age_days (0.089) |
| schedule_callback | resolution_complexity (0.181), issue_category (0.171), prior_contacts (0.150), sentiment (0.135), customer_tier (0.126) |
| send_knowledge_article | sentiment (0.240), resolution_complexity (0.221), prior_contacts (0.156), issue_category (0.134), customer_tier (0.120) |

## drone

**Features**: 23 | **Actions**: 8 | **Estimators**: 256 | **Train cases**: 25 | **Train accuracy**: 1.0000

### Global Feature Importances

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | distance_to_home | 0.0844 |
| 2 | mission_replan_budget | 0.0844 |
| 3 | airspace_deconfliction_status | 0.0634 |
| 4 | estimated_energy_margin | 0.0572 |
| 5 | signal_recovery_confidence | 0.0569 |
| 6 | rules_of_engagement_state | 0.0542 |
| 7 | threat_level | 0.0524 |
| 8 | terrain_occlusion_level | 0.0510 |
| 9 | battery | 0.0504 |
| 10 | pilot_takeover_link_quality | 0.0446 |
| 11 | mission_progress | 0.0435 |
| 12 | operator_control_latency_budget | 0.0415 |
| 13 | mission_urgency | 0.0412 |
| 14 | altitude_headroom | 0.0388 |
| 15 | obstacle_density | 0.0383 |
| 16 | wind | 0.0375 |
| 17 | comms | 0.0306 |
| 18 | gps | 0.0295 |
| 19 | payload_criticality | 0.0289 |
| 20 | safe_landing_zone_available | 0.0216 |
| 21 | takeover_window_remaining | 0.0211 |
| 22 | pilot_response_eta | 0.0180 |
| 23 | autonomous_recovery_allowed | 0.0105 |

### Per-Action Top Features

| Action | Top Features |
| --- | --- |
| climb_for_signal_recovery | distance_to_home (0.096), mission_urgency (0.067), terrain_occlusion_level (0.067), battery (0.064), mission_replan_budget (0.064) |
| conserve_battery_mode | distance_to_home (0.147), mission_replan_budget (0.088), battery (0.084), signal_recovery_confidence (0.075), mission_progress (0.063) |
| continue_mission | distance_to_home (0.099), mission_replan_budget (0.077), terrain_occlusion_level (0.076), threat_level (0.069), battery (0.067) |
| descend_for_safety | airspace_deconfliction_status (0.132), rules_of_engagement_state (0.106), wind (0.080), safe_landing_zone_available (0.070), gps (0.066) |
| hold_position | airspace_deconfliction_status (0.117), rules_of_engagement_state (0.095), pilot_takeover_link_quality (0.073), mission_replan_budget (0.072), wind (0.068) |
| manual_handoff | mission_replan_budget (0.106), airspace_deconfliction_status (0.092), pilot_takeover_link_quality (0.088), rules_of_engagement_state (0.071), takeover_window_remaining (0.068) |
| return_to_home | mission_replan_budget (0.104), distance_to_home (0.098), estimated_energy_margin (0.081), signal_recovery_confidence (0.077), mission_progress (0.074) |
| switch_to_low_observable_path | mission_replan_budget (0.109), distance_to_home (0.085), terrain_occlusion_level (0.073), operator_control_latency_budget (0.071), threat_level (0.065) |

## finance

**Features**: 9 | **Actions**: 8 | **Estimators**: 256 | **Train cases**: 13 | **Train accuracy**: 1.0000

### Global Feature Importances

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | account_history | 0.1665 |
| 2 | anomaly_score | 0.1656 |
| 3 | velocity_indicator | 0.1426 |
| 4 | device_trust | 0.1279 |
| 5 | transaction_amount | 0.1271 |
| 6 | jurisdiction_risk | 0.1143 |
| 7 | kyc_completeness | 0.0816 |
| 8 | document_mismatch | 0.0563 |
| 9 | sanctions_hit | 0.0181 |

### Per-Action Top Features

| Action | Top Features |
| --- | --- |
| allow_with_monitoring | transaction_amount (0.195), account_history (0.181), anomaly_score (0.138), device_trust (0.137), velocity_indicator (0.131) |
| approve_low_risk | anomaly_score (0.191), jurisdiction_risk (0.170), transaction_amount (0.160), account_history (0.139), velocity_indicator (0.123) |
| enhanced_due_diligence | transaction_amount (0.174), jurisdiction_risk (0.172), account_history (0.170), anomaly_score (0.142), velocity_indicator (0.135) |
| escalate_compliance | anomaly_score (0.218), kyc_completeness (0.154), velocity_indicator (0.134), account_history (0.099), document_mismatch (0.088) |
| freeze_for_investigation | account_history (0.224), velocity_indicator (0.187), device_trust (0.171), anomaly_score (0.167), jurisdiction_risk (0.072) |
| lower_limit_temporarily | account_history (0.218), velocity_indicator (0.204), device_trust (0.175), anomaly_score (0.156), jurisdiction_risk (0.090) |
| manual_review | anomaly_score (0.196), account_history (0.171), device_trust (0.152), velocity_indicator (0.150), transaction_amount (0.105) |
| require_additional_docs | kyc_completeness (0.165), document_mismatch (0.129), account_history (0.124), anomaly_score (0.123), jurisdiction_risk (0.122) |

## grid

**Features**: 12 | **Actions**: 8 | **Estimators**: 256 | **Train cases**: 16 | **Train accuracy**: 1.0000

### Global Feature Importances

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | weather_risk | 0.1391 |
| 2 | outage_scope | 0.1242 |
| 3 | frequency_deviation | 0.0953 |
| 4 | customer_impact | 0.0887 |
| 5 | voltage_stability | 0.0867 |
| 6 | relay_state | 0.0863 |
| 7 | crew_availability | 0.0825 |
| 8 | reserve_margin | 0.0818 |
| 9 | fault_isolation_ready | 0.0755 |
| 10 | transfer_path_available | 0.0592 |
| 11 | switching_authorized | 0.0447 |
| 12 | blackstart_required | 0.0359 |

### Per-Action Top Features

| Action | Top Features |
| --- | --- |
| continue_monitoring | outage_scope (0.199), relay_state (0.153), customer_impact (0.106), frequency_deviation (0.090), voltage_stability (0.086) |
| defer_switching_due_weather | weather_risk (0.213), frequency_deviation (0.114), outage_scope (0.109), fault_isolation_ready (0.103), switching_authorized (0.076) |
| dispatch_field_crew | weather_risk (0.136), outage_scope (0.124), customer_impact (0.103), fault_isolation_ready (0.098), frequency_deviation (0.097) |
| escalate_grid_supervisor | weather_risk (0.200), crew_availability (0.139), outage_scope (0.098), frequency_deviation (0.093), relay_state (0.091) |
| isolate_faulted_feeder | outage_scope (0.134), weather_risk (0.128), fault_isolation_ready (0.121), frequency_deviation (0.107), reserve_margin (0.096) |
| prepare_blackstart | weather_risk (0.160), crew_availability (0.135), outage_scope (0.125), blackstart_required (0.089), voltage_stability (0.088) |
| shed_noncritical_load | outage_scope (0.124), weather_risk (0.117), voltage_stability (0.109), crew_availability (0.101), frequency_deviation (0.099) |
| transfer_load | transfer_path_available (0.158), reserve_margin (0.116), outage_scope (0.110), weather_risk (0.102), frequency_deviation (0.092) |

## iam

**Features**: 12 | **Actions**: 7 | **Estimators**: 256 | **Train cases**: 15 | **Train accuracy**: 1.0000

### Global Feature Importances

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | security_review | 0.1176 |
| 2 | requester_risk | 0.1107 |
| 3 | manager_approval | 0.1055 |
| 4 | justification | 0.0981 |
| 5 | session_scope | 0.0906 |
| 6 | requested_privilege | 0.0882 |
| 7 | device_posture | 0.0877 |
| 8 | resource_sensitivity | 0.0832 |
| 9 | sod_risk | 0.0717 |
| 10 | on_call_role | 0.0712 |
| 11 | mfa_state | 0.0457 |
| 12 | ticket_state | 0.0297 |

### Per-Action Top Features

| Action | Top Features |
| --- | --- |
| auto_approve_standard_access | manager_approval (0.222), security_review (0.120), resource_sensitivity (0.119), requested_privilege (0.105), session_scope (0.104) |
| deny_request | requester_risk (0.171), security_review (0.110), device_posture (0.091), mfa_state (0.090), requested_privilege (0.084) |
| escalate_identity_admin | device_posture (0.190), requested_privilege (0.123), security_review (0.111), requester_risk (0.105), resource_sensitivity (0.090) |
| grant_break_glass_access | session_scope (0.204), justification (0.184), on_call_role (0.137), security_review (0.097), sod_risk (0.073) |
| grant_timeboxed_privileged_access | requester_risk (0.206), security_review (0.120), requested_privilege (0.112), resource_sensitivity (0.089), device_posture (0.083) |
| require_manager_approval | manager_approval (0.258), security_review (0.139), resource_sensitivity (0.111), justification (0.100), session_scope (0.080) |
| require_security_review | mfa_state (0.147), security_review (0.131), sod_risk (0.119), session_scope (0.100), justification (0.090) |

## medical

**Features**: 10 | **Actions**: 8 | **Estimators**: 256 | **Train cases**: 12 | **Train accuracy**: 1.0000

### Global Feature Importances

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | clinician_note_flag | 0.1893 |
| 2 | symptom_onset | 0.1809 |
| 3 | infection_risk | 0.1386 |
| 4 | fever_bucket | 0.1284 |
| 5 | acuity_score | 0.1206 |
| 6 | age_bracket | 0.0654 |
| 7 | chest_pain | 0.0562 |
| 8 | respiratory_distress | 0.0560 |
| 9 | focal_neuro_deficit | 0.0512 |
| 10 | hypotension | 0.0132 |

### Per-Action Top Features

| Action | Top Features |
| --- | --- |
| cardiac_chest_pain_pathway | clinician_note_flag (0.275), symptom_onset (0.176), acuity_score (0.147), fever_bucket (0.103), chest_pain (0.088) |
| escalate_supervisor_review | clinician_note_flag (0.211), symptom_onset (0.170), fever_bucket (0.122), focal_neuro_deficit (0.115), infection_risk (0.107) |
| lab_panel_priority_order | infection_risk (0.221), acuity_score (0.155), clinician_note_flag (0.146), fever_bucket (0.140), symptom_onset (0.134) |
| respiratory_support_pathway | symptom_onset (0.192), infection_risk (0.166), clinician_note_flag (0.147), fever_bucket (0.136), acuity_score (0.128) |
| routine_review | symptom_onset (0.191), clinician_note_flag (0.171), infection_risk (0.162), acuity_score (0.139), fever_bucket (0.132) |
| sepsis_screen_pathway | clinician_note_flag (0.251), fever_bucket (0.199), symptom_onset (0.136), infection_risk (0.132), acuity_score (0.072) |
| stroke_alert_pathway | clinician_note_flag (0.228), symptom_onset (0.217), acuity_score (0.143), fever_bucket (0.096), focal_neuro_deficit (0.084) |
| urgent_clinician_review | symptom_onset (0.220), clinician_note_flag (0.159), infection_risk (0.117), fever_bucket (0.114), focal_neuro_deficit (0.097) |

## soc

**Features**: 8 | **Actions**: 7 | **Estimators**: 256 | **Train cases**: 14 | **Train accuracy**: 1.0000

### Global Feature Importances

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | severity | 0.3064 |
| 2 | blast_radius | 0.1496 |
| 3 | endpoint_type | 0.1269 |
| 4 | threat_confidence | 0.1259 |
| 5 | asset_criticality | 0.1088 |
| 6 | internet_exposed | 0.0656 |
| 7 | credential_exposure | 0.0587 |
| 8 | lateral_movement | 0.0580 |

### Per-Action Top Features

| Action | Top Features |
| --- | --- |
| block_ip_temporarily | severity (0.223), endpoint_type (0.223), threat_confidence (0.166), blast_radius (0.129), internet_exposed (0.102) |
| collect_forensics | severity (0.333), threat_confidence (0.148), endpoint_type (0.133), blast_radius (0.111), asset_criticality (0.109) |
| do_nothing_validated | severity (0.354), blast_radius (0.249), threat_confidence (0.140), asset_criticality (0.084), endpoint_type (0.069) |
| escalate_p1 | severity (0.296), lateral_movement (0.169), blast_radius (0.133), asset_criticality (0.094), threat_confidence (0.088) |
| isolate_host | severity (0.282), blast_radius (0.154), endpoint_type (0.144), threat_confidence (0.127), asset_criticality (0.096) |
| monitor_only | severity (0.413), blast_radius (0.154), endpoint_type (0.105), threat_confidence (0.104), asset_criticality (0.096) |
| rotate_credentials | severity (0.272), asset_criticality (0.141), endpoint_type (0.126), blast_radius (0.121), threat_confidence (0.118) |

## sre

**Features**: 27 | **Actions**: 8 | **Estimators**: 256 | **Train cases**: 24 | **Train accuracy**: 1.0000

### Global Feature Importances

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | error_rate | 0.0785 |
| 2 | change_failure_blast_radius | 0.0780 |
| 3 | capacity_headroom | 0.0711 |
| 4 | cross_region_read_staleness | 0.0662 |
| 5 | fault_scope | 0.0619 |
| 6 | control_plane_availability | 0.0602 |
| 7 | replica_skew | 0.0591 |
| 8 | quorum_health | 0.0537 |
| 9 | node_locality_score | 0.0501 |
| 10 | saturation | 0.0483 |
| 11 | dependency_health | 0.0475 |
| 12 | replication_lag | 0.0467 |
| 13 | deployment_recency | 0.0383 |
| 14 | region_health | 0.0322 |
| 15 | telemetry_confidence | 0.0271 |
| 16 | rollback_safe | 0.0226 |
| 17 | mitigation_window_remaining | 0.0209 |
| 18 | automation_policy_permits_failover | 0.0177 |
| 19 | recent_restart_attempts | 0.0167 |
| 20 | deploy_regression_suspected | 0.0160 |
| 21 | failover_ready | 0.0149 |
| 22 | runbook_coordination_required | 0.0142 |
| 23 | latency | 0.0141 |
| 24 | operator_response_eta | 0.0136 |
| 25 | write_path_available | 0.0111 |
| 26 | secondary_capacity_ready | 0.0103 |
| 27 | operator_approval_required | 0.0091 |

### Per-Action Top Features

| Action | Top Features |
| --- | --- |
| drain_node | fault_scope (0.109), change_failure_blast_radius (0.101), error_rate (0.072), saturation (0.068), dependency_health (0.057) |
| enable_readonly_mode | control_plane_availability (0.121), change_failure_blast_radius (0.088), cross_region_read_staleness (0.075), capacity_headroom (0.068), quorum_health (0.061) |
| failover_region | cross_region_read_staleness (0.075), capacity_headroom (0.075), change_failure_blast_radius (0.067), control_plane_availability (0.065), replica_skew (0.057) |
| gather_more_telemetry | error_rate (0.114), capacity_headroom (0.098), change_failure_blast_radius (0.077), replica_skew (0.065), node_locality_score (0.056) |
| page_human_operator | control_plane_availability (0.099), cross_region_read_staleness (0.072), change_failure_blast_radius (0.070), quorum_health (0.065), mitigation_window_remaining (0.064) |
| restart_service | cross_region_read_staleness (0.095), control_plane_availability (0.083), change_failure_blast_radius (0.078), fault_scope (0.074), error_rate (0.072) |
| rollback_deploy | deployment_recency (0.083), change_failure_blast_radius (0.074), replica_skew (0.071), error_rate (0.069), capacity_headroom (0.062) |
| scale_out | error_rate (0.094), capacity_headroom (0.077), change_failure_blast_radius (0.074), saturation (0.072), fault_scope (0.063) |

