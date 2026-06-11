# KVRM SHAP Directional Feature Analysis

Generated: 2026-04-13T03:02:03.186824+00:00

This report shows SHAP (SHapley Additive exPlanations) values for each domain's compact learned selector. Unlike standard feature importances, SHAP values reveal the **direction** of each feature's influence: does a feature push toward or away from a particular action?

**Analyzed domains**: 9 / 9  
**Skipped**: 0

## content_moderation

**Features**: 8 | **Actions**: 7 | **Samples**: 31 | **Method**: TreeExplainer

### Global SHAP Importances (mean |SHAP|)

| Rank | Feature | SHAP Importance |
| ---: | --- | ---: |
| 1 | toxicity_level | 0.2277 |
| 2 | user_trust_score | 0.1334 |
| 3 | recidivism_risk | 0.1270 |
| 4 | context_sensitivity | 0.1244 |
| 5 | audience_reach | 0.1234 |
| 6 | reporter_credibility | 0.1172 |
| 7 | content_type | 0.0875 |
| 8 | content_age_hours | 0.0595 |

### Per-Action Feature Directions

Shows which features push toward (+) or away from (-) each action.

**auto_approve**:
  - - toxicity_level (SHAP: -0.0233)
  - - audience_reach (SHAP: -0.0068)
  - ~ recidivism_risk (SHAP: +0.0006)
  - - reporter_credibility (SHAP: -0.0056)
  - - user_trust_score (SHAP: -0.0066)

**escalate_trust_safety**:
  - ~ context_sensitivity (SHAP: +0.0008)
  - + user_trust_score (SHAP: +0.0070)
  - + toxicity_level (SHAP: +0.0127)
  - + reporter_credibility (SHAP: +0.0101)
  - + recidivism_risk (SHAP: +0.0025)

**flag_for_human_review**:
  - ~ toxicity_level (SHAP: +0.0006)
  - - context_sensitivity (SHAP: -0.0047)
  - - recidivism_risk (SHAP: -0.0031)
  - - reporter_credibility (SHAP: -0.0013)
  - + audience_reach (SHAP: +0.0028)

**reduce_visibility**:
  - - toxicity_level (SHAP: -0.0127)
  - - audience_reach (SHAP: -0.0061)
  - - user_trust_score (SHAP: -0.0017)
  - - recidivism_risk (SHAP: -0.0042)
  - - reporter_credibility (SHAP: -0.0087)

**remove_content**:
  - + toxicity_level (SHAP: +0.0144)
  - + context_sensitivity (SHAP: +0.0011)
  - + content_type (SHAP: +0.0080)
  - + reporter_credibility (SHAP: +0.0108)
  - + recidivism_risk (SHAP: +0.0059)

**request_human_review**:
  - - toxicity_level (SHAP: -0.0013)
  - - user_trust_score (SHAP: -0.0044)
  - - reporter_credibility (SHAP: -0.0064)
  - - audience_reach (SHAP: -0.0031)
  - ~ content_age_hours (SHAP: -0.0009)

**suspend_account**:
  - ~ recidivism_risk (SHAP: -0.0008)
  - + toxicity_level (SHAP: +0.0096)
  - + user_trust_score (SHAP: +0.0043)
  - + context_sensitivity (SHAP: +0.0054)
  - ~ audience_reach (SHAP: -0.0006)

## customer_support

**Features**: 8 | **Actions**: 7 | **Samples**: 25 | **Method**: TreeExplainer

### Global SHAP Importances (mean |SHAP|)

| Rank | Feature | SHAP Importance |
| ---: | --- | ---: |
| 1 | resolution_complexity | 0.2328 |
| 2 | sentiment | 0.1810 |
| 3 | issue_category | 0.1807 |
| 4 | prior_contacts | 0.1379 |
| 5 | customer_tier | 0.1091 |
| 6 | escalation_history | 0.0685 |
| 7 | account_age_days | 0.0642 |
| 8 | has_open_ticket | 0.0259 |

### Per-Action Feature Directions

Shows which features push toward (+) or away from (-) each action.

**assign_specialist**:
  - ~ resolution_complexity (SHAP: -0.0003)
  - ~ issue_category (SHAP: +0.0001)
  - - sentiment (SHAP: -0.0050)
  - + customer_tier (SHAP: +0.0029)
  - ~ prior_contacts (SHAP: -0.0007)

