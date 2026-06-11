# KVRM Demo Suite

Active robust demos built on `kvrm-core` and `kvrm-bench`.

Current demos:
- `soc-playbook-router/` - security incident response playbook routing
- `sre-policy-router/` - service remediation policy routing
- `drone-mission-router/` - mission-policy routing for autonomous aerial systems
- `grid-ops-router/` - bounded grid-operations workflow routing for power-system incident handling
- `finance-risk-router/` - audited financial risk workflow routing
- `medical-workflow-router/` - bounded clinical workflow routing with explicit safe escalation
- `iam-access-router/` - bounded IAM and privileged-access workflow routing with explicit break-glass, denial, and manual-admin escalation paths

Shared design goals:
- finite audited action registries
- deterministic execution or safe handoff
- abstention/fallback behavior
- benchmark artifacts
- supported vs unsupported evaluation
- OOD evaluation
- adversarial/unsupported scenario coverage

Repository layout:
- `<domain>/data/` holds the canonical registry plus train and eval case packs
- `<domain>/data/drafts/` is created on first TUI draft save and holds pending review/train/eval candidate cases
- `<domain>/src/` holds the selector and executor implementation for that domain
- `<domain>/scripts/` holds benchmark entrypoints
- `<domain>/outputs/` holds per-demo benchmark artifacts
- `tests/<domain>/` under `kvrm-demos/` holds the domain-specific regression suite
- `reports/` holds generated cross-demo comparisons

The generated demo comparison report is the source of truth for the current canonical demo pack:
- `kvrm-demos/reports/demo_comparison.md`
- `kvrm-demos/reports/demo_comparison.json`

The generated support-gate stress report is the source of truth for the architecture-resilience claim:
- `kvrm-bench/results/support_gate_stress_report.md`
- `kvrm-bench/results/support_gate_stress_report.json`

The generated fallback-feasibility report is the source of truth for the strict runtime handoff-feasibility claim:
- `kvrm-bench/results/fallback_feasibility_report.md`
- `kvrm-bench/results/fallback_feasibility_report.json`
- `kvrm-bench/results/fallback_feasibility_cases.json`

The generated registry-evolution report is the source of truth for the live-registry continuity claim:
- `kvrm-bench/results/registry_evolution_report.md`
- `kvrm-bench/results/registry_evolution_report.json`
- `kvrm-bench/results/registry_evolution_cases.json`

The generated incident replay report is the source of truth for the short-horizon event-log replay claim:
- `kvrm-bench/results/incident_replay_report.md`
- `kvrm-bench/results/incident_replay_report.json`
- `kvrm-bench/results/incident_replay_episodes.json`
These artifacts now mix counterfactual-derived episodes with explicit authored replay packs in finance, IAM, SRE, and drone.
They now also expose per-source hybrid replay metrics so authored and counterfactual-derived slices can be audited separately in the same artifact.

The generated counterfactual boundary report is the source of truth for the single-step robustness claim:
- `kvrm-bench/results/counterfactual_boundary_report.md`
- `kvrm-bench/results/counterfactual_boundary_report.json`
- `kvrm-bench/results/counterfactual_boundary_cases.json`

The generated ambiguity/regret report is the source of truth for the hard-case frontier slice already present in the canonical packs:
- `kvrm-bench/results/ambiguity_regret_report.md`
- `kvrm-bench/results/ambiguity_regret_report.json`

The generated temporal transition report is the source of truth for two-step recovery and fail-closed transition behavior:
- `kvrm-bench/results/temporal_transition_report.md`
- `kvrm-bench/results/temporal_transition_report.json`
- `kvrm-bench/results/temporal_transition_sequences.json`

The generated coordination chain report is the source of truth for longer three-step fail-closed, recovery, and action-switch chains:
- `kvrm-bench/results/coordination_chain_report.md`
- `kvrm-bench/results/coordination_chain_report.json`
- `kvrm-bench/results/coordination_chain_sequences.json`

