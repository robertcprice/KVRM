# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:09:14.285750+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 1000  
**Total elapsed**: 17958.0 ms  
**Overall throughput**: 55.7 decisions/sec  
**All domains perfect**: False

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| medical | 1000 | 25920 | 232 | 768 | 3 | 0.9914 | 55.7/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| medical | 17.9167 ms | 17.1043 ms | 24.0050 ms | 38.3170 ms | 64.3913 ms |
