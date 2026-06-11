# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:09:00.343623+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 1000  
**Total elapsed**: 7856.1 ms  
**Overall throughput**: 127.3 decisions/sec  
**All domains perfect**: False

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| grid | 1000 | 186624 | 36 | 964 | 0 | 0.4444 | 127.3/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| grid | 7.8254 ms | 0.2552 ms | 20.5177 ms | 25.1490 ms | 99.9994 ms |
