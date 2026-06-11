# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:11:24.925435+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=0, ties=1, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| customer_support | 466 | 156 | 308 | 2 | 0.8590 | prototype | 0.8590 | 0.0000 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| customer_support | single_condition_miss | 156 | 0.9167 | 0.0000 | 0.2244 |
| customer_support | boundary_step | 308 | 0.8592 | 0.0000 | 0.0357 |
| customer_support | multi_action_competition | 2 | 0.5000 | 0.0000 | 0.0000 |
