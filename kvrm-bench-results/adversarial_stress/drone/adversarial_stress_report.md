# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:09:08.756562+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=1, ties=0, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| drone | 3056 | 689 | 2367 | 0 | 1.0000 | prototype | 0.9610 | 0.0390 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| drone | single_condition_miss | 689 | 1.0000 | 0.0000 | 0.9158 |
| drone | boundary_step | 2367 | 1.0000 | 0.0000 | 0.1901 |
