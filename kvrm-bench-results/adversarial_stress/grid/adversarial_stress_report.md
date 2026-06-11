# KVRM Adversarial Near-Boundary Stress Report

Generated: 2026-04-13T02:10:57.656824+00:00

This benchmark generates adversarial cases designed to push KVRM to its limits. Three mutation types probe boundary behaviour: single-condition miss (flip one leaf condition), boundary enum step (one ordinal step on each enum feature), and multi-action competition (feature sets satisfying 2+ actions simultaneously).

Hybrid comparison summary: wins=0, ties=1, losses=0.

## Per-Domain Results

| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| grid | 294 | 128 | 166 | 0 | 0.9922 | prototype | 0.9922 | 0.0000 |

## Mutation-Type Breakdown (Hybrid Strategy)

| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| grid | single_condition_miss | 128 | 1.0000 | 0.0000 | 0.9219 |
| grid | boundary_step | 166 | 0.9915 | 0.0000 | 0.2952 |
