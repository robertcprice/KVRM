# kvrm-bench-results/

Committed **evidence snapshots** — the curated, paper-facing benchmark outputs
that the manuscript and appendix cite. (The regenerable working outputs live in
the gitignored `kvrm-bench/results/`; this directory holds the snapshots kept
under version control.)

| Subdir | Evidence |
|---|---|
| `adversarial_stress/` | Near-boundary adversarial robustness |
| `scale/` | Throughput and latency profiling |
| `calibration/` | ECE / Brier calibration analysis |
| `generalization/` | LOOCV / K-fold cross-validation |
| `overlap_analysis/` | Support-spec overlap disambiguation |
| `shap/` | Directional feature importance (SHAP) |
| `interpretability/` | Feature-importance analysis |

These are referenced from `docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md` (Artifact
References) and validated by `tests/kvrm_bench/`.
