# KVRM Compact Selector — Generalization Analysis

Generated: 2026-04-13 14:08:50 UTC

## Summary

| Domain | Cases | Classes | Train Acc | LOOCV Acc | K-Fold Acc (mean +/- std) | k | Drop |
|--------|------:|--------:|----------:|----------:|--------------------------:|--:|-----:|
| content_moderation | 31 | 7 | 100.0% | 19.4% ** | 35.5% +/- 4.1% | 3 | 80.6% |
| customer_support | 25 | 7 | 100.0% | 16.0% ** | 31.9% +/- 5.2% | 3 | 84.0% |
| drone | 25 | 8 | 100.0% | 96.0% | 100.0% +/- 0.0% | 2 | 4.0% |
| finance | 57 | 8 | 100.0% | 59.6% ** | 57.9% +/- 6.2% | 5 | 40.4% |
| grid | 40 | 8 | 100.0% | 77.5% ** | 85.0% +/- 12.2% | 5 | 22.5% |
| iam | 36 | 7 | 100.0% | 75.0% ** | 77.8% +/- 10.4% | 3 | 25.0% |
| medical | 35 | 8 | 100.0% | 77.1% ** | 69.1% +/- 11.6% | 4 | 22.9% |
| soc | 14 | 7 | 100.0% | 50.0% ** | 64.3% +/- 7.1% | 2 | 50.0% |
| sre | 24 | 8 | 100.0% | 100.0% | 100.0% +/- 0.0% | 2 | 0.0% |

## content_moderation

- **Cases**: 31  |  **Classes**: 7
- **Train accuracy**: 100.0%
- **LOOCV accuracy**: 19.4% (6/31)
- **3-fold CV**: 35.5% +/- 4.1% (folds: 36.4%, 40.0%, 30.0%)

### Label Distribution

| Action | Count |
|--------|------:|
| remove_content | 6 |
| escalate_trust_safety | 6 |
| suspend_account | 5 |
| flag_for_human_review | 4 |
| request_human_review | 4 |
| auto_approve | 3 |
| reduce_visibility | 3 |

### Per-Class LOOCV Accuracy

| Action | Support | Correct | Accuracy | Errors |
|--------|--------:|--------:|---------:|--------|
| auto_approve | 3 | 3 | 100.0% | - |
| escalate_trust_safety | 6 | 0 | 0.0% | remove_content(2), suspend_account(2), request_human_review(1), flag_for_human_review(1) |
| flag_for_human_review | 4 | 0 | 0.0% | escalate_trust_safety(1), remove_content(2), suspend_account(1) |
| reduce_visibility | 3 | 0 | 0.0% | escalate_trust_safety(1), flag_for_human_review(1), remove_content(1) |
| remove_content | 6 | 2 | 33.3% | suspend_account(2), escalate_trust_safety(2) |
| request_human_review | 4 | 0 | 0.0% | auto_approve(1), reduce_visibility(1), suspend_account(1), escalate_trust_safety(1) |
| suspend_account | 5 | 1 | 20.0% | escalate_trust_safety(2), flag_for_human_review(1), remove_content(1) |

### Misclassified Cases (LOOCV)

| Case ID | True Label | Predicted |
|---------|------------|-----------|
| cm_train_004 | reduce_visibility | escalate_trust_safety |
| cm_train_005 | reduce_visibility | flag_for_human_review |
| cm_train_006 | reduce_visibility | remove_content |
| cm_train_007 | flag_for_human_review | escalate_trust_safety |
| cm_train_008 | flag_for_human_review | remove_content |
| cm_train_009 | flag_for_human_review | remove_content |
| cm_train_010 | flag_for_human_review | suspend_account |
| cm_train_011 | remove_content | suspend_account |
| cm_train_012 | remove_content | suspend_account |
| cm_train_014 | remove_content | escalate_trust_safety |
| cm_train_015 | suspend_account | escalate_trust_safety |
| cm_train_016 | suspend_account | escalate_trust_safety |
| cm_train_017 | suspend_account | flag_for_human_review |
| cm_train_018 | escalate_trust_safety | remove_content |
| cm_train_019 | escalate_trust_safety | suspend_account |
| cm_train_020 | escalate_trust_safety | remove_content |
| cm_train_021 | request_human_review | auto_approve |
| cm_train_022 | request_human_review | reduce_visibility |
| cm_train_023 | request_human_review | suspend_account |
| cm_train_024 | request_human_review | escalate_trust_safety |
| cm_train_037 | remove_content | escalate_trust_safety |
| cm_train_040 | suspend_account | remove_content |
| cm_train_041 | escalate_trust_safety | request_human_review |
| cm_train_042 | escalate_trust_safety | flag_for_human_review |
| cm_train_043 | escalate_trust_safety | suspend_account |

