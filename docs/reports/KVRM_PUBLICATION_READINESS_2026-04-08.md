# KVRM Publication Readiness

Date: 2026-04-08
Status: active working memo

## Current Position

KVRM is now in a state where the core architectural claim is honest and defensible:
- registry-constrained finite action routing
- support-envelope gating before calibration, not only validator cleanup after selection
- explicit abstention and fail-closed fallback
- deterministic validation and execution boundaries
- audit records with candidate evidence and fused decision traces
- evidence-fused hybrid selection rather than a demo-specific cascade

The current best benchmark artifacts are:
- `kvrm-demos/reports/demo_comparison.md`
- `baselines/qwen-baseline/outputs/ollama/live_canonical/KVRM_VS_QWEN_OLLAMA_COMPARISON.md`
- `kvrm-bench/results/support_gate_stress_report.md`
- `kvrm-bench/results/fallback_feasibility_report.md`
- `kvrm-bench/results/registry_evolution_report.md`
- `kvrm-bench/results/incident_replay_report.md`
- `kvrm-bench/results/counterfactual_boundary_report.md`
- `kvrm-bench/results/ambiguity_regret_report.md`
- `kvrm-bench/results/temporal_transition_report.md`
- `kvrm-bench/results/coordination_chain_report.md`
- `kvrm-bench/results/feature_ceiling_analysis_cases.md`

## What Is Publication-Ready Now

1. The architectural story
- KVRM is no longer just a thresholded selector stack.
- The core now performs evidence fusion across retrieval, rules, semantic envelopes, and support-aware prototypes.
- The hybrid selector now applies registry-aware support gating before calibration, so unsupported high-confidence candidates are filtered before they can dominate fused scoring.
- The runtime records selected evidence, not just final labels.
- The SRE registry now includes `replica_skew`, `operator_response_eta`, `mitigation_window_remaining`, `quorum_health`, `cross_region_read_staleness`, `control_plane_availability`, and `runbook_coordination_required`; the drone registry now includes explicit route-energy, recovery-affordance, takeover-feasibility, and airspace-governance signals including `pilot_response_eta`, `takeover_window_remaining`, `airspace_deconfliction_status`, `rules_of_engagement_state`, `operator_control_latency_budget`, and `mission_replan_budget`; the grid registry now includes `transfer_path_available`; the new IAM registry adds explicit approval, break-glass, denial, and manual-admin escalation boundaries; and all seven active canonical domains now have zero supported support-spec overlaps.

2. The safety story
- false-accept rate is `0.0` across all seven active canonical demos
- unsupported-case rejection remains `1.0` across all seven active canonical demos
- supported cases can now recover from invalid high-confidence rule or retrieval hits if lower-confidence supported evidence exists downstream
- benchmark artifacts now expose explicit support-gate trigger/short-circuit/rescue rates, so support-envelope behavior is measurable in the publication artifact set
- the published `support_gate_trigger_rate` now excludes legitimate unsupported-context short-circuits, which are tracked separately to keep canonical invalid-candidate trigger rates honest
- the new support-gate stress benchmark makes the architectural claim concrete: with injected `0.999` support-incompatible retrieval/rule candidates, the gated hybrid stays at `semantic_correctness_rate=1.0` and `mean_decision_cost=0.0` across all seven demos while the ungated/post-hoc-validation baseline falls to roughly `0.11-0.23` semantic correctness; IAM joins that suite with gated `1.0` semantic and ungated `0.1111`
- fallback-tagged actions with support envelopes are now validated at runtime as well, so infeasible human escalation no longer bypasses the registry contract through the generic runtime fallback path
- the new fallback-feasibility benchmark isolates that runtime fix directly: on the current SRE (`36` cases) and drone (`62` cases) feasibility-probe slices, strict KVRM keeps `supported_handoff_success_rate=1.0`, `unsupported_unsafe_execution_rate=0.0`, and `mean_feasibility_cost=0.0`, while the legacy bypass baseline hits `unsupported_unsafe_execution_rate=1.0`
- the new registry-evolution benchmark makes the live-registry continuity claim concrete: on controlled rename/split/tightened-support migration probes, live hybrid KVRM keeps `supported_migration_success_rate=1.0`, `tightened_support_safe_rejection_rate=1.0`, and `mean_decision_cost=0.0` across all seven domains; the stale-validated baseline stays safe but loses all supported continuity (`0.0`), while the stale-unvalidated baseline executes obsolete actions and tightened-support false accepts in all seven domains
- the new incident replay benchmark makes the replay-style evaluation claim concrete: on timestamped four-step event logs built from the live counterfactual packs plus explicit authored replay packs in finance, IAM, SRE, and drone, hybrid KVRM has `wins=3`, `ties=4`, `losses=0` against the best non-hybrid baseline, with strict wins in `drone`, `finance`, and `sre`; finance now contributes `4` authored episodes and remains a strict win, IAM contributes `4` authored episodes and remains a clean zero-regret tie, SRE contributes `4` authored episodes and remains a strict win at `0.0` replay regret vs prototype `0.0211`, and drone now contributes `4` authored episodes with both the authored and counterfactual-derived replay slices at `episode_success_rate=1.0`, yielding an overall drone replay score of `1.0` with `0.0` replay regret vs prototype `0.0646`
- the new counterfactual boundary benchmark makes the robustness claim concrete on schema-valid single-feature perturbations: hybrid KVRM now has zero losses across all seven domains on this benchmark family, with strict wins in finance and drone and ties in SOC, SRE, grid, medical, and IAM
- those counterfactual packs are now versioned and cached against the live registry and canonical eval pack, so repeated runs reuse a stable mutation slice instead of silently regenerating drifted artifacts
- the ambiguity/regret frontier benchmark already runs on the live hard-case slice used by the TUI and currently shows zero hybrid regret across the seven canonical domains
- the temporal transition benchmark now converts the cached counterfactual packs into two-step fail-closed, recovery, and action-switch sequences, and hybrid KVRM also has zero losses across all seven domains on this benchmark family, with strict wins in finance, SRE, and drone and ties elsewhere (`wins=3`, `ties=4`, `losses=0`)
- the coordination chain benchmark extends that into deterministic three-step fail-closed, recovery, and action-switch chains, and hybrid KVRM again has zero losses across all seven domains on this benchmark family, with strict wins in finance, SRE, and drone and ties elsewhere (`wins=3`, `ties=4`, `losses=0`)
- a real external small-model comparison now exists across `qwen3:0.6b`, `qwen3:1.7b`, `qwen3.5:0.8b`, and official `gemma4:e2b`: the strongest evaluated external selector, `gemma4:e2b`, reaches macro semantic `0.7406` and macro mean cost `0.5421`, but still fails the paper's open-world requirement with `false_accept_rate=0.9964` and `unsupported_case_rejection_rate=0.0036`; `qwen3:1.7b` still collapses to `invalid_output_rate=1.0`; hybrid KVRM stays perfect on the current six-domain external-comparison subset
- stale-label prevention remains architectural rather than statistical

