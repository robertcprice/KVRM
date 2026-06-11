# tests/

Test suite for the KVRM flagship artifact.

- `kvrm_bench/` — the canonical, publication-critical suite (benchmark families,
  publication pipeline, paper-doc sync, operator pipeline). This is the suite
  the publication gate depends on; keep it green.

## Running
```bash
python -m pytest tests/kvrm_bench -q     # canonical suite (≈131 tests, ~2.5 min)
python -m pytest tests/ -q               # everything discoverable
```

Some tests require optional dependencies (`shap` for interpretability) or live
services (Ollama for external-baseline tests); those skip or fail closed when
the dependency is absent rather than masking a regression in the core suite.