### Confusion Matrix

| | auto_approve | escalate_trust_safety | flag_for_human_review | reduce_visibility | remove_content | request_human_review | suspend_account |
|---|---|---|---|---|---|---|---|
| **auto_approve** | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| **escalate_trust_safety** | 0 | 0 | 1 | 0 | 2 | 1 | 2 |
| **flag_for_human_review** | 0 | 1 | 0 | 0 | 2 | 0 | 1 |
| **reduce_visibility** | 0 | 1 | 1 | 0 | 1 | 0 | 0 |
| **remove_content** | 0 | 2 | 0 | 0 | 2 | 0 | 2 |
| **request_human_review** | 1 | 1 | 0 | 1 | 0 | 0 | 1 |
| **suspend_account** | 0 | 2 | 1 | 0 | 1 | 0 | 1 |

## customer_support

- **Cases**: 25  |  **Classes**: 7
- **Train accuracy**: 100.0%
- **LOOCV accuracy**: 16.0% (4/25)
- **3-fold CV**: 31.9% +/- 5.2% (folds: 33.3%, 25.0%, 37.5%)

### Label Distribution

| Action | Count |
|--------|------:|
| escalate_to_manager | 7 |
| send_knowledge_article | 3 |
| auto_resolve_billing | 3 |
| assign_specialist | 3 |
| schedule_callback | 3 |
| issue_refund | 3 |
| request_human_review | 3 |

### Per-Class LOOCV Accuracy

| Action | Support | Correct | Accuracy | Errors |
|--------|--------:|--------:|---------:|--------|
| assign_specialist | 3 | 0 | 0.0% | escalate_to_manager(2), auto_resolve_billing(1) |
| auto_resolve_billing | 3 | 0 | 0.0% | send_knowledge_article(1), issue_refund(1), assign_specialist(1) |
| escalate_to_manager | 7 | 1 | 14.3% | schedule_callback(4), assign_specialist(2) |
| issue_refund | 3 | 2 | 66.7% | escalate_to_manager(1) |
| request_human_review | 3 | 0 | 0.0% | assign_specialist(3) |
| schedule_callback | 3 | 0 | 0.0% | assign_specialist(1), escalate_to_manager(2) |
| send_knowledge_article | 3 | 1 | 33.3% | escalate_to_manager(1), auto_resolve_billing(1) |

### Misclassified Cases (LOOCV)

| Case ID | True Label | Predicted |
|---------|------------|-----------|
| cs_train_001 | send_knowledge_article | escalate_to_manager |
| cs_train_002 | send_knowledge_article | auto_resolve_billing |
| cs_train_004 | auto_resolve_billing | send_knowledge_article |
| cs_train_005 | auto_resolve_billing | issue_refund |
| cs_train_006 | auto_resolve_billing | assign_specialist |
| cs_train_007 | assign_specialist | escalate_to_manager |
| cs_train_008 | assign_specialist | escalate_to_manager |
| cs_train_009 | assign_specialist | auto_resolve_billing |
| cs_train_010 | schedule_callback | assign_specialist |
| cs_train_011 | schedule_callback | escalate_to_manager |
| cs_train_012 | schedule_callback | escalate_to_manager |
| cs_train_014 | issue_refund | escalate_to_manager |
| cs_train_017 | escalate_to_manager | schedule_callback |
| cs_train_018 | escalate_to_manager | schedule_callback |
| cs_train_019 | request_human_review | assign_specialist |
| cs_train_020 | request_human_review | assign_specialist |
| cs_train_021 | request_human_review | assign_specialist |
| cs_train_031 | escalate_to_manager | assign_specialist |
| cs_train_032 | escalate_to_manager | schedule_callback |
| cs_train_033 | escalate_to_manager | schedule_callback |
| cs_train_034 | escalate_to_manager | assign_specialist |

