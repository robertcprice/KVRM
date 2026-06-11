# baselines/

External comparison baselines for the paper's "real small-model" evaluation.

- `qwen-baseline/` — Ollama-backed small-model selectors (Qwen3 0.6b/1.7b,
  Qwen3.5 0.8b, Gemma4 e2b) evaluated under the strict structured-output
  protocol. Outputs in `qwen-baseline/outputs/ollama/live_canonical/` feed the
  external-baseline table in the manuscript. Regenerate with
  `python scripts/run_qwen_ollama_benchmark.py` (requires a running Ollama).
- `finetune/` — **gitignored** (1.7G). The fine-tuning ceiling experiment
  (fine-tuning a small model on KVRM cases performed *worse* than few-shot,
  reinforcing that KVRM's advantage is architectural, not predictive). The
  negative result is documented in the paper/memory; the raw checkpoints are
  not committed.
