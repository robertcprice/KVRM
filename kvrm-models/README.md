# kvrm-models/

Trained compact **learned-selector** artifacts, one per domain
(`<domain>_compact_selector_v1.joblib`), plus their `*_training_report.json`
metrics. These are the learned member of the selector ensemble; the hybrid
selector fuses them with the rule/retrieval/prototype/semantic selectors.

Regenerate an artifact:
```bash
python scripts/train_kvrm_model.py --domain <domain>
```

Note: `.joblib` files are pinned to a scikit-learn version; a version mismatch
produces an `InconsistentVersionWarning` on load (harmless — tests still pass —
but retrain to silence it).
