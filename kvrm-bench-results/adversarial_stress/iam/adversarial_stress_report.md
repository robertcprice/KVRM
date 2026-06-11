# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:11:17.736959+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=0, ties=1, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| iam | 294 | 163 | 131 | 0 | 1.0000 | prototype | 1.0000 | 0.0000 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| iam | single_condition_miss | 163 | 0.0000 | 0.0000 | 0.8957 |
| iam | boundary_step | 131 | 1.0000 | 0.0000 | 0.4046 |