3. The honesty story
- feature-ceiling analysis now exists and is reproducible
- current hybrid KVRM matches the exact-feature oracle on the active canonical packs
- all seven active canonical packs are now separable with zero supported support-spec overlaps
- the next frontier is no longer generic operator/resource-window or first-order coordination state; it is recovery-planning, write-consistency, and authority-state features on top of the now-live coordination schema, plus longer temporal coordination chains

## What Still Needs Work

1. A prose draft now exists at `docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md`, the live figure/source mapping exists at `docs/papers/KVRM_FIGURE_SOURCE_MAP.md`, a working bibliography exists at `docs/papers/kvrm_refs.bib`, and the current claim-to-artifact backing is summarized in `docs/papers/KVRM_EVIDENCE_MATRIX.md`, but the paper still needs venue-ready citations, polishing, and final figure review.

2. The next architecture/benchmark pass should move beyond the now-live coordination state into deeper recovery-planning and authority-state features, for example:
- `quorum_recovery_eta`
- `write_consistency_requirement`
- `control_plane_rate_limit_state`
- `incident_command_ready`
- `airspace_corridor_stability`
- `jamming_severity`
- `operator_attention_budget`
- `replan_authorization_state`

3. A user-facing operator surface is now available via the TUI:
- `python3 kvrm_tui.py`

