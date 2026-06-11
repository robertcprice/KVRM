# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:09:32.317875+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 1000  
**Total elapsed**: 18367.0 ms  
**Overall throughput**: 54.5 decisions/sec  
**All domains perfect**: False

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| soc | 1000 | 7200 | 162 | 838 | 2 | 0.9938 | 54.5/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| soc | 18.3198 ms | 17.2336 ms | 25.4529 ms | 46.2980 ms | 94.8096 ms |
