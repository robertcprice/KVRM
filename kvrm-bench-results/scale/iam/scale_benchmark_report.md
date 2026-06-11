# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:09:08.281550+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 1000  
**Total elapsed**: 5915.5 ms  
**Overall throughput**: 169.1 decisions/sec  
**All domains perfect**: False

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| iam | 1000 | 1574640 | 0 | 1000 | 0 | 0.0000 | 169.1/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| iam | 5.8877 ms | 0.1619 ms | 19.9515 ms | 23.7653 ms | 59.9300 ms |
