# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:09:50.770083+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 1000  
**Total elapsed**: 17292.4 ms  
**Overall throughput**: 57.8 decisions/sec  
**All domains perfect**: False

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sre | 1000 | 43459459338240 | 22 | 978 | 1 | 0.0909 | 57.8/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| sre | 17.2450 ms | 16.3931 ms | 24.4081 ms | 39.0124 ms | 58.5466 ms |