### Confusion Matrix

| | assign_specialist | auto_resolve_billing | escalate_to_manager | issue_refund | request_human_review | schedule_callback | send_knowledge_article |
|---|---|---|---|---|---|---|---|
| **assign_specialist** | 0 | 1 | 2 | 0 | 0 | 0 | 0 |
| **auto_resolve_billing** | 1 | 0 | 0 | 1 | 0 | 0 | 1 |
| **escalate_to_manager** | 2 | 0 | 1 | 0 | 0 | 4 | 0 |
| **issue_refund** | 0 | 0 | 1 | 2 | 0 | 0 | 0 |
| **request_human_review** | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| **schedule_callback** | 1 | 0 | 2 | 0 | 0 | 0 | 0 |
| **send_knowledge_article** | 0 | 1 | 1 | 0 | 0 | 0 | 1 |

## drone

- **Cases**: 25  |  **Classes**: 8
- **Train accuracy**: 100.0%
- **LOOCV accuracy**: 96.0% (24/25)
- **2-fold CV**: 100.0% +/- 0.0% (folds: 100.0%, 100.0%)

### Label Distribution

| Action | Count |
|--------|------:|
| climb_for_signal_recovery | 4 |
| descend_for_safety | 4 |
| return_to_home | 3 |
| hold_position | 3 |
| switch_to_low_observable_path | 3 |
| conserve_battery_mode | 3 |
| manual_handoff | 3 |
| continue_mission | 2 |

### Per-Class LOOCV Accuracy

| Action | Support | Correct | Accuracy | Errors |
|--------|--------:|--------:|---------:|--------|
| climb_for_signal_recovery | 4 | 3 | 75.0% | continue_mission(1) |
| conserve_battery_mode | 3 | 3 | 100.0% | - |
| continue_mission | 2 | 2 | 100.0% | - |
| descend_for_safety | 4 | 4 | 100.0% | - |
| hold_position | 3 | 3 | 100.0% | - |
| manual_handoff | 3 | 3 | 100.0% | - |
| return_to_home | 3 | 3 | 100.0% | - |
| switch_to_low_observable_path | 3 | 3 | 100.0% | - |

### Misclassified Cases (LOOCV)

| Case ID | True Label | Predicted |
|---------|------------|-----------|
| drone_train_021 | climb_for_signal_recovery | continue_mission |

### Confusion Matrix

| | climb_for_signal_recovery | conserve_battery_mode | continue_mission | descend_for_safety | hold_position | manual_handoff | return_to_home | switch_to_low_observable_path |
|---|---|---|---|---|---|---|---|---|
| **climb_for_signal_recovery** | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| **conserve_battery_mode** | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| **continue_mission** | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| **descend_for_safety** | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| **hold_position** | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| **manual_handoff** | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| **return_to_home** | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| **switch_to_low_observable_path** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |

## finance

- **Cases**: 57  |  **Classes**: 8
- **Train accuracy**: 100.0%
- **LOOCV accuracy**: 59.6% (34/57)
- **5-fold CV**: 57.9% +/- 6.2% (folds: 66.7%, 50.0%, 54.5%, 63.6%, 54.5%)

### Label Distribution

| Action | Count |
|--------|------:|
| manual_review | 9 |
| enhanced_due_diligence | 8 |
| freeze_for_investigation | 8 |
| require_additional_docs | 7 |
| lower_limit_temporarily | 7 |
| escalate_compliance | 7 |
| allow_with_monitoring | 6 |
| approve_low_risk | 5 |

### Per-Class LOOCV Accuracy

| Action | Support | Correct | Accuracy | Errors |
|--------|--------:|--------:|---------:|--------|
| allow_with_monitoring | 6 | 4 | 66.7% | manual_review(2) |
| approve_low_risk | 5 | 5 | 100.0% | - |
| enhanced_due_diligence | 8 | 4 | 50.0% | allow_with_monitoring(1), approve_low_risk(2), manual_review(1) |
| escalate_compliance | 7 | 1 | 14.3% | approve_low_risk(2), freeze_for_investigation(1), allow_with_monitoring(1), enhanced_due_diligence(1), require_additional_docs(1) |
| freeze_for_investigation | 8 | 7 | 87.5% | lower_limit_temporarily(1) |
| lower_limit_temporarily | 7 | 6 | 85.7% | freeze_for_investigation(1) |
| manual_review | 9 | 6 | 66.7% | allow_with_monitoring(2), require_additional_docs(1) |
| require_additional_docs | 7 | 1 | 14.3% | approve_low_risk(3), allow_with_monitoring(1), enhanced_due_diligence(1), manual_review(1) |

