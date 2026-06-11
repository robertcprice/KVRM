# scripts/

Repo-root-anchored entry points and maintenance utilities. Run them from the
repository root (e.g. `python scripts/train_kvrm_model.py ...`); each resolves
paths relative to the repo root, not its own location.

## Entry points
| Script | Purpose |
|---|---|
| `kvrm_tui.py` | Operator TUI — per-case audit, draft curation, replay browser, training audit, decision explanations. |
| `train_kvrm_model.py` | Train a compact learned selector for one domain and save the `.joblib` artifact into `kvrm-models/`. |
| `run_full_benchmark.py` | Run the full canonical benchmark across all domains. |
| `run_qwen_ollama_benchmark.py` | Run the external small-model baseline (Ollama-backed Qwen/Gemma) under the strict structured-output protocol. |
| `analyze_feature_ceiling.py` | Feature-ceiling separability analysis (separates selector failure from schema failure). |

## Maintenance utilities
| Script | Purpose |
|---|---|
| `run_sre_schema_upgrade.py` | One-off SRE registry/schema migration. |
| `expand_datasets.py` | Grow per-domain case datasets. |
| `generate_cases_v3.py`, `generate_sre_v4.py` | Dataset generators for specific domain/version revisions. |
| `fix_demo_pythonpath.py`, `flatten_demo_layout.py` | Demo-package layout normalizers. |

The canonical publication pipeline lives separately under `kvrm-bench/scripts/`.