**auto_resolve_billing**:
  - ~ issue_category (SHAP: -0.0006)
  - ~ sentiment (SHAP: +0.0009)
  - ~ prior_contacts (SHAP: +0.0008)
  - - resolution_complexity (SHAP: -0.0036)
  - ~ escalation_history (SHAP: -0.0010)

**escalate_to_manager**:
  - + resolution_complexity (SHAP: +0.0240)
  - + sentiment (SHAP: +0.0196)
  - + issue_category (SHAP: +0.0248)
  - + escalation_history (SHAP: +0.0060)
  - + customer_tier (SHAP: +0.0158)

**issue_refund**:
  - - resolution_complexity (SHAP: -0.0175)
  - - prior_contacts (SHAP: -0.0057)
  - + sentiment (SHAP: +0.0054)
  - - issue_category (SHAP: -0.0067)
  - + customer_tier (SHAP: +0.0010)

**request_human_review**:
  - - issue_category (SHAP: -0.0166)
  - - customer_tier (SHAP: -0.0082)
  - + resolution_complexity (SHAP: +0.0036)
  - - sentiment (SHAP: -0.0069)
  - - account_age_days (SHAP: -0.0040)

**schedule_callback**:
  - - prior_contacts (SHAP: -0.0027)
  - + resolution_complexity (SHAP: +0.0012)
  - + sentiment (SHAP: +0.0010)
  - ~ issue_category (SHAP: -0.0009)
  - - customer_tier (SHAP: -0.0059)

**send_knowledge_article**:
  - - resolution_complexity (SHAP: -0.0075)
  - - sentiment (SHAP: -0.0151)
  - - prior_contacts (SHAP: -0.0028)
  - - customer_tier (SHAP: -0.0024)
  - ~ issue_category (SHAP: -0.0001)

## drone

**Features**: 23 | **Actions**: 8 | **Samples**: 25 | **Method**: TreeExplainer

### Global SHAP Importances (mean |SHAP|)

| Rank | Feature | SHAP Importance |
| ---: | --- | ---: |
| 1 | mission_replan_budget | 0.0924 |
| 2 | distance_to_home | 0.0867 |
| 3 | airspace_deconfliction_status | 0.0719 |
| 4 | signal_recovery_confidence | 0.0705 |
| 5 | rules_of_engagement_state | 0.0627 |
| 6 | pilot_takeover_link_quality | 0.0565 |
| 7 | terrain_occlusion_level | 0.0484 |
| 8 | threat_level | 0.0481 |
| 9 | estimated_energy_margin | 0.0467 |
| 10 | operator_control_latency_budget | 0.0466 |
| 11 | obstacle_density | 0.0458 |
| 12 | battery | 0.0440 |
| 13 | altitude_headroom | 0.0436 |
| 14 | mission_progress | 0.0386 |
| 15 | mission_urgency | 0.0327 |
| 16 | wind | 0.0295 |
| 17 | gps | 0.0263 |
| 18 | payload_criticality | 0.0238 |
| 19 | comms | 0.0236 |
| 20 | safe_landing_zone_available | 0.0197 |
| 21 | takeover_window_remaining | 0.0175 |
| 22 | pilot_response_eta | 0.0145 |
| 23 | autonomous_recovery_allowed | 0.0097 |

### Per-Action Feature Directions

Shows which features push toward (+) or away from (-) each action.

**climb_for_signal_recovery**:
  - - signal_recovery_confidence (SHAP: -0.0044)
  - + distance_to_home (SHAP: +0.0061)
  - - altitude_headroom (SHAP: -0.0037)
  - ~ mission_replan_budget (SHAP: +0.0002)
  - + terrain_occlusion_level (SHAP: +0.0011)

**conserve_battery_mode**:
  - - distance_to_home (SHAP: -0.0085)
  - - battery (SHAP: -0.0025)
  - ~ mission_replan_budget (SHAP: -0.0003)
  - ~ signal_recovery_confidence (SHAP: -0.0001)
  - - mission_progress (SHAP: -0.0063)

**continue_mission**:
  - - distance_to_home (SHAP: -0.0019)
  - - mission_replan_budget (SHAP: -0.0012)
  - - battery (SHAP: -0.0038)
  - - terrain_occlusion_level (SHAP: -0.0035)
  - - signal_recovery_confidence (SHAP: -0.0027)

