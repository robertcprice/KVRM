# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:11:06.301158+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=1, ties=0, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| finance | 213 | 83 | 130 | 0 | 1.0000 | semantic | 0.9921 | 0.0079 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| finance | single_condition_miss | 83 | 1.0000 | 0.0000 | 0.5060 |
| finance | boundary_step | 130 | 1.0000 | 0.0000 | 0.1154 |