### Misclassified Cases (LOOCV)

| Case ID | True Label | Predicted |
|---------|------------|-----------|
| finance_train_005 | enhanced_due_diligence | allow_with_monitoring |
| finance_train_011 | manual_review | allow_with_monitoring |
| finance_train_013 | manual_review | allow_with_monitoring |
| finance_train_017 | allow_with_monitoring | manual_review |
| finance_train_019 | enhanced_due_diligence | approve_low_risk |
| finance_train_021 | enhanced_due_diligence | approve_low_risk |
| finance_train_022 | require_additional_docs | approve_low_risk |
| finance_train_023 | require_additional_docs | allow_with_monitoring |
| finance_train_024 | require_additional_docs | enhanced_due_diligence |
| finance_train_026 | lower_limit_temporarily | freeze_for_investigation |
| finance_train_028 | freeze_for_investigation | lower_limit_temporarily |
| finance_train_031 | escalate_compliance | approve_low_risk |
| finance_train_032 | escalate_compliance | freeze_for_investigation |
| finance_train_033 | escalate_compliance | allow_with_monitoring |
| finance_train_037 | require_additional_docs | manual_review |
| finance_train_038 | escalate_compliance | enhanced_due_diligence |
| finance_train_040 | enhanced_due_diligence | manual_review |
| finance_train_043 | allow_with_monitoring | manual_review |
| finance_train_045 | escalate_compliance | approve_low_risk |
| finance_train_046 | escalate_compliance | require_additional_docs |
| finance_train_047 | require_additional_docs | approve_low_risk |
| finance_train_048 | require_additional_docs | approve_low_risk |
| finance_train_054 | manual_review | require_additional_docs |

### Confusion Matrix

| | allow_with_monitoring | approve_low_risk | enhanced_due_diligence | escalate_compliance | freeze_for_investigation | lower_limit_temporarily | manual_review | require_additional_docs |
|---|---|---|---|---|---|---|---|---|
| **allow_with_monitoring** | 4 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| **approve_low_risk** | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| **enhanced_due_diligence** | 1 | 2 | 4 | 0 | 0 | 0 | 1 | 0 |
| **escalate_compliance** | 1 | 2 | 1 | 1 | 1 | 0 | 0 | 1 |
| **freeze_for_investigation** | 0 | 0 | 0 | 0 | 7 | 1 | 0 | 0 |
| **lower_limit_temporarily** | 0 | 0 | 0 | 0 | 1 | 6 | 0 | 0 |
| **manual_review** | 2 | 0 | 0 | 0 | 0 | 0 | 6 | 1 |
| **require_additional_docs** | 1 | 3 | 1 | 0 | 0 | 0 | 1 | 1 |

## grid

- **Cases**: 40  |  **Classes**: 8
- **Train accuracy**: 100.0%
- **LOOCV accuracy**: 77.5% (31/40)
- **5-fold CV**: 85.0% +/- 12.2% (folds: 75.0%, 75.0%, 100.0%, 75.0%, 100.0%)

### Label Distribution

| Action | Count |
|--------|------:|
| continue_monitoring | 5 |
| isolate_faulted_feeder | 5 |
| transfer_load | 5 |
| dispatch_field_crew | 5 |
| shed_noncritical_load | 5 |
| prepare_blackstart | 5 |
| defer_switching_due_weather | 5 |
| escalate_grid_supervisor | 5 |

### Per-Class LOOCV Accuracy

