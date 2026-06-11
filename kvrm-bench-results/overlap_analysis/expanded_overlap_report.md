# KVRM Expanded Overlap Stress-Test Report

Generated: 2026-04-13T13:12:52.016734+00:00

## Overview

This report analyses synthetic overlap cases generated for domains with
known high-overlap action pairs.  The goal is to identify which overlaps
are genuinely hard to disambiguate (accuracy < 80%) versus easily handled
by the hybrid selector.

## Hard Pairs (Accuracy < 80%)

No pairs with accuracy below 80% -- the hybrid selector handles all overlaps well.

## Easy Pairs (Accuracy >= 80%)

| Domain | Pair | Cases | Accuracy | Mean Conf | Mean Margin |
|--------|------|------:|---------:|----------:|------------:|
| content_moderation | remove_content vs request_human_review | 13 | 100.00% | 0.9354 | 0.0386 |
| content_moderation | remove_content vs suspend_account | 9 | 100.00% | 0.9788 | 0.0386 |
| content_moderation | request_human_review vs suspend_account | 9 | 100.00% | 0.9788 | 0.0386 |
| content_moderation | flag_for_human_review vs request_human_review | 8 | 100.00% | 0.9705 | 0.0519 |
| content_moderation | reduce_visibility vs request_human_review | 7 | 100.00% | 0.9221 | 0.0400 |
| content_moderation | escalate_trust_safety vs request_human_review | 7 | 100.00% | 0.9481 | 0.0459 |
| content_moderation | auto_approve vs request_human_review | 5 | 100.00% | 0.9539 | 0.0333 |
| content_moderation | escalate_trust_safety vs remove_content | 4 | 100.00% | 0.9546 | 0.0400 |
| content_moderation | escalate_trust_safety vs suspend_account | 3 | 100.00% | 1.0000 | 0.0400 |
| content_moderation | flag_for_human_review vs reduce_visibility | 1 | 100.00% | 1.0000 | 0.0400 |
| content_moderation | flag_for_human_review vs remove_content | 1 | 100.00% | 1.0000 | 0.0400 |
| content_moderation | flag_for_human_review vs suspend_account | 1 | 100.00% | 1.0000 | 0.0400 |
| content_moderation | escalate_trust_safety vs flag_for_human_review | 1 | 100.00% | 0.9636 | 0.0636 |
| customer_support | escalate_to_manager vs request_human_review | 8 | 100.00% | 0.8894 | 0.0263 |
| customer_support | assign_specialist vs request_human_review | 7 | 100.00% | 0.8921 | 0.0400 |
| customer_support | request_human_review vs send_knowledge_article | 6 | 100.00% | 0.8953 | 0.0400 |
| customer_support | auto_resolve_billing vs request_human_review | 6 | 100.00% | 0.9457 | 0.0400 |
| customer_support | request_human_review vs schedule_callback | 6 | 100.00% | 0.9496 | 0.0677 |
| customer_support | issue_refund vs request_human_review | 5 | 100.00% | 0.9396 | 0.0400 |
| customer_support | assign_specialist vs schedule_callback | 2 | 100.00% | 1.0000 | 0.0400 |
| customer_support | escalate_to_manager vs issue_refund | 2 | 100.00% | 0.9260 | 0.0400 |
| customer_support | auto_resolve_billing vs send_knowledge_article | 1 | 100.00% | 1.0000 | 0.0400 |
| customer_support | escalate_to_manager vs schedule_callback | 1 | 100.00% | 0.9289 | 0.0089 |
| customer_support | auto_resolve_billing vs issue_refund | 1 | 100.00% | 1.0000 | 0.0400 |

## CONTENT MODERATION Detail

- Actions: 7
- Supported cases: 40
- Overlap cases: 33 (82.50%)

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

### Per-Pair Disambiguation (Real Cases)

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

### Synthetic Overlap Stress-Test

- **Total synthetic cases**: 25
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

## CUSTOMER SUPPORT Detail

- Actions: 7
- Supported cases: 36
- Overlap cases: 31 (86.11%)

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

### Per-Pair Disambiguation (Real Cases)

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

### Synthetic Overlap Stress-Test

- **Total synthetic cases**: 75
- **Accuracy**: 63/75 = 84.00%
- **Mean confidence**: 0.7803
- **Mean margin**: 0.0879

#### Per-Pair Synthetic Breakdown

| Pair | Generated | Accuracy | Mean Conf | Mean Margin |
|------|----------:|---------:|----------:|------------:|
| escalate_to_manager vs request_human_review | 25 | 84.00% | 0.7316 | n/a |
| assign_specialist vs request_human_review | 25 | 76.00% | 0.7815 | 0.0879 |
| request_human_review vs send_knowledge_article | 25 | 92.00% | 0.8279 | n/a |

- Expected `assign_specialist`: 19/25 correct
- Expected `escalate_to_manager`: 21/25 correct
- Expected `send_knowledge_article`: 23/25 correct

#### Misclassified Synthetic Cases

| Case ID | Expected | Predicted | Confidence | Margin |
|---------|----------|-----------|----------:|-------:|
| cs_synth_escalate_to_manager_vs_request_human_review_002 | escalate_to_manager | request_human_review | 0.9200 | n/a |
| cs_synth_escalate_to_manager_vs_request_human_review_005 | escalate_to_manager | request_human_review | 0.9200 | n/a |
| cs_synth_escalate_to_manager_vs_request_human_review_019 | escalate_to_manager | request_human_review | 0.9200 | n/a |
| cs_synth_escalate_to_manager_vs_request_human_review_025 | escalate_to_manager | request_human_review | 0.9200 | n/a |
| cs_synth_assign_specialist_vs_request_human_review_030 | assign_specialist | request_human_review | 0.7274 | n/a |
| cs_synth_assign_specialist_vs_request_human_review_032 | assign_specialist | request_human_review | 0.8459 | n/a |
| cs_synth_assign_specialist_vs_request_human_review_035 | assign_specialist | request_human_review | 0.7570 | n/a |
| cs_synth_assign_specialist_vs_request_human_review_040 | assign_specialist | schedule_callback | 0.9200 | 0.0741 |
| cs_synth_assign_specialist_vs_request_human_review_046 | assign_specialist | schedule_callback | 0.9407 | 0.0207 |
| cs_synth_assign_specialist_vs_request_human_review_049 | assign_specialist | schedule_callback | 0.9200 | 0.1689 |
| cs_synth_request_human_review_vs_send_knowledge_article_056 | send_knowledge_article | request_human_review | 0.7867 | n/a |
| cs_synth_request_human_review_vs_send_knowledge_article_069 | send_knowledge_article | request_human_review | 0.8815 | n/a |

## Key Insight: Hard vs Easy Disambiguation

**Hard pairs** (accuracy < 80%) represent overlap zones where the hybrid
selector's evidence signals (retrieval bank, rules, prototypes, semantic
matching) are insufficient to reliably distinguish the two actions.  These
pairs are candidates for:

  1. Additional discriminating features in the support_spec
  2. More training cases in the retrieval bank for these specific overlaps
  3. Targeted rules that capture the domain design intent

**Easy pairs** (accuracy >= 80%) show the hybrid selector successfully
disambiguates despite the support_spec overlap -- the non-spec evidence
(retrieval exemplars, rule lookups, prototype distance) provides enough
signal.