**descend_for_safety**:
  - + airspace_deconfliction_status (SHAP: +0.0016)
  - - rules_of_engagement_state (SHAP: -0.0014)
  - + pilot_takeover_link_quality (SHAP: +0.0024)
  - - safe_landing_zone_available (SHAP: -0.0020)
  - + wind (SHAP: +0.0033)

**hold_position**:
  - - airspace_deconfliction_status (SHAP: -0.0042)
  - - rules_of_engagement_state (SHAP: -0.0017)
  - - pilot_takeover_link_quality (SHAP: -0.0037)
  - ~ mission_replan_budget (SHAP: +0.0003)
  - + obstacle_density (SHAP: +0.0017)

**manual_handoff**:
  - - pilot_takeover_link_quality (SHAP: -0.0025)
  - ~ airspace_deconfliction_status (SHAP: +0.0003)
  - ~ operator_control_latency_budget (SHAP: -0.0002)
  - ~ mission_replan_budget (SHAP: -0.0001)
  - + rules_of_engagement_state (SHAP: +0.0012)

**return_to_home**:
  - - distance_to_home (SHAP: -0.0014)
  - ~ mission_replan_budget (SHAP: +0.0004)
  - - mission_progress (SHAP: -0.0057)
  - - signal_recovery_confidence (SHAP: -0.0012)
  - - estimated_energy_margin (SHAP: -0.0028)

**switch_to_low_observable_path**:
  - - mission_replan_budget (SHAP: -0.0039)
  - - operator_control_latency_budget (SHAP: -0.0042)
  - - threat_level (SHAP: -0.0039)
  - ~ distance_to_home (SHAP: -0.0007)
  - ~ terrain_occlusion_level (SHAP: +0.0003)

## finance

**Features**: 9 | **Actions**: 8 | **Samples**: 13 | **Method**: TreeExplainer

### Global SHAP Importances (mean |SHAP|)

| Rank | Feature | SHAP Importance |
| ---: | --- | ---: |
| 1 | account_history | 0.1799 |
| 2 | anomaly_score | 0.1753 |
| 3 | velocity_indicator | 0.1716 |
| 4 | transaction_amount | 0.1168 |
| 5 | jurisdiction_risk | 0.1087 |
| 6 | device_trust | 0.1074 |
| 7 | kyc_completeness | 0.0705 |
| 8 | document_mismatch | 0.0547 |
| 9 | sanctions_hit | 0.0151 |

### Per-Action Feature Directions

Shows which features push toward (+) or away from (-) each action.

**allow_with_monitoring**:
  - - account_history (SHAP: -0.0088)
  - - transaction_amount (SHAP: -0.0045)
  - + anomaly_score (SHAP: +0.0016)
  - - device_trust (SHAP: -0.0047)
  - - velocity_indicator (SHAP: -0.0023)

**approve_low_risk**:
  - + anomaly_score (SHAP: +0.0041)
  - + jurisdiction_risk (SHAP: +0.0017)
  - + account_history (SHAP: +0.0042)
  - + velocity_indicator (SHAP: +0.0071)
  - - transaction_amount (SHAP: -0.0078)

**enhanced_due_diligence**:
  - ~ account_history (SHAP: -0.0002)
  - + transaction_amount (SHAP: +0.0020)
  - - jurisdiction_risk (SHAP: -0.0046)
  - + velocity_indicator (SHAP: +0.0051)
  - ~ anomaly_score (SHAP: -0.0003)

**escalate_compliance**:
  - - kyc_completeness (SHAP: -0.0138)
  - - anomaly_score (SHAP: -0.0027)
  - ~ velocity_indicator (SHAP: +0.0000)
  - - document_mismatch (SHAP: -0.0075)
  - - sanctions_hit (SHAP: -0.0095)

**freeze_for_investigation**:
  - - velocity_indicator (SHAP: -0.0018)
  - ~ account_history (SHAP: +0.0010)
  - + device_trust (SHAP: +0.0027)
  - - anomaly_score (SHAP: -0.0069)
  - + kyc_completeness (SHAP: +0.0044)

**lower_limit_temporarily**:
  - - velocity_indicator (SHAP: -0.0189)
  - - anomaly_score (SHAP: -0.0073)
  - - account_history (SHAP: -0.0022)
  - - device_trust (SHAP: -0.0036)
  - ~ jurisdiction_risk (SHAP: +0.0005)