| Action | Support | Correct | Accuracy | Errors |
|--------|--------:|--------:|---------:|--------|
| continue_monitoring | 5 | 5 | 100.0% | - |
| defer_switching_due_weather | 5 | 5 | 100.0% | - |
| dispatch_field_crew | 5 | 1 | 20.0% | isolate_faulted_feeder(2), transfer_load(1), defer_switching_due_weather(1) |
| escalate_grid_supervisor | 5 | 3 | 60.0% | prepare_blackstart(1), defer_switching_due_weather(1) |
| isolate_faulted_feeder | 5 | 4 | 80.0% | dispatch_field_crew(1) |
| prepare_blackstart | 5 | 5 | 100.0% | - |
| shed_noncritical_load | 5 | 3 | 60.0% | prepare_blackstart(2) |
| transfer_load | 5 | 5 | 100.0% | - |

### Misclassified Cases (LOOCV)

| Case ID | True Label | Predicted |
|---------|------------|-----------|
| grid_train_007 | dispatch_field_crew | isolate_faulted_feeder |
| grid_train_008 | dispatch_field_crew | transfer_load |
| grid_train_010 | shed_noncritical_load | prepare_blackstart |
| grid_train_020 | isolate_faulted_feeder | dispatch_field_crew |
| grid_train_026 | dispatch_field_crew | isolate_faulted_feeder |
| grid_train_027 | dispatch_field_crew | defer_switching_due_weather |
| grid_train_030 | shed_noncritical_load | prepare_blackstart |
| grid_train_039 | escalate_grid_supervisor | prepare_blackstart |
| grid_train_040 | escalate_grid_supervisor | defer_switching_due_weather |

### Confusion Matrix

| | continue_monitoring | defer_switching_due_weather | dispatch_field_crew | escalate_grid_supervisor | isolate_faulted_feeder | prepare_blackstart | shed_noncritical_load | transfer_load |
|---|---|---|---|---|---|---|---|---|
| **continue_monitoring** | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **defer_switching_due_weather** | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| **dispatch_field_crew** | 0 | 1 | 1 | 0 | 2 | 0 | 0 | 1 |
| **escalate_grid_supervisor** | 0 | 1 | 0 | 3 | 0 | 1 | 0 | 0 |
| **isolate_faulted_feeder** | 0 | 0 | 1 | 0 | 4 | 0 | 0 | 0 |
| **prepare_blackstart** | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| **shed_noncritical_load** | 0 | 0 | 0 | 0 | 0 | 2 | 3 | 0 |
| **transfer_load** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |

## iam

- **Cases**: 36  |  **Classes**: 7
- **Train accuracy**: 100.0%
- **LOOCV accuracy**: 75.0% (27/36)
- **3-fold CV**: 77.8% +/- 10.4% (folds: 91.7%, 75.0%, 66.7%)

### Label Distribution

| Action | Count |
|--------|------:|
| deny_request | 10 |
| auto_approve_standard_access | 5 |
| require_manager_approval | 5 |
| grant_timeboxed_privileged_access | 5 |
| require_security_review | 4 |
| escalate_identity_admin | 4 |
| grant_break_glass_access | 3 |

### Per-Class LOOCV Accuracy

| Action | Support | Correct | Accuracy | Errors |
|--------|--------:|--------:|---------:|--------|
| auto_approve_standard_access | 5 | 5 | 100.0% | - |
| deny_request | 10 | 3 | 30.0% | grant_timeboxed_privileged_access(3), require_security_review(1), auto_approve_standard_access(3) |
| escalate_identity_admin | 4 | 4 | 100.0% | - |
| grant_break_glass_access | 3 | 3 | 100.0% | - |
| grant_timeboxed_privileged_access | 5 | 4 | 80.0% | deny_request(1) |
| require_manager_approval | 5 | 5 | 100.0% | - |
| require_security_review | 4 | 3 | 75.0% | deny_request(1) |

### Misclassified Cases (LOOCV)

| Case ID | True Label | Predicted |
|---------|------------|-----------|
| iam_train_006 | require_security_review | deny_request |
| iam_train_007 | grant_timeboxed_privileged_access | deny_request |
| iam_train_011 | deny_request | grant_timeboxed_privileged_access |
| iam_train_012 | deny_request | require_security_review |
| iam_train_028 | deny_request | grant_timeboxed_privileged_access |
| iam_train_029 | deny_request | auto_approve_standard_access |
| iam_train_031 | deny_request | grant_timeboxed_privileged_access |
| iam_train_032 | deny_request | auto_approve_standard_access |
| iam_train_035 | deny_request | auto_approve_standard_access |

### Confusion Matrix

