"""KVRM in five minutes.

Routes two inputs through a real domain (power-grid operations) and shows the
two behaviors that define KVRM:

  1. A supported input selects a registered action, passes validation, and
     executes — with a full audit record.
  2. An input outside every action's support envelope is NOT guessed at.
     The runtime fails closed: it either abstains or hands off to the
     domain's designated fallback action, and the audit record says why.

Run from a repo checkout (after `pip install -e kvrm-core/ -e kvrm-bench/`
plus the demo packages — see README Quick Start):

    python examples/quickstart.py
"""

from __future__ import annotations

import json
from pathlib import Path

from kvrm_core import DecisionInput, load_registry
from kvrm_bench.demo import _cached_runtime_for_strategy

REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAIN = "grid"


def show(title: str, decision) -> None:
    payload = json.loads(decision.model_dump_json())
    print(f"\n=== {title} ===")
    print(f"  selected action : {payload['selected_action_id']}")
    print(f"  final status    : {payload['final_status']}")
    print(f"  fallback used   : {payload['fallback_used']}")
    if payload.get("validation_reason"):
        print(f"  reason          : {payload['validation_reason']}")
    audit = payload["audit_record"]
    print(f"  registry digest : {audit['registry_digest'][:16]}…")
    print(f"  candidates      : "
          + ", ".join(f"{c['action_id']}={c['confidence']:.2f}"
                      for c in audit["candidate_scores"][:3]))


def main() -> None:
    # Every decision is constrained to a versioned, hashed action registry.
    registry = load_registry(
        REPO_ROOT / "kvrm-demos" / "grid-ops-router" / "data" / "registry.json"
    )
    print(f"registry: {registry.registry_name} v{registry.version}, "
          f"{len(registry.actions)} actions")
    for action in registry.actions:
        print(f"  - {action.action_id}")

    # The runtime wires selector ensemble -> support gate -> validator -> executor.
    runtime, _ = _cached_runtime_for_strategy(
        str(REPO_ROOT), DOMAIN, "cases.jsonl", "hybrid", None, 0.60
    )

    # 1) A healthy circuit under observation: squarely inside the support
    #    envelope of `continue_monitoring`.
    supported = DecisionInput(
        case_id="quickstart_supported",
        features={
            "outage_scope": "none", "relay_state": "normal",
            "customer_impact": "low", "reserve_margin": "adequate",
            "frequency_deviation": "normal", "voltage_stability": "stable",
            "crew_availability": "available", "weather_risk": "low",
            "fault_isolation_ready": False, "switching_authorized": True,
            "transfer_path_available": False, "blackstart_required": False,
        },
    )
    show("supported input -> executes", runtime.decide_and_execute(supported))

    # 2) A regional blackout with no authorization, no crew, no transfer path:
    #    no registered action's support spec covers this state. A plain
    #    classifier would still emit its nearest label. KVRM refuses and
    #    routes to the audited fallback instead.
    unsupported = DecisionInput(
        case_id="quickstart_unsupported",
        features={
            "outage_scope": "regional", "relay_state": "reclose_lockout",
            "customer_impact": "critical", "reserve_margin": "low",
            "frequency_deviation": "severe", "voltage_stability": "unstable",
            "crew_availability": "limited", "weather_risk": "severe",
            "fault_isolation_ready": False, "switching_authorized": False,
            "transfer_path_available": False, "blackstart_required": False,
        },
    )
    show("unsupported input -> fails closed", runtime.decide_and_execute(unsupported))

    print(
        "\nThat is the whole idea: actions come only from the registry,"
        "\nunsupported states are rejected rather than approximated, and"
        "\nevery decision carries a deterministic audit trail."
        "\n\nNext steps:"
        "\n  kvrm domains                    # the same pipeline, from the CLI"
        "\n  kvrm case sre -i 3 --matrix     # compare selector strategies"
        "\n  README 'Adding a New Domain'    # build your own registry"
    )


if __name__ == "__main__":
    main()