**manual_review**:
  - + anomaly_score (SHAP: +0.0130)
  - + account_history (SHAP: +0.0061)
  - + velocity_indicator (SHAP: +0.0079)
  - + device_trust (SHAP: +0.0067)
  - + transaction_amount (SHAP: +0.0108)

**require_additional_docs**:
  - - kyc_completeness (SHAP: -0.0117)
  - - document_mismatch (SHAP: -0.0156)
  - - anomaly_score (SHAP: -0.0016)
  - ~ jurisdiction_risk (SHAP: -0.0004)
  - - transaction_amount (SHAP: -0.0012)

## grid

**Features**: 12 | **Actions**: 8 | **Samples**: 16 | **Method**: TreeExplainer

### Global SHAP Importances (mean |SHAP|)

| Rank | Feature | SHAP Importance |
| ---: | --- | ---: |
| 1 | weather_risk | 0.1290 |
| 2 | outage_scope | 0.1247 |
| 3 | frequency_deviation | 0.1195 |
| 4 | reserve_margin | 0.0976 |
| 5 | fault_isolation_ready | 0.0891 |
| 6 | customer_impact | 0.0820 |
| 7 | voltage_stability | 0.0773 |
| 8 | crew_availability | 0.0710 |
| 9 | relay_state | 0.0680 |
| 10 | transfer_path_available | 0.0574 |
| 11 | switching_authorized | 0.0507 |
| 12 | blackstart_required | 0.0337 |

### Per-Action Feature Directions

Shows which features push toward (+) or away from (-) each action.

**continue_monitoring**:
  - - outage_scope (SHAP: -0.0065)
  - - relay_state (SHAP: -0.0023)
  - - customer_impact (SHAP: -0.0065)
  - + voltage_stability (SHAP: +0.0016)
  - - frequency_deviation (SHAP: -0.0033)

**defer_switching_due_weather**:
  - - weather_risk (SHAP: -0.0034)
  - - fault_isolation_ready (SHAP: -0.0049)
  - - switching_authorized (SHAP: -0.0043)
  - - frequency_deviation (SHAP: -0.0031)
  - + outage_scope (SHAP: +0.0026)

**dispatch_field_crew**:
  - + fault_isolation_ready (SHAP: +0.0043)
  - + outage_scope (SHAP: +0.0011)
  - ~ frequency_deviation (SHAP: -0.0002)
  - + weather_risk (SHAP: +0.0035)
  - ~ customer_impact (SHAP: -0.0001)

**escalate_grid_supervisor**:
  - ~ weather_risk (SHAP: +0.0006)
  - ~ crew_availability (SHAP: +0.0008)
  - + frequency_deviation (SHAP: +0.0019)
  - + outage_scope (SHAP: +0.0035)
  - + voltage_stability (SHAP: +0.0021)

**isolate_faulted_feeder**:
  - - fault_isolation_ready (SHAP: -0.0095)
  - ~ outage_scope (SHAP: +0.0005)
  - + frequency_deviation (SHAP: +0.0044)
  - ~ weather_risk (SHAP: -0.0004)
  - ~ reserve_margin (SHAP: -0.0007)

**prepare_blackstart**:
  - + outage_scope (SHAP: +0.0031)
  - - weather_risk (SHAP: -0.0018)
  - - blackstart_required (SHAP: -0.0080)
  - - crew_availability (SHAP: -0.0041)
  - + frequency_deviation (SHAP: +0.0032)

**shed_noncritical_load**:
  - - reserve_margin (SHAP: -0.0056)
  - - frequency_deviation (SHAP: -0.0042)
  - - outage_scope (SHAP: -0.0033)
  - - weather_risk (SHAP: -0.0010)
  - - voltage_stability (SHAP: -0.0027)

**transfer_load**:
  - - transfer_path_available (SHAP: -0.0177)
  - + frequency_deviation (SHAP: +0.0015)
  - + voltage_stability (SHAP: +0.0022)
  - ~ reserve_margin (SHAP: -0.0006)
  - - customer_impact (SHAP: -0.0016)

## iam

**Features**: 12 | **Actions**: 7 | **Samples**: 15 | **Method**: TreeExplainer

### Global SHAP Importances (mean |SHAP|)

