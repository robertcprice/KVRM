# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:11:37.412863+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=0, ties=1, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| content_moderation | 573 | 115 | 449 | 9 | 0.6268 | prototype | 0.6268 | 0.0000 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| content_moderation | single_condition_miss | 115 | 0.8750 | 0.0000 | 0.0261 |
| content_moderation | boundary_step | 449 | 0.6132 | 0.0000 | 0.0022 |
| content_moderation | multi_action_competition | 9 | 0.3333 | 0.0000 | 0.0000 |
