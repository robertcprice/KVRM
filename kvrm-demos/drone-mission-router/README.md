# Drone Mission Router

This demo routes mission-state observations into a finite audited drone policy registry.

Purpose:
- demonstrate KVRM on autonomy-adjacent mission policy selection
- keep outputs bounded to approved policy modes
- avoid pretending to do raw flight control

Registry actions:
- continue_mission
- return_to_home
- hold_position
- switch_to_low_observable_path
- conserve_battery_mode
- climb_for_signal_recovery
- descend_for_safety
- manual_handoff

Data files:
- `data/registry.json`
- `data/train_cases.jsonl`
- `data/cases.jsonl`

Current registry additions:
- route-energy boundary features: `distance_to_home`, `estimated_energy_margin`, `mission_progress`
- recovery-affordance features: `safe_landing_zone_available`, `autonomous_recovery_allowed`, `pilot_takeover_link_quality`
- signal-recovery feasibility features: `altitude_headroom`, `signal_recovery_confidence`, `terrain_occlusion_level`

Current benchmark setup:
- retrieval baseline
- rule baseline
- hybrid selector: retrieval -> high-confidence rule -> compact prototype selector -> abstain/fallback

Current benchmark outcome:
- retrieval reaches `0.2021` semantic correctness
- rule reaches `0.1809` semantic correctness
- hybrid reaches `1.0` semantic correctness on the canonical `135`-case pack
- all three preserve structural validity
- hybrid keeps unsupported-case rejection at `1.0`
- hybrid keeps false-accept at `0.0` and mean decision cost at `0.0`
- the canonical drone support surface now has `0` supported overlap cases
- the compact learned selector now reaches `0.7447` selector-only semantic correctness on the canonical eval pack, while `hybrid_augmented` remains `1.0`

Quickstart:
```bash
PYTHONPATH=/Users/bobbyprice/projects/KVRM/kvrm-core/src:/Users/bobbyprice/projects/KVRM/kvrm-bench/src:/Users/bobbyprice/projects/KVRM/kvrm-demos/drone-mission-router \
/opt/homebrew/bin/python3.14 /Users/bobbyprice/projects/KVRM/kvrm-demos/drone-mission-router/scripts/run_benchmark.py
```

Tests:
```bash
/opt/homebrew/bin/python3.14 -m pytest /Users/bobbyprice/projects/KVRM/kvrm-demos/tests/drone -q
```

Outputs:
- `outputs/drone_mission_router_retrieval/`
- `outputs/drone_mission_router_rule/`
- `outputs/drone_mission_router_hybrid/`
- `../../kvrm-bench/results/drone_compact_training_report_v1.json`

This demo is intentionally policy-level only. It does not control flight surfaces or motors.
