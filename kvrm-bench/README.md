# kvrm-bench

kvrm-bench is the shared benchmark harness for KVRM Phase 1.

It provides:
- dataset loading
- metric aggregation
- benchmark execution
- feature-ceiling and overlap analysis
- counterfactual boundary benchmarking
- registry-evolution benchmarking
- replay-style incident-log benchmarking
- reporting and replay
- registry mutation helpers
- standard artifact emission

Artifact tree per run:
- `config.json`
- `registry.json`
- `metrics.json`
- `per_case_results.jsonl`
- `summary.md`

Quickstart:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/examples/toy_benchmark.py
```

Expected toy output:
- `/Users/bobbyprice/projects/KVRM/kvrm-bench/outputs/toy_run/`

How future demos should plug in:
1. define a registry JSON file
2. define a JSONL case file with structured features
3. create a runtime using `kvrm_core`
4. run that runtime through `kvrm_bench.runner.BenchmarkRunner`
5. inspect artifacts and replay results

Phase 1 scope:
- tiny toy benchmark only
- no domain-specific production claims
- shared substrate for later SOC, SRE, drone, grid, finance, medical, and IAM demos

Feature-ceiling analysis:
```bash
python3 /Users/bobbyprice/projects/KVRM/analyze_feature_ceiling.py
```

Counterfactual boundary benchmark:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_counterfactual_boundary_benchmark.py
```

Fallback-feasibility benchmark:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_fallback_feasibility_benchmark.py
```

This benchmark is intentionally narrower than the others: it compares the current strict runtime against
the legacy fallback-support bypass on SRE and drone handoff-feasibility slices, using supported handoff
controls plus schema-valid infeasible-handoff probes derived from the live canonical packs.

Counterfactual packs are cached under `kvrm-bench/results/counterfactual_boundary_case_cache/` and reused until the
live registry or canonical eval pack changes. Force regeneration with:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_counterfactual_boundary_benchmark.py --refresh-cases
```

Ambiguity/regret benchmark:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_ambiguity_regret_benchmark.py
```

Temporal transition benchmark:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_temporal_transition_benchmark.py
```

Coordination chain benchmark:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_coordination_chain_benchmark.py
```

Draft export manifest refresh:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_draft_export_manifest.py
```

This refreshes both:
- `kvrm-bench/results/draft_exports/manifest.json`
- `kvrm-bench/results/draft_exports/manifest.md`

Use it after exporting draft audit packets from the TUI so the review bundle is reproducible from the shell as well as from the operator surface.

Draft export bundle refresh:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_draft_export_bundle.py --domains finance --targets review --sorts queue target --include-groups
```

This walks the requested domain/target/filter/sort combinations, writes deterministic slice packets for every non-empty queue, optionally writes one packet per visible group for grouped sort modes, and then refreshes both manifest files automatically.

Publication bundle refresh:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_publication_bundle.py
```

This stages a curated publication-ready artifact tree under `kvrm-bench/results/publication_bundle/`, copies the current benchmark reports, draft-audit indices, paper/docs artifacts, training reports, and figures into `artifacts/`, and writes:
- `kvrm-bench/results/publication_bundle/manifest.json`
- `kvrm-bench/results/publication_bundle/manifest.md`
- `kvrm-bench/results/publication_bundle/publication_summary.json`
- `kvrm-bench/results/publication_bundle/publication_summary.md`
- `kvrm-bench/results/publication_bundle/paper_assets.json`
- `kvrm-bench/results/publication_bundle/paper_tables.md`
- `kvrm-bench/results/publication_bundle/figure_captions.md`
- `kvrm-bench/results/publication_bundle/paper_appendix.md`
- `kvrm-bench/results/publication_bundle/paper_doc_audit.json`
- `kvrm-bench/results/publication_bundle/paper_doc_audit.md`
- `kvrm-bench/results/publication_bundle/manuscript/manifest.json`
- `kvrm-bench/results/publication_bundle/manuscript/manifest.md`
- `kvrm-bench/results/publication_bundle/manuscript/README.md`
- `kvrm-bench/results/publication_bundle/submission/manifest.json`
- `kvrm-bench/results/publication_bundle/submission/manifest.md`
- `kvrm-bench/results/publication_bundle/submission/README.md`
- `kvrm-bench/results/publication_bundle/submission/review-anonymous/README.md`
- `kvrm-bench/results/publication_bundle/submission/review-anonymous/paper.pdf`
- `kvrm-bench/results/publication_bundle/submission/review-anonymous/submission_bundle.zip`
- `kvrm-bench/results/publication_bundle/submission/working-manuscript/README.md`
- `kvrm-bench/results/publication_bundle/submission/working-manuscript/paper.pdf`
- `kvrm-bench/results/publication_bundle/submission/working-manuscript/submission_bundle.zip`
- `kvrm-bench/results/publication_bundle/publication_check.json`
- `kvrm-bench/results/publication_bundle/publication_check.md`
- `kvrm-bench/results/publication_bundle/README.md`
- `kvrm-bench/results/publication_bundle/publication_portal.json`
- `kvrm-bench/results/publication_bundle/publication_portal.md`

