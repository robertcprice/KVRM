# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:11:53.382639+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=3, ties=6, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| soc | 701 | 256 | 445 | 0 | 0.9968 | prototype | 0.9968 | 0.0000 |
| sre | 1850 | 625 | 1225 | 0 | 1.0000 | prototype | 0.9948 | 0.0052 |
| drone | 3056 | 689 | 2367 | 0 | 1.0000 | prototype | 0.9610 | 0.0390 |
| grid | 294 | 128 | 166 | 0 | 0.9922 | prototype | 0.9922 | 0.0000 |
| finance | 213 | 83 | 130 | 0 | 1.0000 | semantic | 0.9921 | 0.0079 |
| medical | 200 | 75 | 125 | 0 | 1.0000 | semantic | 1.0000 | 0.0000 |
| iam | 294 | 163 | 131 | 0 | 1.0000 | prototype | 1.0000 | 0.0000 |
| customer_support | 466 | 156 | 308 | 2 | 0.8590 | prototype | 0.8590 | 0.0000 |
| content_moderation | 573 | 115 | 449 | 9 | 0.6268 | prototype | 0.6268 | 0.0000 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| soc | single_condition_miss | 256 | 0.9688 | 0.0000 | 0.8789 |
| soc | boundary_step | 445 | 1.0000 | 0.0000 | 0.3730 |
| sre | single_condition_miss | 625 | 1.0000 | 0.0000 | 0.9920 |
| sre | boundary_step | 1225 | 1.0000 | 0.0000 | 0.2245 |
| drone | single_condition_miss | 689 | 1.0000 | 0.0000 | 0.9158 |
| drone | boundary_step | 2367 | 1.0000 | 0.0000 | 0.1901 |
| grid | single_condition_miss | 128 | 1.0000 | 0.0000 | 0.9219 |
| grid | boundary_step | 166 | 0.9915 | 0.0000 | 0.2952 |
| finance | single_condition_miss | 83 | 1.0000 | 0.0000 | 0.5060 |
| finance | boundary_step | 130 | 1.0000 | 0.0000 | 0.1154 |
| medical | single_condition_miss | 75 | 1.0000 | 0.0000 | 0.7867 |
| medical | boundary_step | 125 | 1.0000 | 0.0000 | 0.0480 |
| iam | single_condition_miss | 163 | 0.0000 | 0.0000 | 0.8957 |
| iam | boundary_step | 131 | 1.0000 | 0.0000 | 0.4046 |
| customer_support | single_condition_miss | 156 | 0.9167 | 0.0000 | 0.2244 |
| customer_support | boundary_step | 308 | 0.8592 | 0.0000 | 0.0357 |
| customer_support | multi_action_competition | 2 | 0.5000 | 0.0000 | 0.0000 |
| content_moderation | single_condition_miss | 115 | 0.8750 | 0.0000 | 0.0261 |
| content_moderation | boundary_step | 449 | 0.6132 | 0.0000 | 0.0022 |
| content_moderation | multi_action_competition | 9 | 0.3333 | 0.0000 | 0.0000 |