| | auto_approve_standard_access | deny_request | escalate_identity_admin | grant_break_glass_access | grant_timeboxed_privileged_access | require_manager_approval | require_security_review |
|---|---|---|---|---|---|---|---|
| **auto_approve_standard_access** | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| **deny_request** | 3 | 3 | 0 | 0 | 3 | 0 | 1 |
| **escalate_identity_admin** | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| **grant_break_glass_access** | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| **grant_timeboxed_privileged_access** | 0 | 1 | 0 | 0 | 4 | 0 | 0 |
| **require_manager_approval** | 0 | 0 | 0 | 0 | 0 | 5 | 0 |
| **require_security_review** | 0 | 1 | 0 | 0 | 0 | 0 | 3 |

## medical

- **Cases**: 35  |  **Classes**: 8
- **Train accuracy**: 100.0%
- **LOOCV accuracy**: 77.1% (27/35)
- **4-fold CV**: 69.1% +/- 11.6% (folds: 66.7%, 55.6%, 66.7%, 87.5%)

### Label Distribution

| Action | Count |
|--------|------:|
| routine_review | 5 |
| urgent_clinician_review | 5 |
| escalate_supervisor_review | 5 |
| sepsis_screen_pathway | 4 |
| stroke_alert_pathway | 4 |
| cardiac_chest_pain_pathway | 4 |
| respiratory_support_pathway | 4 |
| lab_panel_priority_order | 4 |

### Per-Class LOOCV Accuracy

| Action | Support | Correct | Accuracy | Errors |
|--------|--------:|--------:|---------:|--------|
| cardiac_chest_pain_pathway | 4 | 3 | 75.0% | urgent_clinician_review(1) |
| escalate_supervisor_review | 5 | 4 | 80.0% | cardiac_chest_pain_pathway(1) |
| lab_panel_priority_order | 4 | 3 | 75.0% | urgent_clinician_review(1) |
| respiratory_support_pathway | 4 | 4 | 100.0% | - |
| routine_review | 5 | 5 | 100.0% | - |
| sepsis_screen_pathway | 4 | 3 | 75.0% | lab_panel_priority_order(1) |
| stroke_alert_pathway | 4 | 3 | 75.0% | routine_review(1) |
| urgent_clinician_review | 5 | 2 | 40.0% | escalate_supervisor_review(2), routine_review(1) |

### Misclassified Cases (LOOCV)

| Case ID | True Label | Predicted |
|---------|------------|-----------|
| medical_train_004 | urgent_clinician_review | escalate_supervisor_review |
| medical_train_016 | urgent_clinician_review | routine_review |
| medical_train_017 | urgent_clinician_review | escalate_supervisor_review |
| medical_train_020 | sepsis_screen_pathway | lab_panel_priority_order |
| medical_train_022 | stroke_alert_pathway | routine_review |
| medical_train_026 | cardiac_chest_pain_pathway | urgent_clinician_review |
| medical_train_031 | lab_panel_priority_order | urgent_clinician_review |
| medical_train_034 | escalate_supervisor_review | cardiac_chest_pain_pathway |

### Confusion Matrix

| | cardiac_chest_pain_pathway | escalate_supervisor_review | lab_panel_priority_order | respiratory_support_pathway | routine_review | sepsis_screen_pathway | stroke_alert_pathway | urgent_clinician_review |
|---|---|---|---|---|---|---|---|---|
| **cardiac_chest_pain_pathway** | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **escalate_supervisor_review** | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| **lab_panel_priority_order** | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 1 |
| **respiratory_support_pathway** | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| **routine_review** | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 |
| **sepsis_screen_pathway** | 0 | 0 | 1 | 0 | 0 | 3 | 0 | 0 |
| **stroke_alert_pathway** | 0 | 0 | 0 | 0 | 1 | 0 | 3 | 0 |
| **urgent_clinician_review** | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 2 |

## soc

- **Cases**: 14  |  **Classes**: 7
- **Train accuracy**: 100.0%
- **LOOCV accuracy**: 50.0% (7/14)
- **2-fold CV**: 64.3% +/- 7.1% (folds: 57.1%, 71.4%)

### Label Distribution

