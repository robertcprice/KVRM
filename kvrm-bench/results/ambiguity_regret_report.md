# KVRM Ambiguity-Regret Report

Generated: 2026-04-10T18:38:04.457147+00:00

The ambiguity frontier is derived from the live review-queue heuristic used by the TUI. Cases enter the slice when they exhibit one or more of the selected high-signal flags: `strategy_disagreement`, `fallback_path`, `low_confidence`, `supported_ood`, `unsupported_case`, `selector_abstention`, `hybrid_incorrect`.

This benchmark is case-slice-oriented rather than stress-injection-oriented: it measures how KVRM and its component strategies behave on the real hard cases already present in the canonical packs, with explicit regret and decision-cost accounting.

| Domain | Frontier Cases | Rate | Hybrid Regret | Best Non-Hybrid | Baseline Regret | Gain | Hybrid Cost | Baseline Cost | Hybrid Severe | Baseline Severe |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| soc | 124 | 0.9841 | 0.0000 | prototype | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
Flags `soc`: fallback_path=48, low_confidence=2, strategy_disagreement=76, supported_ood=52, unsupported_case=38
Slice `soc`: supported=86, unsupported=38, ood_supported=52

| sre | 140 | 1.0000 | 0.0000 | prototype | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
Flags `sre`: fallback_path=57, strategy_disagreement=83, supported_ood=63, unsupported_case=46
Slice `sre`: supported=94, unsupported=46, ood_supported=63

| drone | 145 | 0.9932 | 0.0000 | prototype | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
Flags `drone`: fallback_path=59, strategy_disagreement=86, supported_ood=74, unsupported_case=48
Slice `drone`: supported=97, unsupported=48, ood_supported=74

| grid | 24 | 1.0000 | 0.0000 | prototype | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
Flags `grid`: fallback_path=8, strategy_disagreement=16, supported_ood=18, unsupported_case=6
Slice `grid`: supported=18, unsupported=6, ood_supported=18

| finance | 17 | 0.7083 | 0.0000 | semantic | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
Flags `finance`: fallback_path=9, strategy_disagreement=8, supported_ood=10, unsupported_case=6
Slice `finance`: supported=11, unsupported=6, ood_supported=10

| medical | 18 | 0.7500 | 0.0000 | prototype | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
Flags `medical`: fallback_path=8, strategy_disagreement=10, supported_ood=10, unsupported_case=6
Slice `medical`: supported=12, unsupported=6, ood_supported=10

| iam | 24 | 1.0000 | 0.0000 | prototype | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
Flags `iam`: fallback_path=18, strategy_disagreement=12, supported_ood=11, unsupported_case=6
Slice `iam`: supported=18, unsupported=6, ood_supported=11