Interpretation:
- the suite now spans seven bounded workflow domains instead of a single narrow benchmark family
- each active demo domain now exposes one canonical dataset at `data/cases.jsonl`
- all seven active demo registries now declare `required_features` and `context_schema`, so support gating is anchored in the registry instead of only in handwritten selector predicates
- the new IAM registry adds a distinct identity-operations use case with bounded approval, security-review, break-glass, denial, and manual-admin escalation actions; the live canonical IAM pack is `24` cases (`18` supported, `6` unsupported) and the hybrid runtime is at `semantic_correctness_rate=1.0`, `false_accept_rate=0.0`, `unsupported_case_rejection_rate=1.0`, and `mean_decision_cost=0.0`
- the SRE registry is now at `1.5.0` and adds explicit coordination-state features (`quorum_health`, `cross_region_read_staleness`, `control_plane_availability`, `runbook_coordination_required`) on top of the earlier locality and handoff-feasibility expansions, so failover, readonly, and human-page boundaries are now audited against live coordination state instead of being inferred
- the drone registry is now at `1.4.0` and adds explicit airspace-governance and command-budget state (`airspace_deconfliction_status`, `rules_of_engagement_state`, `operator_control_latency_budget`, `mission_replan_budget`) on top of the route-energy, landing-safety, signal-recovery, and takeover-feasibility features already present in `1.3.0`
- the grid registry is now at `1.1.0` and adds `transfer_path_available` as an audited topology-capability feature, which removes the prior `isolate_faulted_feeder` vs `transfer_load` / `dispatch_field_crew` overlap without turning valid transfer cases into unsupported fallbacks
- the finance and medical registries are now at `1.2.0` and tighten their support specs around previously ambiguous review/escalation boundaries
- the hybrid selector now also enforces support-envelope gating before evidence fusion calibration, so unsupported high-confidence candidates are filtered before they can win the fused score
- fallback-tagged actions with support specs are now validated against live features at runtime too, so infeasible human handoffs fail closed instead of bypassing the registry contract through the generic runtime fallback path
- the registry-evolution benchmark now makes the live-registry contract story concrete: across all seven domains, live hybrid KVRM preserves `supported_migration_success_rate=1.0` on controlled rename/split migration probes, the stale-validated baseline preserves safety but drops to `0.0` continuity, and the stale-unvalidated baseline executes obsolete or newly unsupported actions in every domain
- the new incident replay benchmark now packages live counterfactual cases plus explicit authored finance/IAM/SRE/drone replay packs into timestamped four-step event logs; hybrid currently has `wins=3`, `ties=4`, `losses=0` against the best non-hybrid baseline, with the strongest replay gains in `drone`, `finance`, and `sre`; finance now includes `4` authored episodes and remains a strict hybrid win, IAM contributes `4` authored episodes and remains a clean tie at zero regret, SRE now contributes `4` authored episodes and remains a strict hybrid win, and drone now contributes `4` authored episodes with both the authored slice and the counterfactual-derived slice at `episode_success_rate=1.0` and `mean_episode_regret=0.0`
- the new fallback-feasibility benchmark makes that runtime claim concrete on the two domains that now model explicit handoff feasibility; strict KVRM stays at `unsupported_unsafe_execution_rate=0.0` while the legacy bypass baseline is at `1.0` on both the SRE (`36` cases) and drone (`62` cases) probe slices
- hybrid benchmark artifacts now expose `support_gate_trigger_rate`, `supported_support_gate_rescue_rate`, `unsupported_support_gate_short_circuit_rate`, and `support_gate_exhausted_rate` so support gating can be measured instead of only described
- `support_gate_trigger_rate` counts invalid-candidate filtering/exhaustion events; globally unsupported contexts are reported separately via `unsupported_support_gate_short_circuit_rate`
- the support-gate stress benchmark injects high-confidence support-incompatible candidates into retrieval and rule stages; the gated hybrid preserves `semantic_correctness_rate=1.0` and `mean_decision_cost=0.0` across all seven demos while the ungated/post-hoc-validation baseline collapses to about `0.10-0.23` semantic correctness with non-zero cost; IAM joins that suite with gated `1.0` semantic vs ungated `0.1111`
- the counterfactual boundary benchmark mutates one schema-valid feature at a time from supported canonical cases, keeps only registry-resolved single-action or safe-reject transitions, and still shows hybrid KVRM with zero losses across all seven domains on this benchmark family (`wins=2`, `ties=5`, `losses=0`); finance and drone are strict wins, while SOC, SRE, grid, medical, and IAM tie their best non-hybrid baseline
- those counterfactual packs are now versioned and cached under `kvrm-bench/results/counterfactual_boundary_case_cache/`, so reruns only regenerate when the live registry or canonical eval pack changes, or when the case-pack version is bumped
- the ambiguity/regret benchmark slices the live review frontier already used by the TUI and currently shows zero hybrid regret across the seven canonical domains
- the temporal transition benchmark lifts the cached counterfactual packs into two-step sequences for supported action switches, supported-to-unsupported fail-closed transitions, and unsupported-to-supported recovery transitions, and now shows hybrid KVRM with zero losses across all seven domains on this benchmark family (`wins=3`, `ties=4`, `losses=0`)
- the coordination chain benchmark composes those cached counterfactual packs into deterministic three-step sequences and also shows hybrid KVRM with zero losses across all seven domains on this benchmark family (`wins=3`, `ties=4`, `losses=0`)
- the canonical SOC pack includes `126` cases, the canonical SRE pack includes `140` cases (`94` supported, `46` unsupported), and the canonical Drone pack now includes `146` cases (`98` supported, `48` unsupported) after the coordination-state expansion
- all seven active canonical registries now have zero supported support-spec overlap cases on their live canonical packs
- the next SRE frontier is no longer generic severity tuning or first-order coordination gating; the live ceiling report now points to `quorum_recovery_eta`, `write_consistency_requirement`, `control_plane_rate_limit_state`, and `incident_command_ready`
- the next drone frontier is no longer first-order action overlap or basic airspace governance; the live ceiling report now points to `airspace_corridor_stability`, `jamming_severity`, `operator_attention_budget`, and `replan_authorization_state`
- older numbered datasets and benchmark artifacts are archived under `data/legacy/` and `kvrm-bench/results/legacy/` for provenance only
- the benchmark layer now also reports `mean_decision_cost`, which penalizes supported-case abstention less than misroutes and penalizes unsupported false accepts most heavily
- this makes it easier to compare conservative vs aggressive selectors without pretending all errors have equal deployment cost

