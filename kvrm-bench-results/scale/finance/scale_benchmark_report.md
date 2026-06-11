# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:08:42.918213+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 1000  
**Total elapsed**: 17348.4 ms  
**Overall throughput**: 57.6 decisions/sec  
**All domains perfect**: False

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| finance | 1000 | 15552 | 621 | 379 | 2 | 0.9968 | 57.6/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| finance | 17.3072 ms | 16.4844 ms | 23.3589 ms | 33.5280 ms | 93.3858 ms |
