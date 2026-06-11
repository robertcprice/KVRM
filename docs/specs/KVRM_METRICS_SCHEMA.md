# KVRM Metrics Schema

Required benchmark metrics:

- `structural_validity_rate`: fraction of cases whose final chosen action is inside the registry.
- `semantic_correctness_rate`: fraction of supported cases whose final outcome matches the expected action or utility target.
- `abstention_rate`: fraction of cases that explicitly abstain before execution.
- `fallback_rate`: fraction of cases resolved through deterministic fallback.
- `invalid_output_rate`: fraction of cases that produce an invalid action before fallback handling.
- `false_accept_rate`: fraction of unsupported cases incorrectly executed as supported actions.
- `latency_p50_ms`: median end-to-end runtime latency in milliseconds.
- `latency_p95_ms`: 95th percentile runtime latency in milliseconds.
- `latency_p99_ms`: 99th percentile runtime latency in milliseconds.
- `calibration_ece`: expected calibration error over confidence buckets when confidence values exist.
- `ood_accuracy_supported_only`: correctness rate on out-of-distribution supported cases.
- `unsupported_case_rejection_rate`: fraction of unsupported cases rejected via abstain or fail-closed behavior.
