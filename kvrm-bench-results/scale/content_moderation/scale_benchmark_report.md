# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:07:51.083125+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 1000  
**Total elapsed**: 17231.1 ms  
**Overall throughput**: 58.0 decisions/sec  
**All domains perfect**: False

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| content_moderation | 1000 | 160000 | 388 | 612 | 41 | 0.3969 | 58.0/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| content_moderation | 17.1895 ms | 18.0318 ms | 28.0697 ms | 44.8483 ms | 103.3759 ms |