| Rank | Feature | SHAP Importance |
| ---: | --- | ---: |
| 1 | security_review | 0.1529 |
| 2 | session_scope | 0.1012 |
| 3 | requested_privilege | 0.1000 |
| 4 | device_posture | 0.0943 |
| 5 | manager_approval | 0.0920 |
| 6 | sod_risk | 0.0881 |
| 7 | requester_risk | 0.0808 |
| 8 | resource_sensitivity | 0.0801 |
| 9 | justification | 0.0790 |
| 10 | on_call_role | 0.0646 |
| 11 | ticket_state | 0.0338 |
| 12 | mfa_state | 0.0332 |

### Per-Action Feature Directions

Shows which features push toward (+) or away from (-) each action.

**auto_approve_standard_access**:
  - - security_review (SHAP: -0.0034)
  - - session_scope (SHAP: -0.0022)
  - - requested_privilege (SHAP: -0.0018)
  - + manager_approval (SHAP: +0.0076)
  - - ticket_state (SHAP: -0.0036)

**deny_request**:
  - ~ requester_risk (SHAP: +0.0002)
  - + security_review (SHAP: +0.0061)
  - + device_posture (SHAP: +0.0103)
  - - mfa_state (SHAP: -0.0158)
  - + requested_privilege (SHAP: +0.0082)

**escalate_identity_admin**:
  - - device_posture (SHAP: -0.0193)
  - + requested_privilege (SHAP: +0.0014)
  - - requester_risk (SHAP: -0.0044)
  - + security_review (SHAP: +0.0026)
  - + resource_sensitivity (SHAP: +0.0027)

**grant_break_glass_access**:
  - - session_scope (SHAP: -0.0119)
  - - justification (SHAP: -0.0076)
  - - on_call_role (SHAP: -0.0048)
  - + sod_risk (SHAP: +0.0024)
  - + security_review (SHAP: +0.0030)

**grant_timeboxed_privileged_access**:
  - - requested_privilege (SHAP: -0.0062)
  - - security_review (SHAP: -0.0023)
  - - resource_sensitivity (SHAP: -0.0063)
  - + requester_risk (SHAP: +0.0019)
  - + sod_risk (SHAP: +0.0035)

**require_manager_approval**:
  - - manager_approval (SHAP: -0.0186)
  - - security_review (SHAP: -0.0018)
  - + resource_sensitivity (SHAP: +0.0016)
  - ~ justification (SHAP: -0.0001)
  - - device_posture (SHAP: -0.0061)

**require_security_review**:
  - - sod_risk (SHAP: -0.0144)
  - - security_review (SHAP: -0.0041)
  - + session_scope (SHAP: +0.0012)
  - + mfa_state (SHAP: +0.0117)
  - - justification (SHAP: -0.0010)

## medical

**Features**: 10 | **Actions**: 8 | **Samples**: 12 | **Method**: TreeExplainer

### Global SHAP Importances (mean |SHAP|)

| Rank | Feature | SHAP Importance |
| ---: | --- | ---: |
| 1 | symptom_onset | 0.2046 |
| 2 | clinician_note_flag | 0.1866 |
| 3 | fever_bucket | 0.1410 |
| 4 | infection_risk | 0.1362 |
| 5 | acuity_score | 0.0970 |
| 6 | chest_pain | 0.0595 |
| 7 | respiratory_distress | 0.0586 |
| 8 | age_bracket | 0.0528 |
| 9 | focal_neuro_deficit | 0.0527 |
| 10 | hypotension | 0.0109 |

### Per-Action Feature Directions

Shows which features push toward (+) or away from (-) each action.

**cardiac_chest_pain_pathway**:
  - - clinician_note_flag (SHAP: -0.0151)
  - - symptom_onset (SHAP: -0.0078)
  - - acuity_score (SHAP: -0.0011)
  - - chest_pain (SHAP: -0.0057)
  - ~ fever_bucket (SHAP: -0.0004)

**escalate_supervisor_review**:
  - + clinician_note_flag (SHAP: +0.0113)
  - + symptom_onset (SHAP: +0.0079)
  - - chest_pain (SHAP: -0.0047)
  - + fever_bucket (SHAP: +0.0058)
  - - focal_neuro_deficit (SHAP: -0.0028)

**lab_panel_priority_order**:
  - - infection_risk (SHAP: -0.0072)
  - - fever_bucket (SHAP: -0.0064)
  - - acuity_score (SHAP: -0.0076)
  - + symptom_onset (SHAP: +0.0022)
  - ~ clinician_note_flag (SHAP: -0.0005)