Run demo benchmarks:
- SOC:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/soc-playbook-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/soc-playbook-router/scripts/run_benchmark.py
```
- SRE:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/sre-policy-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/sre-policy-router/scripts/run_benchmark.py
```
- Drone:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/drone-mission-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/drone-mission-router/scripts/run_benchmark.py
```
- Grid:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/grid-ops-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/grid-ops-router/scripts/run_benchmark.py
```

Or use the launcher:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/run_demo.py soc
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/run_demo.py sre
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/run_demo.py drone
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/run_demo.py grid
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/run_demo.py finance
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/run_demo.py medical
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/run_demo.py iam
```

Generate the consolidated comparison report:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/compare_demos.py
```

Generate the support-gate stress report:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_support_gate_stress.py
```

Generate the fallback-feasibility report:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_fallback_feasibility_benchmark.py
```

Generate the registry-evolution report:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_registry_evolution_benchmark.py
```

Generate the incident replay report:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_incident_replay_benchmark.py
```

Generate the counterfactual boundary report:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_counterfactual_boundary_benchmark.py
```

Force a full counterfactual pack refresh:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_counterfactual_boundary_benchmark.py --refresh-cases
```

Generate the ambiguity/regret report:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_ambiguity_regret_benchmark.py
```

Generate the temporal transition report:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_temporal_transition_benchmark.py
```