The same bundle refresh also syncs a generated paper-facing snapshot to `docs/papers/KVRM_PUBLICATION_APPENDIX.md` so the manuscript folder has one canonical appendix generated from the live artifact set.
The paper authoring workflow and the generated-vs-hand-edited split are documented in `docs/papers/README.md`.

Paper-doc audit refresh:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_paper_doc_audit.py
```

This writes `paper_doc_audit.json` and `paper_doc_audit.md` under the publication bundle output root without rebuilding the entire bundle.

Publication readiness check:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_publication_check.py
```

This refreshes the publication bundle, reruns the paper-doc audit, runs `pytest tests/kvrm_bench -q`, writes `publication_check.json` and `publication_check.md`, and refreshes the publication portal so the bundle landing page reflects the latest readiness status.

Submission export refresh:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_publication_submission_export.py
```

This rebuilds the `submission/` subdirectory from the manuscript packet, normalizes the exported sources to `paper.md`, `appendix.md`, and `references.bib`, rewrites the markdown into title-aware Pandoc input, strips repo-only workflow sections from the anonymous review paper source, renders both the manuscript and appendix to `tex` and `pdf` via `pandoc` plus `pdflatex`, records PDF metadata in the submission manifest, and writes `submission_bundle.zip` for handoff. Use `--profile review-anonymous` for the default anonymous review packet, `--profile working-manuscript` to keep the full manuscript text while still emitting normalized submission filenames, or `--all-profiles` to mirror the bundle layout with side-by-side `submission/review-anonymous/` and `submission/working-manuscript/` exports.

Registry-evolution benchmark:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_registry_evolution_benchmark.py
```

This benchmark compares the live hybrid runtime against two stale-selector baselines on controlled migration probes:
- renamed live actions whose old ids are now obsolete
- merged predecessor actions that were split into multiple audited live actions
- tightened support envelopes where an old once-plausible action must now fail closed

The current live artifact is `kvrm-bench/results/registry_evolution_report.md`. It shows:
- live hybrid continuity is `1.0` across all seven domains on the supported migration slice
- stale validated baselines stay safe but drop to `0.0` supported continuity
- stale unvalidated baselines execute obsolete actions and tightened-support false accepts in all seven domains

Incident replay benchmark:
```bash
python3 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_incident_replay_benchmark.py
```

This benchmark converts live counterfactual cases into timestamped four-step event-log episodes with baseline,
degradation or switch, unsupported checkpoint, and recovery or stabilization steps, and it now also accepts
explicit authored replay packs validated against the live registries. The current live artifact is
`kvrm-bench/results/incident_replay_report.md`, where hybrid KVRM currently records `wins=3`, `ties=4`,
`losses=0` against the best non-hybrid baseline, with the strongest gains in `drone`, `finance`, and `sre`;
finance, IAM, SRE, and drone now each contribute `4` authored replay episodes, and the report now exposes
per-source replay metrics so authored slices can be audited separately from the counterfactual-derived ones.
