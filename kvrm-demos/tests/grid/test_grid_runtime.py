from __future__ import annotations

from pathlib import Path

from grid_ops_router import build_executor
from grid_ops_router import build_hybrid_selector, build_rule_selector
from kvrm_bench.ceiling import load_cases, support_overlap_cases
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.types import DecisionInput, FinalStatus
from kvrm_core.validation import DeterministicValidator

ROOT = Path(__file__).resolve().parents[2] / "grid-ops-router"
REGISTRY_PATH = ROOT / "data" / "registry.json"
TRAIN_CASES_PATH = ROOT / "data" / "train_cases.jsonl"


def test_rule_selector_routes_fault_isolation_case():
    selector = build_rule_selector()
    result = selector.select(
        DecisionInput(
            case_id="x",
            features={
                "outage_scope": "feeder",
                "relay_state": "tripped",
                "customer_impact": "high",
                "reserve_margin": "adequate",
                "frequency_deviation": "mild",
                "voltage_stability": "degraded",
                "crew_availability": "available",
                "weather_risk": "low",
                "fault_isolation_ready": True,
                "switching_authorized": True,
                "transfer_path_available": False,
                "blackstart_required": False,
            },
        )
    )
    assert result[0].action_id == "isolate_faulted_feeder"


def test_hybrid_selector_generalizes_blackstart_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(
        DecisionInput(
            case_id="blackstart",
            features={
                "outage_scope": "regional",
                "relay_state": "normal",
                "customer_impact": "critical",
                "reserve_margin": "low",
                "frequency_deviation": "severe",
                "voltage_stability": "unstable",
                "crew_availability": "available",
                "weather_risk": "low",
                "fault_isolation_ready": False,
                "switching_authorized": True,
                "transfer_path_available": False,
                "blackstart_required": True,
            },
        )
    )
    assert result[0].action_id == "prepare_blackstart"


def test_hybrid_selector_routes_transfer_when_path_is_available():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(
        DecisionInput(
            case_id="transfer-load",
            features={
                "outage_scope": "substation",
                "relay_state": "tripped",
                "customer_impact": "critical",
                "reserve_margin": "high",
                "frequency_deviation": "mild",
                "voltage_stability": "degraded",
                "crew_availability": "available",
                "weather_risk": "elevated",
                "fault_isolation_ready": True,
                "switching_authorized": True,
                "transfer_path_available": True,
                "blackstart_required": False,
            },
        )
    )
    assert result[0].action_id == "transfer_load"


def test_grid_registry_has_no_supported_overlap_cases():
    registry = load_registry(REGISTRY_PATH)
    cases = load_cases(ROOT / "data" / "cases.jsonl")
    assert support_overlap_cases(registry, cases, supported_only=True) == []


def test_runtime_falls_back_for_unsupported_case():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(
        registry,
        build_rule_selector(),
        DeterministicValidator(registry),
        build_executor(),
        threshold=0.8,
        fallback_action_id="escalate_grid_supervisor",
    )
    result = runtime.decide_and_execute(
        DecisionInput(
            case_id="unsupported",
            features={
                "outage_scope": "microgrid",
                "relay_state": "tripped",
                "customer_impact": "high",
                "reserve_margin": "adequate",
                "frequency_deviation": "mild",
                "voltage_stability": "degraded",
                "crew_availability": "available",
                "weather_risk": "low",
                "fault_isolation_ready": True,
                "switching_authorized": True,
                "transfer_path_available": False,
                "blackstart_required": False,
            },
            supported=False,
            ood=True,
        )
    )
    assert result.final_status in {FinalStatus.FALLBACK_EXECUTED, FinalStatus.FAIL_CLOSED}