The current TUI supports:
- focused-domain test, benchmark, and compact-model training actions
- focused-domain and stale-domain operator refresh pipelines that retrain compact models, rerun domain benchmarks, and refresh the suite comparison artifact in one job
- focused-domain support-gate stress benchmarking
- fallback-feasibility benchmarking for the SRE/drone handoff-feasibility slice
- focused-domain counterfactual boundary and ambiguity/regret benchmarking
- focused-domain temporal transition benchmarking
- focused-domain coordination-chain benchmarking
- cross-domain artifact overview for the selected registry
- per-case audit drilldown with strategy-by-strategy comparison
- compact-model/training audit that checks model/report freshness against the live registry and train/eval packs
- incident replay browsing with episode-level and per-step audit drilldown against the live replay artifact
- prioritized review-queue traversal for disagreement, fallback-path, OOD, and unsupported cases
- draft-case capture into per-domain review/train/eval queues under `data/drafts/`
- draft browsing, label editing, support/OOD toggles, and promotion from draft queues into canonical train/eval packs
- draft filtering so blocked-only, promotable-only, pending-only, reviewed-only, and promoted-only slices can be worked directly from the operator surface
- draft sorting/grouping so repeated diagnostic failures or review-status clusters can be triaged in-place instead of only in raw file order
- draft batch actions now support both visible-slice promotion and current-group promotion, so operators can clear filtered review buckets without scanning the entire draft file
- grouped draft queues now support direct previous/next group navigation from the operator surface
- grouped draft queues now expose per-group audit summaries, so the operator can see status mix and dominant labels for the current cluster without leaving the focused case view
- grouped draft queues now support review-state edits at group scope while explicitly skipping already promoted drafts
- grouped draft queues now support focused-draft flag propagation (`supported` / `ood`) at group scope, again with promoted-draft skipping
- visible filtered draft slices now support review-state edits with the same conservative promoted-draft skipping rule
- visible filtered draft slices now also support focused-draft flag propagation (`supported` / `ood`) with the same promoted-draft skipping rule
- the operator surface now exports deterministic draft-audit packets for the current visible slice or group under `kvrm-bench/results/draft_exports/<domain>/<target>/`, which makes review artifacts reproducible and citable instead of ad hoc
- the same export surface now writes a suite-level manifest at `kvrm-bench/results/draft_exports/manifest.json`, so those packets can be bundled into a reproducible review set instead of tracked manually
- the manifest refresh also writes `kvrm-bench/results/draft_exports/manifest.md`, giving the paper/demo workflow a human-readable audit index instead of forcing reviewers to inspect the JSON manifest directly
- there is now a shellable bundle path at `kvrm-bench/scripts/run_draft_export_bundle.py`, so publication bundles can be regenerated across selected domains/targets without driving the curses operator manually
- there is now also a curated publication-artifact packager at `kvrm-bench/scripts/run_publication_bundle.py`, which stages the current benchmark/evidence/docs figure set into `kvrm-bench/results/publication_bundle/` with deterministic manifests
- the publication bundle script now also generates `publication_summary.json` and `publication_summary.md` from the live artifact set, so paper-facing headline claims are derived from source artifacts instead of being maintained only as hand-edited prose
- the same publication bundle script now emits `paper_tables.md` and `figure_captions.md` from the generated summary, which gives the manuscript workflow stable table/caption text anchored in the live artifact set
- the publication bundle script now also emits `paper_appendix.md` and syncs `docs/papers/KVRM_PUBLICATION_APPENDIX.md`, so the paper folder has a single generated appendix snapshot instead of relying on scattered hand-maintained references
- the publication bundle script now also emits `paper_doc_audit.json` and `paper_doc_audit.md`, which records whether the draft/scaffold/evidence docs are still aligned to the appendix-backed workflow
- the publication bundle script now also emits `publication_portal.json` and `publication_portal.md`, which turn the bundle root into a self-describing landing page for the manifest, summary, appendix, and paper-doc audit
- the same publication portal now also lands at `kvrm-bench/results/publication_bundle/README.md`, so opening the bundle root immediately shows the current publication-facing status and file map
- the publication bundle script now also stages a dedicated manuscript packet under `kvrm-bench/results/publication_bundle/manuscript/`, so the draft, appendix, bibliography, and paper-facing generated outputs can be handed off without traversing the full evidence tree
- there is now also a direct submission export at `kvrm-bench/results/publication_bundle/submission/`, rendered from the manuscript packet via `pandoc` and `pdflatex`, so the repo emits normalized `paper.*` and `appendix.*` submission artifacts instead of only working-manuscript filenames
- the submission export now also records PDF metadata in its manifest and writes `submission_bundle.zip`, which gives the publication workflow a single handoff artifact instead of only a directory tree
- the paper workflow entrypoint is now `docs/papers/README.md`, which documents which paper docs are hand-edited and which are generated from the bundle
- there is now also a direct paper-doc audit script at `kvrm-bench/scripts/run_paper_doc_audit.py`, so manuscript-alignment checks can be regenerated without rebuilding the full publication bundle
- there is now also a direct submission-export script at `kvrm-bench/scripts/run_publication_submission_export.py`, so the venue-export step can be rerun without re-driving the full benchmark pipeline manually
- there is now also a single publication-readiness script at `kvrm-bench/scripts/run_publication_check.py`, which refreshes the bundle, reruns the paper-doc audit, runs the `tests/kvrm_bench` suite, writes `publication_check.json` / `publication_check.md`, and refreshes the portal with the latest check status
- draft-queue summaries plus batch promotion of all ready drafts in the focused queue
- normalized draft diagnostics that translate schema/support failures into operator-readable fix hints
- promotion-readiness validation that checks registry schema conformance, expected-action validity, and support compatibility before review drafts can enter train/eval
- task-output monitoring and cache refresh after retraining

## Recommended Next Sequence

1. Turn the current prose draft into venue-ready copy with citations, captioned figures, and venue formatting.
2. Add a true shadow or historical replay slice in at least one domain so the story moves beyond canonical-plus-derived replay plus the current authored finance/IAM/SRE event logs.
3. Extend the new coordination-chain family beyond deterministic three-step chains into longer sequences with explicit quorum, airspace-governance, and operator-latency state.
4. Extend the TUI from single-case draft review into bulk case editing, schema-debugging, and promotion workflows.
5. Extend the external baseline comparison or add a true historical/shadow replay slice so the paper is stronger on external comparison and real-world replay evidence, not only on synthetic breadth.
