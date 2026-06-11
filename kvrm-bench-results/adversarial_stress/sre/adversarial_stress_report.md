# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:07:57.830646+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=1, ties=0, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| sre | 1850 | 625 | 1225 | 0 | 1.0000 | prototype | 0.9948 | 0.0052 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| sre | single_condition_miss | 625 | 1.0000 | 0.0000 | 0.9920 |
| sre | boundary_step | 1225 | 1.0000 | 0.0000 | 0.2245 |
