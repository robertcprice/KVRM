# KVRM Demo Tests

This directory is the canonical home for domain-specific demo regression tests.

Layout:
- `soc/` validates the SOC playbook router
- `sre/` validates the SRE policy router
- `drone/` validates the drone mission router
- `grid/` validates the grid operations router
- `finance/` validates the finance risk router
- `medical/` validates the medical workflow router
- `iam/` validates the IAM access router

The root `tests/` tree is reserved for shared package tests such as `kvrm_core` and `kvrm_bench`.