Generate the coordination chain report:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-bench/scripts/run_coordination_chain_benchmark.py
```

Operator TUI:
```bash
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm_tui.py
```

TUI workflow:
- focus a domain with `h/l` or left/right
- run the focused domain test, benchmark, or training job from the left action panel
- run the focused domain's support-gate stress benchmark from the left action panel
- run the fallback-feasibility benchmark from the left action panel; on non-SRE/non-drone tabs it defaults to the paired SRE+drone slice
- run the focused domain's counterfactual boundary benchmark from the left action panel
- run the focused domain's ambiguity/regret frontier benchmark from the left action panel
- run the focused domain's temporal transition benchmark from the left action panel
- run the focused domain's coordination chain benchmark from the left action panel
- run the focused domain's registry-evolution benchmark from the left action panel
- run the focused domain's incident replay benchmark from the left action panel
- run the focused domain refresh pipeline from the left action panel to retrain, rerun the domain benchmark, and refresh the suite comparison in one job
- run the stale-domain refresh pipeline from the left action panel to rebuild only domains whose compact-model artifacts are missing or stale
- toggle interactive audit with `d`
- toggle prioritized boundary review with `v`
- toggle editable draft browsing with `g`
- toggle incident replay browsing with `i`
- toggle compact-model/training audit with `x`
- inspect the current case across `rule`, `retrieval`, `prototype`, `semantic`, `learned`, and `hybrid` selectors in one pane
- in replay mode, browse timestamped incident episodes with up/down and inspect per-step decisions with `[` / `]`
- in training mode, inspect compact-model freshness, report freshness, registry-digest alignment, and selector-only vs hybrid-augmented metrics before or after running task `a` or `b`
- save the current case into `data/drafts/` with `w` (review), `t` (train candidate), or `y` (eval candidate)
- in draft mode, the audit pane now shows train/eval readiness, registry-schema validation, and expected-action support status for the selected draft
- in draft mode, use `n` to switch draft queues, `F` to cycle filtered queue views (`all`, `pending`, `reviewed`, `promotable`, `blocked`, `promoted`), `s` to cycle queue sort/grouping (`queue`, `diagnostic`, `status`, `target`), `{` / `}` to jump between visible groups, `[` / `]` to change the expected action label, `u` to toggle supported, `o` to toggle OOD, `R` / `P` to mark the current visible group reviewed or pending, `U` / `O` to apply the focused draft's `supported` / `ood` value across the current visible group, `V` / `B` to mark the current visible queue slice reviewed or pending, `S` / `D` to apply the focused draft's `supported` / `ood` value across the current visible queue slice, `m` to promote the current draft, `M` to batch-promote all ready drafts in the current visible queue slice, and `G` to batch-promote all ready drafts in the current visible group
- the draft browser now exposes queue-level counts for pending, reviewed, promoted, blocked, and promotable drafts so bulk curation can be audited before promotion
- blocked drafts now show normalized schema/action diagnostics and fix hints instead of raw `context:...` or `unsupported_features:...` reason strings
- filtered draft browsing preserves the original draft index internally, so edits and promotions still target the correct JSONL row even when the visible queue is a blocked-only or promotable-only slice
- sorted draft browsing now exposes group labels and group counts, so operators can clear repeated blocked reasons or review-status clusters as a batch instead of hunting through flat queue order
- grouped draft queues now also expose per-group summaries in the right pane, including status mix, target mix, dominant labels, and diagnostic-feature counts where relevant
- grouped review-state edits skip already promoted drafts so operator convenience actions do not rewrite promotion provenance
- grouped flag propagation also skips already promoted drafts and copies the focused draft's current boolean value across the visible group
- visible-slice review-state edits use the same conservative rule and also skip already promoted drafts
- visible-slice flag propagation follows the same rule and copies the focused draft's current boolean value across the filtered queue while skipping promoted drafts
- `E` exports the current visible slice, `H` exports the current visible group, and `J` refreshes the suite manifest for those packets under `kvrm-bench/results/draft_exports/`
- the same manifest refresh now also writes a human-readable markdown index at `kvrm-bench/results/draft_exports/manifest.md`, so audit packets can be cited or handed off without inspecting raw JSON
- for shell-driven publication bundles, `kvrm-bench/scripts/run_draft_export_bundle.py` now exports deterministic slice/group packets across selected domains/targets and refreshes the manifest in one step
- `kvrm-bench/scripts/run_publication_bundle.py` now stages the benchmark reports, draft-audit outputs, paper docs, training reports, and figures into `kvrm-bench/results/publication_bundle/` with manifest json/markdown indices, a generated publication summary pair, and generated paper tables / figure captions derived from the live summary
- review-queue drafts auto-route to `train` or `eval` only when the case is promotion-ready; invalid schema or unsupported labels stay blocked instead of silently polluting the canonical packs
- use `r` to refresh artifacts and clear cached runtimes after retraining

Report outputs:
- `kvrm-demos/reports/demo_comparison.json`
- `kvrm-demos/reports/demo_comparison.md`
- draft audit packets under `kvrm-bench/results/draft_exports/<domain>/<target>/`
- draft export manifest at `kvrm-bench/results/draft_exports/manifest.json`
- draft export markdown index at `kvrm-bench/results/draft_exports/manifest.md`
- publication bundle manifests at `kvrm-bench/results/publication_bundle/{manifest.json,manifest.md}`
- publication bundle summary at `kvrm-bench/results/publication_bundle/{publication_summary.json,publication_summary.md}`
- generated paper assets at `kvrm-bench/results/publication_bundle/{README.md,paper_assets.json,paper_tables.md,figure_captions.md,paper_appendix.md,paper_doc_audit.json,paper_doc_audit.md,publication_check.json,publication_check.md,publication_portal.json,publication_portal.md}` plus `kvrm-bench/results/publication_bundle/manuscript/{README.md,manifest.json,manifest.md}` and `kvrm-bench/results/publication_bundle/submission/{README.md,manifest.json,manifest.md,paper.md,paper.tex,paper.pdf,appendix.md,appendix.tex,appendix.pdf,references.bib,submission_bundle.zip}`
- synced paper appendix at `docs/papers/KVRM_PUBLICATION_APPENDIX.md`
- paper authoring workflow at `docs/papers/README.md`
- per-run metrics under `kvrm-demos/*/outputs/*/metrics.json`

This suite is now strong enough to demonstrate the KVRM architecture pattern across multiple critical-infrastructure-adjacent domains without pretending to do unconstrained autonomous control.