| Action | Count |
|--------|------:|
| escalate_p1 | 2 |
| isolate_host | 2 |
| rotate_credentials | 2 |
| block_ip_temporarily | 2 |
| collect_forensics | 2 |
| monitor_only | 2 |
| do_nothing_validated | 2 |

### Per-Class LOOCV Accuracy

| Action | Support | Correct | Accuracy | Errors |
|--------|--------:|--------:|---------:|--------|
| block_ip_temporarily | 2 | 1 | 50.0% | collect_forensics(1) |
| collect_forensics | 2 | 0 | 0.0% | monitor_only(2) |
| do_nothing_validated | 2 | 2 | 100.0% | - |
| escalate_p1 | 2 | 1 | 50.0% | rotate_credentials(1) |
| isolate_host | 2 | 2 | 100.0% | - |
| monitor_only | 2 | 1 | 50.0% | collect_forensics(1) |
| rotate_credentials | 2 | 0 | 0.0% | isolate_host(1), collect_forensics(1) |

### Misclassified Cases (LOOCV)

| Case ID | True Label | Predicted |
|---------|------------|-----------|
| soc_train_003 | rotate_credentials | isolate_host |
| soc_train_004 | block_ip_temporarily | collect_forensics |
| soc_train_005 | collect_forensics | monitor_only |
| soc_train_006 | monitor_only | collect_forensics |
| soc_train_008 | escalate_p1 | rotate_credentials |
| soc_train_010 | rotate_credentials | collect_forensics |
| soc_train_012 | collect_forensics | monitor_only |

### Confusion Matrix

| | block_ip_temporarily | collect_forensics | do_nothing_validated | escalate_p1 | isolate_host | monitor_only | rotate_credentials |
|---|---|---|---|---|---|---|---|
| **block_ip_temporarily** | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| **collect_forensics** | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| **do_nothing_validated** | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| **escalate_p1** | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| **isolate_host** | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| **monitor_only** | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| **rotate_credentials** | 0 | 1 | 0 | 0 | 1 | 0 | 0 |

## sre

- **Cases**: 24  |  **Classes**: 8
- **Train accuracy**: 100.0%
- **LOOCV accuracy**: 100.0% (24/24)
- **2-fold CV**: 100.0% +/- 0.0% (folds: 100.0%, 100.0%)

### Label Distribution

| Action | Count |
|--------|------:|
| enable_readonly_mode | 4 |
| page_human_operator | 4 |
| rollback_deploy | 3 |
| failover_region | 3 |
| restart_service | 3 |
| drain_node | 3 |
| scale_out | 2 |
| gather_more_telemetry | 2 |

### Per-Class LOOCV Accuracy

| Action | Support | Correct | Accuracy | Errors |
|--------|--------:|--------:|---------:|--------|
| drain_node | 3 | 3 | 100.0% | - |
| enable_readonly_mode | 4 | 4 | 100.0% | - |
| failover_region | 3 | 3 | 100.0% | - |
| gather_more_telemetry | 2 | 2 | 100.0% | - |
| page_human_operator | 4 | 4 | 100.0% | - |
| restart_service | 3 | 3 | 100.0% | - |
| rollback_deploy | 3 | 3 | 100.0% | - |
| scale_out | 2 | 2 | 100.0% | - |

### Confusion Matrix

| | drain_node | enable_readonly_mode | failover_region | gather_more_telemetry | page_human_operator | restart_service | rollback_deploy | scale_out |
|---|---|---|---|---|---|---|---|---|
| **drain_node** | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **enable_readonly_mode** | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| **failover_region** | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| **gather_more_telemetry** | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| **page_human_operator** | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 |
| **restart_service** | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| **rollback_deploy** | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| **scale_out** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |

## Key Findings

- **Perfect LOOCV**: sre (1/9 domains)
- **Below 100% LOOCV**: 8 domains
  - **customer_support**: 16.0% (21 misclassified)
  - **content_moderation**: 19.4% (25 misclassified)
  - **soc**: 50.0% (7 misclassified)
  - **finance**: 59.6% (23 misclassified)
  - **iam**: 75.0% (9 misclassified)
  - **medical**: 77.1% (8 misclassified)
  - **grid**: 77.5% (9 misclassified)
  - **drone**: 96.0% (1 misclassified)
- **Mean LOOCV across domains**: 63.4%
- **Min LOOCV**: 16.0%
