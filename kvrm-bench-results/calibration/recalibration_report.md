# KVRM Hybrid Selector Post-Hoc Recalibration Report

**Generated**: 2026-04-13 13:05 UTC
**Strategy**: hybrid
**CV Method**: Leave-One-Out Cross-Validation (LOOCV)
**Scalers**: temperature, platt, isotonic
**Domains**: 9

## Cross-Domain Scaler Ranking

| Scaler | Mean Pre-ECE | Mean Post-ECE | ECE Improvement | Mean Pre-Brier | Mean Post-Brier | Brier Improvement |
|--------|-------------|--------------|-----------------|---------------|----------------|-------------------|
| isotonic | 0.2745 | 0.0858 | +65.7% | 0.2401 | 0.1129 | +52.1% |
| platt | 0.2745 | 0.2054 | +24.4% | 0.2401 | 0.1579 | +33.4% |
| temperature | 0.2745 | 0.2700 | +1.9% | 0.2401 | 0.1831 | +23.5% |

**Best scaler**: `isotonic` (mean post-ECE = 0.0858, improvement = +65.7%)

## Per-Domain Results

| Domain | Scaler | n | Pre-ECE | Post-ECE | ECE Delta | ECE Improvement | Pre-Brier | Post-Brier | Brier Delta |
|--------|--------|---|---------|----------|-----------|-----------------|-----------|------------|-------------|
| soc | temperature | 126 | 0.2846 | 0.1287 | -0.1559 | +54.8% | 0.2629 | 0.1986 | -0.0644 |
| soc | platt | 126 | 0.2846 | 0.1944 | -0.0902 | +31.7% | 0.2629 | 0.2164 | -0.0465 |
| soc | isotonic | 126 | 0.2846 | 0.0000 | -0.2846 | +100.0% | 0.2629 | 0.1395 | -0.1234 |
| sre | temperature | 140 | 0.2979 | 0.1467 | -0.1513 | +50.8% | 0.2823 | 0.1957 | -0.0866 |
| sre | platt | 140 | 0.2979 | 0.3878 | +0.0898 | -30.2% | 0.2823 | 0.2172 | -0.0651 |
| sre | isotonic | 140 | 0.2979 | 0.0000 | -0.2979 | +100.0% | 0.2823 | 0.1095 | -0.1728 |
| drone | temperature | 146 | 0.2917 | 0.3579 | +0.0662 | -22.7% | 0.2785 | 0.1826 | -0.0959 |
| drone | platt | 146 | 0.2917 | 0.0001 | -0.2917 | +100.0% | 0.2785 | 0.0000 | -0.2785 |
| drone | isotonic | 146 | 0.2917 | 0.0000 | -0.2917 | +100.0% | 0.2785 | 0.0000 | -0.2785 |
| grid | temperature | 24 | 0.3601 | 0.4571 | +0.0970 | -26.9% | 0.2390 | 0.2423 | +0.0033 |
| grid | platt | 24 | 0.3601 | 0.2813 | -0.0788 | +21.9% | 0.2390 | 0.1837 | -0.0553 |
| grid | isotonic | 24 | 0.3601 | 0.0000 | -0.3601 | +100.0% | 0.2390 | 0.1995 | -0.0394 |
| finance | temperature | 24 | 0.2200 | 0.2542 | +0.0342 | -15.6% | 0.2137 | 0.1573 | -0.0564 |
| finance | platt | 24 | 0.2200 | 0.3252 | +0.1052 | -47.8% | 0.2137 | 0.1913 | -0.0225 |
| finance | isotonic | 24 | 0.2200 | 0.2222 | +0.0023 | -1.0% | 0.2137 | 0.1235 | -0.0903 |
| medical | temperature | 24 | 0.2378 | 0.2557 | +0.0179 | -7.5% | 0.2145 | 0.1593 | -0.0552 |
| medical | platt | 24 | 0.2378 | 0.3611 | +0.1233 | -51.8% | 0.2145 | 0.2118 | -0.0026 |
| medical | isotonic | 24 | 0.2378 | 0.2347 | -0.0031 | +1.3% | 0.2145 | 0.1272 | -0.0873 |
| iam | temperature | 24 | 0.2223 | 0.1855 | -0.0367 | +16.5% | 0.2119 | 0.1451 | -0.0668 |
| iam | platt | 24 | 0.2223 | 0.0006 | -0.2217 | +99.7% | 0.2119 | 0.0000 | -0.2119 |
| iam | isotonic | 24 | 0.2223 | 0.0000 | -0.2223 | +100.0% | 0.2119 | 0.0000 | -0.2119 |
| customer_support | temperature | 48 | 0.2903 | 0.3199 | +0.0296 | -10.2% | 0.2280 | 0.1895 | -0.0385 |
| customer_support | platt | 48 | 0.2903 | 0.2515 | -0.0388 | +13.4% | 0.2280 | 0.1973 | -0.0307 |
| customer_support | isotonic | 48 | 0.2903 | 0.3103 | +0.0201 | -6.9% | 0.2280 | 0.1605 | -0.0675 |
| content_moderation | temperature | 54 | 0.2655 | 0.3239 | +0.0585 | -22.0% | 0.2302 | 0.1779 | -0.0523 |
| content_moderation | platt | 54 | 0.2655 | 0.0466 | -0.2189 | +82.5% | 0.2302 | 0.2033 | -0.0270 |
| content_moderation | isotonic | 54 | 0.2655 | 0.0045 | -0.2610 | +98.3% | 0.2302 | 0.1565 | -0.0737 |

## Key Findings

- **ECE improvement range**: [-51.8%, +100.0%]
- **Mean ECE improvement**: +30.7%
- **Mean Brier improvement**: +36.4%
- **temperature**: improved ECE in 3/9 domains
- **platt**: improved ECE in 6/9 domains
- **isotonic**: improved ECE in 7/9 domains