**respiratory_support_pathway**:
  - - infection_risk (SHAP: -0.0057)
  - - symptom_onset (SHAP: -0.0026)
  - - fever_bucket (SHAP: -0.0025)
  - - respiratory_distress (SHAP: -0.0091)
  - ~ clinician_note_flag (SHAP: -0.0003)

**routine_review**:
  - + symptom_onset (SHAP: +0.0067)
  - + fever_bucket (SHAP: +0.0036)
  - + infection_risk (SHAP: +0.0083)
  - + clinician_note_flag (SHAP: +0.0042)
  - - acuity_score (SHAP: -0.0056)

**sepsis_screen_pathway**:
  - + clinician_note_flag (SHAP: +0.0044)
  - ~ fever_bucket (SHAP: -0.0007)
  - + symptom_onset (SHAP: +0.0034)
  - + infection_risk (SHAP: +0.0024)
  - + respiratory_distress (SHAP: +0.0018)

**stroke_alert_pathway**:
  - - symptom_onset (SHAP: -0.0094)
  - - clinician_note_flag (SHAP: -0.0080)
  - + acuity_score (SHAP: +0.0020)
  - - focal_neuro_deficit (SHAP: -0.0060)
  - + fever_bucket (SHAP: +0.0013)

**urgent_clinician_review**:
  - ~ symptom_onset (SHAP: -0.0005)
  - + clinician_note_flag (SHAP: +0.0040)
  - + infection_risk (SHAP: +0.0017)
  - + focal_neuro_deficit (SHAP: +0.0027)
  - + respiratory_distress (SHAP: +0.0051)

## soc

**Features**: 8 | **Actions**: 7 | **Samples**: 14 | **Method**: TreeExplainer

### Global SHAP Importances (mean |SHAP|)

| Rank | Feature | SHAP Importance |
| ---: | --- | ---: |
| 1 | severity | 0.3074 |
| 2 | blast_radius | 0.1491 |
| 3 | threat_confidence | 0.1446 |
| 4 | asset_criticality | 0.1027 |
| 5 | endpoint_type | 0.0987 |
| 6 | credential_exposure | 0.0732 |
| 7 | internet_exposed | 0.0708 |
| 8 | lateral_movement | 0.0535 |

### Per-Action Feature Directions

Shows which features push toward (+) or away from (-) each action.

**block_ip_temporarily**:
  - - endpoint_type (SHAP: -0.0129)
  - ~ threat_confidence (SHAP: -0.0003)
  - - severity (SHAP: -0.0020)
  - - internet_exposed (SHAP: -0.0017)
  - + blast_radius (SHAP: +0.0042)

**collect_forensics**:
  - + severity (SHAP: +0.0133)
  - - threat_confidence (SHAP: -0.0072)
  - + blast_radius (SHAP: +0.0052)
  - ~ internet_exposed (SHAP: +0.0007)
  - - asset_criticality (SHAP: -0.0067)

**do_nothing_validated**:
  - - severity (SHAP: -0.0013)
  - - blast_radius (SHAP: -0.0127)
  - + threat_confidence (SHAP: +0.0021)
  - + asset_criticality (SHAP: +0.0024)
  - ~ internet_exposed (SHAP: +0.0007)

**escalate_p1**:
  - - severity (SHAP: -0.0041)
  - - lateral_movement (SHAP: -0.0133)
  - - blast_radius (SHAP: -0.0050)
  - ~ credential_exposure (SHAP: +0.0003)
  - + asset_criticality (SHAP: +0.0043)

**isolate_host**:
  - + severity (SHAP: +0.0026)
  - ~ blast_radius (SHAP: +0.0009)
  - ~ threat_confidence (SHAP: -0.0001)
  - - asset_criticality (SHAP: -0.0045)
  - + endpoint_type (SHAP: +0.0023)

**monitor_only**:
  - - severity (SHAP: -0.0133)
  - + blast_radius (SHAP: +0.0052)
  - + asset_criticality (SHAP: +0.0056)
  - - threat_confidence (SHAP: -0.0020)
  - + internet_exposed (SHAP: +0.0011)

**rotate_credentials**:
  - + severity (SHAP: +0.0048)
  - + threat_confidence (SHAP: +0.0026)
  - - credential_exposure (SHAP: -0.0092)
  - - asset_criticality (SHAP: -0.0043)
  - ~ endpoint_type (SHAP: +0.0005)

