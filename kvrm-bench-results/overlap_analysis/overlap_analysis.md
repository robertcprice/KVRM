# KVRM Support-Spec Overlap Analysis

Generated: 2026-04-13T03:04:12.374519+00:00

## Cross-Domain Summary

| Domain | Supported Cases | Overlap Cases | Overlap % | Overlap Acc | Non-Overlap Acc | All Acc | Gap (pp) |
|--------|----------------:|-------------:|----------:|------------:|----------------:|--------:|---------:|
| soc | 88 | 0 | 0.00% | 0.00% | 100.00% | 100.00% | n/a |
| sre | 94 | 0 | 0.00% | 0.00% | 100.00% | 100.00% | n/a |
| drone | 98 | 0 | 0.00% | 0.00% | 100.00% | 100.00% | n/a |
| grid | 18 | 0 | 0.00% | 0.00% | 100.00% | 100.00% | n/a |
| finance | 18 | 0 | 0.00% | 0.00% | 100.00% | 100.00% | n/a |
| medical | 18 | 0 | 0.00% | 0.00% | 100.00% | 100.00% | n/a |
| iam | 18 | 0 | 0.00% | 0.00% | 100.00% | 100.00% | n/a |
| customer_support | 36 | 31 | 86.11% | 100.00% | 100.00% | 100.00% | 0.0 |
| content_moderation | 40 | 33 | 82.50% | 100.00% | 100.00% | 100.00% | 0.0 |

## SOC

- Actions: 8
- Supported eval cases: 88
- Overlap cases: 0 (0.00%)
- Non-overlap cases: 88

### Disambiguation Accuracy

- **Overlap zone**: 0/0 = 0.00% (mean conf 0.0000, mean margin n/a)
- **Non-overlap zone**: 88/88 = 100.00% (mean conf 0.9249)
- **All supported**: 88/88 = 100.00%

## SRE

- Actions: 8
- Supported eval cases: 94
- Overlap cases: 0 (0.00%)
- Non-overlap cases: 94

### Disambiguation Accuracy

- **Overlap zone**: 0/0 = 0.00% (mean conf 0.0000, mean margin n/a)
- **Non-overlap zone**: 94/94 = 100.00% (mean conf 0.9434)
- **All supported**: 94/94 = 100.00%

## DRONE

- Actions: 8
- Supported eval cases: 98
- Overlap cases: 0 (0.00%)
- Non-overlap cases: 98

### Disambiguation Accuracy

- **Overlap zone**: 0/0 = 0.00% (mean conf 0.0000, mean margin n/a)
- **Non-overlap zone**: 98/98 = 100.00% (mean conf 0.9820)
- **All supported**: 98/98 = 100.00%

## GRID

- Actions: 8
- Supported eval cases: 18
- Overlap cases: 0 (0.00%)
- Non-overlap cases: 18

### Disambiguation Accuracy

- **Overlap zone**: 0/0 = 0.00% (mean conf 0.0000, mean margin n/a)
- **Non-overlap zone**: 18/18 = 100.00% (mean conf 0.8173)
- **All supported**: 18/18 = 100.00%

## FINANCE

- Actions: 8
- Supported eval cases: 18
- Overlap cases: 0 (0.00%)
- Non-overlap cases: 18

### Disambiguation Accuracy

- **Overlap zone**: 0/0 = 0.00% (mean conf 0.0000, mean margin n/a)
- **Non-overlap zone**: 18/18 = 100.00% (mean conf 0.9717)
- **All supported**: 18/18 = 100.00%

## MEDICAL

- Actions: 8
- Supported eval cases: 18
- Overlap cases: 0 (0.00%)
- Non-overlap cases: 18

### Disambiguation Accuracy

- **Overlap zone**: 0/0 = 0.00% (mean conf 0.0000, mean margin n/a)
- **Non-overlap zone**: 18/18 = 100.00% (mean conf 0.9667)
- **All supported**: 18/18 = 100.00%

## IAM

- Actions: 7
- Supported eval cases: 18
- Overlap cases: 0 (0.00%)
- Non-overlap cases: 18

### Disambiguation Accuracy

- **Overlap zone**: 0/0 = 0.00% (mean conf 0.0000, mean margin n/a)
- **Non-overlap zone**: 18/18 = 100.00% (mean conf 0.9905)
- **All supported**: 18/18 = 100.00%

## CUSTOMER SUPPORT

- Actions: 7
- Supported eval cases: 36
- Overlap cases: 31 (86.11%)
- Non-overlap cases: 5

### Overlap Action Pairs

- `escalate_to_manager` vs `request_human_review`: 8 cases
- `assign_specialist` vs `request_human_review`: 7 cases
- `request_human_review` vs `send_knowledge_article`: 6 cases
- `auto_resolve_billing` vs `request_human_review`: 6 cases
- `request_human_review` vs `schedule_callback`: 6 cases
- `issue_refund` vs `request_human_review`: 5 cases
- `assign_specialist` vs `schedule_callback`: 2 cases
- `escalate_to_manager` vs `issue_refund`: 2 cases
- `auto_resolve_billing` vs `send_knowledge_article`: 1 cases
- `escalate_to_manager` vs `schedule_callback`: 1 cases
- `auto_resolve_billing` vs `issue_refund`: 1 cases

### Per-Pair Disambiguation

