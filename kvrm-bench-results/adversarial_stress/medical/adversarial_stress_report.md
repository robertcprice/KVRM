# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:11:12.233456+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=0, ties=1, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| medical | 200 | 75 | 125 | 0 | 1.0000 | semantic | 1.0000 | 0.0000 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| medical | single_condition_miss | 75 | 1.0000 | 0.0000 | 0.7867 |
| medical | boundary_step | 125 | 1.0000 | 0.0000 | 0.0480 |
