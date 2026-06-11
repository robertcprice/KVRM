# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:07:29.834227+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=0, ties=1, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| soc | 701 | 256 | 445 | 0 | 0.9968 | prototype | 0.9968 | 0.0000 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| soc | single_condition_miss | 256 | 0.9688 | 0.0000 | 0.8789 |
| soc | boundary_step | 445 | 1.0000 | 0.0000 | 0.3730 |