| Pair | Cases | Accuracy | Mean Conf | Mean Margin |
|------|------:|---------:|----------:|------------:|
| escalate_to_manager vs request_human_review | 8 | 100.00% | 0.8894 | 0.0263 |
| assign_specialist vs request_human_review | 7 | 100.00% | 0.8921 | 0.0400 |
| request_human_review vs send_knowledge_article | 6 | 100.00% | 0.8953 | 0.0400 |
| auto_resolve_billing vs request_human_review | 6 | 100.00% | 0.9457 | 0.0400 |
| request_human_review vs schedule_callback | 6 | 100.00% | 0.9496 | 0.0677 |
| issue_refund vs request_human_review | 5 | 100.00% | 0.9396 | 0.0400 |
| assign_specialist vs schedule_callback | 2 | 100.00% | 1.0000 | 0.0400 |
| escalate_to_manager vs issue_refund | 2 | 100.00% | 0.9260 | 0.0400 |
| auto_resolve_billing vs send_knowledge_article | 1 | 100.00% | 1.0000 | 0.0400 |
| escalate_to_manager vs schedule_callback | 1 | 100.00% | 0.9289 | 0.0089 |
| auto_resolve_billing vs issue_refund | 1 | 100.00% | 1.0000 | 0.0400 |

### Disambiguation Accuracy

- **Overlap zone**: 31/31 = 100.00% (mean conf 0.9039, mean margin 0.0497)
- **Non-overlap zone**: 5/5 = 100.00% (mean conf 0.8459)
- **All supported**: 36/36 = 100.00%

## CONTENT MODERATION

- Actions: 7
- Supported eval cases: 40
- Overlap cases: 33 (82.50%)
- Non-overlap cases: 7

### Overlap Action Pairs

- `remove_content` vs `request_human_review`: 13 cases
- `remove_content` vs `suspend_account`: 9 cases
- `request_human_review` vs `suspend_account`: 9 cases
- `flag_for_human_review` vs `request_human_review`: 8 cases
- `reduce_visibility` vs `request_human_review`: 7 cases
- `escalate_trust_safety` vs `request_human_review`: 7 cases
- `auto_approve` vs `request_human_review`: 5 cases
- `escalate_trust_safety` vs `remove_content`: 4 cases
- `escalate_trust_safety` vs `suspend_account`: 3 cases
- `flag_for_human_review` vs `reduce_visibility`: 1 cases
- `flag_for_human_review` vs `remove_content`: 1 cases
- `flag_for_human_review` vs `suspend_account`: 1 cases
- `escalate_trust_safety` vs `flag_for_human_review`: 1 cases

### Per-Pair Disambiguation

| Pair | Cases | Accuracy | Mean Conf | Mean Margin |
|------|------:|---------:|----------:|------------:|
| remove_content vs request_human_review | 13 | 100.00% | 0.9354 | 0.0386 |
| remove_content vs suspend_account | 9 | 100.00% | 0.9788 | 0.0386 |
| request_human_review vs suspend_account | 9 | 100.00% | 0.9788 | 0.0386 |
| flag_for_human_review vs request_human_review | 8 | 100.00% | 0.9705 | 0.0519 |
| reduce_visibility vs request_human_review | 7 | 100.00% | 0.9221 | 0.0400 |
| escalate_trust_safety vs request_human_review | 7 | 100.00% | 0.9481 | 0.0459 |
| auto_approve vs request_human_review | 5 | 100.00% | 0.9539 | 0.0333 |
| escalate_trust_safety vs remove_content | 4 | 100.00% | 0.9546 | 0.0400 |
| escalate_trust_safety vs suspend_account | 3 | 100.00% | 1.0000 | 0.0400 |
| flag_for_human_review vs reduce_visibility | 1 | 100.00% | 1.0000 | 0.0400 |
| flag_for_human_review vs remove_content | 1 | 100.00% | 1.0000 | 0.0400 |
| flag_for_human_review vs suspend_account | 1 | 100.00% | 1.0000 | 0.0400 |
| escalate_trust_safety vs flag_for_human_review | 1 | 100.00% | 0.9636 | 0.0636 |

### Disambiguation Accuracy

- **Overlap zone**: 33/33 = 100.00% (mean conf 0.9395, mean margin 0.0434)
- **Non-overlap zone**: 7/7 = 100.00% (mean conf 0.8632)
- **All supported**: 40/40 = 100.00%

### Content Moderation Synthetic Overlap Zone

Generated 25 synthetic cases in the reduce_visibility / flag_for_human_review overlap.

- **Accuracy**: 14/25 = 56.00%
- **Mean confidence**: 0.9038
- **Mean margin**: 0.0515

- Expected `flag_for_human_review`: 11/12 correct
- Expected `reduce_visibility`: 3/13 correct

#### Misclassified Synthetic Cases

| Case ID | Expected | Predicted | Confidence | Margin |
|---------|----------|-----------|----------:|-------:|
| cm_synth_overlap_004 | flag_for_human_review | reduce_visibility | 0.9152 | 0.0152 |
| cm_synth_overlap_005 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0333 |
| cm_synth_overlap_007 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0061 |
| cm_synth_overlap_009 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0333 |
| cm_synth_overlap_011 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0061 |
| cm_synth_overlap_013 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0818 |
| cm_synth_overlap_015 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0667 |
| cm_synth_overlap_017 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0212 |
| cm_synth_overlap_021 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0697 |
| cm_synth_overlap_023 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0515 |
| cm_synth_overlap_025 | reduce_visibility | flag_for_human_review | 0.9000 | 0.0697 |

## Interpretation

- **Overlap fraction** = proportion of supported cases where 2+ actions' support_specs both match.
- **Accuracy gap** = non-overlap accuracy minus overlap accuracy (in percentage points).
  A positive gap means overlaps are harder to disambiguate than non-overlapping cases.
- When the gap is large, the hybrid selector relies on evidence beyond support_spec matching
  (retrieval bank, rules, prototypes) to choose the right action.
- The content-moderation synthetic analysis stress-tests the intentional overlap between
  `reduce_visibility` and `flag_for_human_review` at `toxicity_level=moderate`.
