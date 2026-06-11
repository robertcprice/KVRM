# KVRM Scale Benchmark Report

Generated: 2026-04-13T02:10:08.144284+00:00

This benchmark generates 1000+ synthetic cases per domain by enumerating the full feature space (cartesian product of enum and boolean values) and random-sampling when the space exceeds the target count.  Each case is labelled by evaluating every action's support_spec.

**Total cases**: 9000  
**Total elapsed**: 134670.3 ms  
**Overall throughput**: 66.8 decisions/sec  
**All domains perfect**: False

## Per-Domain Results

| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| content_moderation | 1000 | 160000 | 388 | 612 | 41 | 0.3969 | 58.0/s |
| customer_support | 1000 | 36864 | 20 | 980 | 0 | 0.7500 | 65.6/s |
| drone | 1000 | 235092492288 | 112 | 888 | 0 | 1.0000 | 57.3/s |
| finance | 1000 | 15552 | 621 | 379 | 2 | 0.9968 | 57.6/s |
| grid | 1000 | 186624 | 36 | 964 | 0 | 0.4444 | 127.3/s |
| iam | 1000 | 1574640 | 0 | 1000 | 0 | 0.0000 | 169.1/s |
| medical | 1000 | 25920 | 232 | 768 | 3 | 0.9914 | 55.7/s |
| soc | 1000 | 7200 | 162 | 838 | 2 | 0.9938 | 54.5/s |
| sre | 1000 | 43459459338240 | 22 | 978 | 1 | 0.0909 | 57.8/s |

## Latency Profile

| Domain | Mean | P50 | P95 | P99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| content_moderation | 17.1895 ms | 18.0318 ms | 28.0697 ms | 44.8483 ms | 103.3759 ms |
| customer_support | 15.2103 ms | 16.9661 ms | 24.8766 ms | 31.5100 ms | 84.2977 ms |
| drone | 17.4092 ms | 16.5893 ms | 30.5205 ms | 45.9684 ms | 95.3103 ms |
| finance | 17.3072 ms | 16.4844 ms | 23.3589 ms | 33.5280 ms | 93.3858 ms |
| grid | 7.8254 ms | 0.2552 ms | 20.5177 ms | 25.1490 ms | 99.9994 ms |
| iam | 5.8877 ms | 0.1619 ms | 19.9515 ms | 23.7653 ms | 59.9300 ms |
| medical | 17.9167 ms | 17.1043 ms | 24.0050 ms | 38.3170 ms | 64.3913 ms |
| soc | 18.3198 ms | 17.2336 ms | 25.4529 ms | 46.2980 ms | 94.8096 ms |
| sre | 17.2450 ms | 16.3931 ms | 24.4081 ms | 39.0124 ms | 58.5466 ms |
