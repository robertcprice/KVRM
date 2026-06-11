# AGENTS.md — KVRM Project Guidance

This file codifies how to work in the KVRM repository. Treat the monorepo with care: it contains multiple research threads of varying maturity under one name.

## Core Identity

**Primary valuable artifact**: The registry-constrained decision architecture (kvrm-core + kvrm-bench + kvrm-demos) for fail-closed finite-action routing in safety-adjacent domains.

- 9–12 domains, 90 actions, 682 eval cases
- Structural guarantees: 1.0 semantic correctness, 0.0 false accept rate on canonical suites
- 231+ tests (as of 2026-04)
- Full publication automation with audit gates (15/15 checks), submission export, LaTeX rendering

**KVRM brand collision**: "KVRM" is overloaded.
- Main line (this README focus): **Registry-Constrained Decision Architectures** (support specs, evidence fusion hybrid, strict validator).
- kvrm-llm-compiler/: Earlier/experimental **Key-Value Router Machine** — a verified neural instruction decoder / LLM-as-CPU project (7+ GB artifacts, separate papers). Not the same architecture.
- kvrm-gpu/: GPU kernel selection / tiled attention application of KVRM ideas.
- kvrm-os/, kvrm-ecosystem/: Experimental neural OS and PCAP anomaly detection threads.

When in doubt, the flagship paper `docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md` and `kvrm-bench/results/publication_bundle/` define the active research claim.

## Every Session — Mandatory Reads

1. `README.md` (architecture + quickstart)
2. `docs/papers/README.md` (paper workflow + guardrails)
3. `docs/KVRM_OVERVIEW.md` (problem framing)
4. `kvrm-bench/results/publication_bundle/publication_summary.md` (live headline claims + evidence links)
5. This `AGENTS.md`

Before major refactors or new domains: re-read `docs/papers/KVRM_PRE_SUBMISSION_CHECKLIST.md`.

## Repository Health Rules

- **Never commit venvs, build artifacts, or large training outputs.** Current .gitignore covers `venv/`, `.venv/`, but history contains bloat (kvrm-ecosystem/venv ~16k files, kvrm-gpu/venv, kvrm-vector, kvrm-llm-compiler training_artifacts, staged_classifier). Future clones should consider shallow + filter if disk is constrained.
- **Publication artifacts are sacred.** Regenerate via `python kvrm-bench/scripts/run_publication_bundle.py` (or the full `run_publication_check.py`). Do not hand-edit generated files under `kvrm-bench/results/publication_bundle/` or the synced copies in `docs/papers/`.
- **Domain boilerplate is technical debt.** Every domain duplicates ~150–200 LOC of `build_*_selector()` wiring. See "Modularization Priorities" below. New domains must not add more duplication.
- **Bench must not depend on demo source layouts forever.** The dynamic import + relative path hack in `kvrm_bench/demo.py` and friends works for research but is packaging poison. Long-term goal: each demo becomes a proper package with entry points or a `kvrm_domain` protocol.
- **Top-level hygiene.** One-off scripts belong in `scripts/`. Large experimental threads that are not active (kvrm-spnc is empty) should be archived or split.

## Domain Addition Checklist

1. Create `kvrm-demos/<kebab-name>/` with:
   - `data/registry.json` (versioned, with support_specs)
   - `data/train_cases.jsonl` + `data/cases.jsonl`
   - `src/<snake_name>/selectors.py` + `executor.py` (implement the 6 build_*_selector functions + build_executor)
   - `pyproject.toml` (optional but recommended)
   - `README.md` (no absolute paths)
2. Register in `kvrm-bench/src/kvrm_bench/demo.py` `DOMAIN_CONFIG` (and any other places that hardcode the set: tests, publication scripts).
3. Add to test bootstrap in `tests/conftest.py` if needed.
4. Run `python kvrm-bench/scripts/run_publication_check.py` and ensure paper_doc_audit still passes.
5. Update `docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md` only via the generated appendix workflow.

## Modularization Priorities (2026-04)

**P0 — Eliminate selector wiring duplication (high impact, medium risk)**
- Introduce in `kvrm-core` (or a new thin `kvrm-domains-kit`) a `build_standard_hybrid_selector(...)` that takes:
  - registry + unsupported_predicate
  - the 4–6 component selectors (or factories)
  - fallback_action_id + name
- Provide a `DomainKit` or protocol so domains only supply feature_order, categorical_values, distance_fn, rule_table, prototype_bank, etc.
- Pilot on 2 domains, then migrate the rest. Target: each domain selectors.py drops from ~250 LOC to <80.

**P1 — Centralize domain loading**
- Single `DomainLoader` / `load_domain_runtime(...)` in `kvrm_bench` that all 8+ modules currently re-implementing `importlib.import_module + _domain_paths` must use.
- Remove repeated config dicts.

**P2 — Publication subpackage**
- Move the 10+ `publication_*.py` + `paper_*.py` modules under `kvrm_bench/publication/` with a clean `__init__.py` re-exporting the CLI entrypoints.
- Keep `kvrm_bench/scripts/run_*.py` as thin wrappers.

**P3 — Packaging**
- Make the 9+ demos proper packages installable via `pip install -e kvrm-demos/sre-policy-router` (they already have pyproject.toml in some cases).
- Make kvrm-bench declare optional dependencies or use importlib.metadata entry points for domain discovery instead of hardcoded strings + PYTHONPATH.

## Testing & Verification Discipline

- Always run `PYTHONPATH=kvrm-core/src:kvrm-bench/src python -m pytest tests/ -q` (or the full harness in `tests/conftest.py`) after structural changes.
- For publication-impacting work, run `python kvrm-bench/scripts/run_publication_check.py` and confirm `all_checks_passed=true`.
- 2026-04 baseline: 231 passed, 1 optional shap failure (missing dep).

## When to Split the Monorepo

Consider extracting when:
- A satellite (llm-compiler, os, ecosystem) grows another 5 GB or requires conflicting deps.
- External collaborators want to use only the decision-routing core.
- You want a clean `kvrm-core` PyPI package without the 12-domain demo data + 7 GB of GPU/LLM artifacts.

Current pragmatic stance: keep together for rapid cross-pollination during active research, but enforce strict "active focus" boundaries in docs and CI.

## Memory & Continuity

- Daily notes live in `memory/YYYY-MM-DD.md` (this project only).
- Major architectural decisions, benchmark surprises, and publication process changes belong in `docs/reports/` or updates to this file.
- The user's global `~/memory/` and `MEMORY.md` capture cross-project context (oNeura, j3sus, etc.).

## Quick Commands

```bash
# Full health gate (recommended before commits touching paper or core)
python kvrm-bench/scripts/run_publication_check.py

# Regenerate everything the paper depends on
python kvrm-bench/scripts/run_publication_bundle.py

# Run TUI (draft review / promotion workflow)
python kvrm_tui.py

# Core + bench tests (minimal)
PYTHONPATH=kvrm-core/src:kvrm-bench/src python -m pytest tests/ -q
```

Update this file when the architecture, packaging story, or scope boundaries change. It is the contract for future agents and humans working in the repo.
