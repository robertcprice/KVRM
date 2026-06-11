# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:08:09.990162+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 1000  
**Total elapsed**: 15248.3 ms  
**Overall throughput**: 65.6 decisions/sec  
**All domains perfect**: False

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| customer_support | 1000 | 36864 | 20 | 980 | 0 | 0.7500 | 65.6/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| customer_support | 15.2103 ms | 16.9661 ms | 24.8766 ms | 31.5100 ms | 84.2977 ms |
