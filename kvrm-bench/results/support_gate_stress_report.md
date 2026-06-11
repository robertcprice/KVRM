# KVRM Support-Gate Stress Report

Generated: 2026-04-10T18:38:04.434582+00:00

Injected support-incompatible high-confidence candidates into the retrieval and rule stages at confidence `0.999`. The gated variant keeps registry-aware support filtering inside the hybrid selector; the ungated variant leaves invalid candidates to post-hoc runtime validation.

This benchmark is intentionally architecture-focused: both variants keep deterministic runtime validation, so the gap shows up in supported-case correctness, fallback pressure, and decision cost rather than in false accepts.

| Domain | Gated Semantic | Ungated Semantic | Gain | Gated Cost | Ungated Cost | Cost Reduction | Gated Trigger | Rescue | False Accept |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| soc | 1.0000 | 0.1136 | 0.8864 | 0.0000 | 0.2167 | 0.2167 | 0.6190 | 0.8864 | 0.0000 |
| sre | 1.0000 | 0.1170 | 0.8830 | 0.0000 | 0.2075 | 0.2075 | 0.5929 | 0.8830 | 0.0000 |
| drone | 1.0000 | 0.1122 | 0.8878 | 0.0000 | 0.2086 | 0.2086 | 0.5959 | 0.8878 | 0.0000 |
| grid | 1.0000 | 0.1111 | 0.8889 | 0.0000 | 0.2333 | 0.2333 | 0.6667 | 0.8889 | 0.0000 |
| finance | 1.0000 | 0.1667 | 0.8333 | 0.0000 | 0.2188 | 0.2188 | 0.7500 | 0.8333 | 0.0000 |
| medical | 1.0000 | 0.1111 | 0.8889 | 0.0000 | 0.2333 | 0.2333 | 0.7500 | 0.8889 | 0.0000 |
| iam | 1.0000 | 0.1111 | 0.8889 | 0.0000 | 0.2333 | 0.2333 | 0.7500 | 0.3333 | 0.0000 |
