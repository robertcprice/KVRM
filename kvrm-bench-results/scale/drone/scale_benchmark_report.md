# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:08:25.386324+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 1000  
**Total elapsed**: 17453.5 ms  
**Overall throughput**: 57.3 decisions/sec  
**All domains perfect**: True

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| drone | 1000 | 235092492288 | 112 | 888 | 0 | 1.0000 | 57.3/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| drone | 17.4092 ms | 16.5893 ms | 30.5205 ms | 45.9684 ms | 95.3103 ms |
