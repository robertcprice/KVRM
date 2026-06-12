# KVRM — Agent Onboarding

Registry-constrained decision architecture: fail-closed routing among finite,
audited actions. Read `AGENTS.md` for governance and working conventions;
this file is the fast path to being productive.

## Setup & verification

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e kvrm-core/ -e kvrm-bench/
for d in kvrm-demos/*/; do [ -f "${d}pyproject.toml" ] && pip install -e "$d"; done

python -m pytest tests kvrm-demos -q --ignore=tests/baselines   # full suite (~2 min)
python kvrm-bench/scripts/run_publication_check.py              # publication gate (must stay green)
```

`tests/baselines` needs a live Ollama server — skip unless working on external baselines.

## Map

| Path | What it is |
|---|---|
| `kvrm-core/src/kvrm_core/` | The library: types, registry, selectors, support gate, runtime, validation, `domain_factory`; `cli.py` is the `kvrm` console command and `domain_dir.py` is the bring-your-own-domain loader behind it |
| `kvrm-bench/src/kvrm_bench/` | Benchmarks + publication pipeline; its `cli.py` backs `kvrm demo` (bundled research packs) |
| `kvrm-demos/<domain>-router/` | 12 domains; each = `data/` (registry + cases) + `<domain>/domain.py` (a `DomainConfig`) |
| `kvrm-demos/run_demo.py` + `compare_demos.py` | Regenerate the canonical evidence (`kvrm-demos/reports/demo_comparison.json`) |
| `docs/papers/` | Manuscript (markdown = source of truth), evidence matrix, LaTeX build (`latex/build_paper.py`) |
| `examples/quickstart.py` | Five-minute pipeline walkthrough |

Top-level dirs `kvrm-llm-compiler/`, `kvrm-os/`, `kvrm-gpu/`, `kvrm-vector/`,
`kvrm-ecosystem/` are gitignored experimental satellites — not part of the
flagship artifact; do not import from them.

## Hard rules

- **Never hand-edit generated artifacts** (`docs/papers/KVRM_PUBLICATION_APPENDIX.md`, `kvrm-bench/results/publication_bundle/`, benchmark report tables). Regenerate them.
- **Benchmark numbers in prose must match the generated appendix.** After touching any registry, cases, or selector logic, rerun the affected domain benchmark and `run_publication_check.py`.
- **Domains use the factory pattern**: behavior lives in `DomainConfig` in `domain.py`. Do not add per-domain `selectors.py`/`executor.py` — that duplication was deliberately removed.
- **All 12 domains are in the canonical suite (682 cases).** "7 canonical" still applies to the ceiling, frontier, robustness-family, and registry-evolution analyses, which cover the original seven only (see `docs/papers/KVRM_PRE_SUBMISSION_CHECKLIST.md`).
- Tests live in `tests/` and `kvrm-demos/tests/`; new behavior needs tests in the matching tree.
