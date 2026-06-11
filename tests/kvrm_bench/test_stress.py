from __future__ import annotations

from pathlib import Path

from kvrm_core.types import ActionSpec, DecisionCandidate, DecisionInput, RegistrySpec
from kvrm_bench.stress import SupportIncompatibleCandidateInjector, run_support_gate_stress

ROOT = Path(__file__).resolve().parents[2]


class StaticSelector:
    def __init__(self, candidates: list[DecisionCandidate]):
        self._candidates = candidates

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        return list(self._candidates)


def test_support_incompatible_candidate_injector_prepends_registry_invalid_candidate():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="safe_action",
                name="Safe Action",
                description="Compatible with safe inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="risky_action",
                name="Risky Action",
                description="Compatible with risky inputs.",
                support_spec={"feature": "kind", "op": "eq", "value": "risky"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Fallback",
                description="Fallback action.",
                tags=["fallback", "safe"],
            ),
        ],
    )
    injector = SupportIncompatibleCandidateInjector(
        wrapped=StaticSelector([DecisionCandidate(action_id="safe_action", confidence=0.81, source="wrapped")]),
        registry=registry,
        confidence=0.999,
        name="stress_injector",
    )

    candidates = injector.select(
        DecisionInput(
            case_id="c1",
            features={"kind": "safe"},
            expected_action_id="safe_action",
        )
    )

    assert candidates[0].action_id == "risky_action"
    assert candidates[0].confidence == 0.999
    assert candidates[0].evidence["stress_injected"] is True
    assert candidates[1].action_id == "safe_action"


def test_support_gate_stress_report_shows_gated_outperforming_ungated(tmp_path):
    payload = run_support_gate_stress(
        repo_root=ROOT,
        domains=["grid"],
        output_dir=tmp_path,
    )

    grid_payload = payload["domains"]["grid"]
    gated_metrics = grid_payload["gated"]["metrics"]
    ungated_metrics = grid_payload["ungated"]["metrics"]
    comparison = grid_payload["comparison"]

    assert gated_metrics["semantic_correctness_rate"] == 1.0
    assert ungated_metrics["semantic_correctness_rate"] < gated_metrics["semantic_correctness_rate"]
    assert gated_metrics["mean_decision_cost"] == 0.0
    assert ungated_metrics["mean_decision_cost"] > gated_metrics["mean_decision_cost"]
    assert gated_metrics["support_gate_trigger_rate"] > 0.5
    assert gated_metrics["supported_support_gate_rescue_rate"] > 0.5
    assert ungated_metrics["support_gate_trigger_rate"] == 0.0
    assert gated_metrics["false_accept_rate"] == 0.0
    assert ungated_metrics["false_accept_rate"] == 0.0
    assert comparison["semantic_correctness_gain"] > 0.5
    assert comparison["mean_decision_cost_reduction"] > 0.1
    assert (tmp_path / "support_gate_stress_report.json").exists()
    assert (tmp_path / "support_gate_stress_report.md").exists()