## sre

**Features**: 27 | **Actions**: 8 | **Samples**: 24 | **Method**: TreeExplainer

### Global SHAP Importances (mean |SHAP|)

| Rank | Feature | SHAP Importance |
| ---: | --- | ---: |
| 1 | cross_region_read_staleness | 0.0834 |
| 2 | error_rate | 0.0757 |
| 3 | change_failure_blast_radius | 0.0752 |
| 4 | capacity_headroom | 0.0704 |
| 5 | quorum_health | 0.0679 |
| 6 | control_plane_availability | 0.0678 |
| 7 | fault_scope | 0.0667 |
| 8 | dependency_health | 0.0589 |
| 9 | saturation | 0.0487 |
| 10 | replication_lag | 0.0473 |
| 11 | replica_skew | 0.0435 |
| 12 | region_health | 0.0357 |
| 13 | node_locality_score | 0.0354 |
| 14 | deployment_recency | 0.0336 |
| 15 | mitigation_window_remaining | 0.0210 |
| 16 | telemetry_confidence | 0.0208 |
| 17 | rollback_safe | 0.0196 |
| 18 | recent_restart_attempts | 0.0179 |
| 19 | automation_policy_permits_failover | 0.0170 |
| 20 | runbook_coordination_required | 0.0142 |
| 21 | deploy_regression_suspected | 0.0141 |
| 22 | failover_ready | 0.0135 |
| 23 | operator_response_eta | 0.0133 |
| 24 | write_path_available | 0.0118 |
| 25 | latency | 0.0091 |
| 26 | secondary_capacity_ready | 0.0090 |
| 27 | operator_approval_required | 0.0083 |

### Per-Action Feature Directions

Shows which features push toward (+) or away from (-) each action.

**drain_node**:
  - - fault_scope (SHAP: -0.0037)
  - ~ change_failure_blast_radius (SHAP: -0.0006)
  - - error_rate (SHAP: -0.0012)
  - + dependency_health (SHAP: +0.0012)
  - ~ saturation (SHAP: -0.0003)

**enable_readonly_mode**:
  - ~ control_plane_availability (SHAP: +0.0006)
  - + cross_region_read_staleness (SHAP: +0.0049)
  - + change_failure_blast_radius (SHAP: +0.0017)
  - + quorum_health (SHAP: +0.0055)
  - + capacity_headroom (SHAP: +0.0028)

**failover_region**:
  - ~ cross_region_read_staleness (SHAP: -0.0003)
  - ~ dependency_health (SHAP: +0.0002)
  - - automation_policy_permits_failover (SHAP: -0.0031)
  - + fault_scope (SHAP: +0.0015)
  - ~ capacity_headroom (SHAP: -0.0009)

**gather_more_telemetry**:
  - - error_rate (SHAP: -0.0083)
  - - capacity_headroom (SHAP: -0.0030)
  - - telemetry_confidence (SHAP: -0.0133)
  - - change_failure_blast_radius (SHAP: -0.0026)
  - - cross_region_read_staleness (SHAP: -0.0017)

**page_human_operator**:
  - + control_plane_availability (SHAP: +0.0031)
  - - mitigation_window_remaining (SHAP: -0.0015)
  - + cross_region_read_staleness (SHAP: +0.0052)
  - + quorum_health (SHAP: +0.0015)
  - + fault_scope (SHAP: +0.0026)

**restart_service**:
  - - cross_region_read_staleness (SHAP: -0.0023)
  - ~ quorum_health (SHAP: -0.0007)
  - - change_failure_blast_radius (SHAP: -0.0024)
  - + error_rate (SHAP: +0.0043)
  - - replication_lag (SHAP: -0.0015)

**rollback_deploy**:
  - - deployment_recency (SHAP: -0.0078)
  - - rollback_safe (SHAP: -0.0052)
  - - replication_lag (SHAP: -0.0014)
  - + change_failure_blast_radius (SHAP: +0.0016)
  - ~ cross_region_read_staleness (SHAP: -0.0009)

**scale_out**:
  - - error_rate (SHAP: -0.0045)
  - - capacity_headroom (SHAP: -0.0024)
  - - saturation (SHAP: -0.0023)
  - - replica_skew (SHAP: -0.0038)
  - - cross_region_read_staleness (SHAP: -0.0039)

