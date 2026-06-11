from __future__ import annotations

from pathlib import Path

from finance_risk_router import build_executor
from finance_risk_router import build_hybrid_selector, build_rule_selector
from kvrm_bench.ceiling import load_cases, support_overlap_cases
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.types import DecisionInput, FinalStatus
from kvrm_core.validation import DeterministicValidator

ROOT = Path(__file__).resolve().parents[2] / "finance-risk-router"
REGISTRY_PATH = ROOT / "data" / "registry.json"
TRAIN_CASES_PATH = ROOT / "data" / "train_cases.jsonl"


def test_rule_selector_routes_low_risk_case():
    selector = build_rule_selector()
    result = selector.select(
        DecisionInput(
            case_id="x",
            features={
                "transaction_amount": "low",
                "jurisdiction_risk": "low",
                "anomaly_score": "low",
                "account_history": "clean",
                "kyc_completeness": "complete",
                "velocity_indicator": "normal",
                "sanctions_hit": False,
                "document_mismatch": False,
                "device_trust": "trusted",
            },
        )
    )
    assert result[0].action_id == "approve_low_risk"


def test_hybrid_selector_generalizes_medium_risk_monitoring_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(
        DecisionInput(
            case_id="ood",
            features={
                "transaction_amount": "high",
                "jurisdiction_risk": "low",
                "anomaly_score": "medium",
                "account_history": "clean",
                "kyc_completeness": "complete",
                "velocity_indicator": "elevated",
                "sanctions_hit": False,
                "document_mismatch": False,
                "device_trust": "new",
            },
        )
    )
    assert result[0].action_id == "allow_with_monitoring"


def test_hybrid_selector_routes_missing_kyc_case_to_additional_docs():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(
        DecisionInput(
            case_id="docs",
            features={
                "transaction_amount": "low",
                "jurisdiction_risk": "low",
                "anomaly_score": "medium",
                "account_history": "clean",
                "kyc_completeness": "missing",
                "velocity_indicator": "normal",
                "sanctions_hit": False,
                "document_mismatch": False,
                "device_trust": "trusted",
            },
        )
    )
    assert result[0].action_id == "require_additional_docs"


def test_hybrid_selector_routes_high_risk_kyc_gap_to_compliance():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(
        DecisionInput(
            case_id="compliance",
            features={
                "transaction_amount": "medium",
                "jurisdiction_risk": "high",
                "anomaly_score": "severe",
                "account_history": "clean",
                "kyc_completeness": "missing",
                "velocity_indicator": "normal",
                "sanctions_hit": False,
                "document_mismatch": True,
                "device_trust": "anonymous",
            },
        )
    )
    assert result[0].action_id == "escalate_compliance"


def test_hybrid_selector_routes_ambiguous_high_jurisdiction_case_to_manual_review():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(
        DecisionInput(
            case_id="manual-review-boundary",
            features={
                "transaction_amount": "high",
                "jurisdiction_risk": "high",
                "anomaly_score": "medium",
                "account_history": "watch",
                "kyc_completeness": "complete",
                "velocity_indicator": "normal",
                "sanctions_hit": False,
                "document_mismatch": False,
                "device_trust": "new",
            },
        )
    )
    assert result[0].action_id == "manual_review"


def test_runtime_routes_ambiguous_high_jurisdiction_case_to_manual_review():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(
        registry,
        build_hybrid_selector(TRAIN_CASES_PATH),
        DeterministicValidator(registry),
        build_executor(),
        threshold=0.6,
        fallback_action_id="manual_review",
    )
    result = runtime.decide_and_execute(
        DecisionInput(
            case_id="manual-review-runtime-boundary",
            features={
                "transaction_amount": "high",
                "jurisdiction_risk": "high",
                "anomaly_score": "medium",
                "account_history": "watch",
                "kyc_completeness": "complete",
                "velocity_indicator": "normal",
                "sanctions_hit": False,
                "document_mismatch": False,
                "device_trust": "new",
            },
            expected_action_id="manual_review",
        )
    )

    assert result.selected_action_id == "manual_review"
    assert result.final_status == FinalStatus.FALLBACK_EXECUTED
    assert result.correct is True


def test_runtime_prefers_lower_limit_action_over_fallback_consensus_when_velocity_spikes():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(
        registry,
        build_hybrid_selector(TRAIN_CASES_PATH),
        DeterministicValidator(registry),
        build_executor(),
        threshold=0.6,
        fallback_action_id="manual_review",
    )
    result = runtime.decide_and_execute(
        DecisionInput(
            case_id="velocity-spike-boundary",
            features={
                "transaction_amount": "high",
                "jurisdiction_risk": "high",
                "anomaly_score": "medium",
                "account_history": "watch",
                "kyc_completeness": "complete",
                "velocity_indicator": "high",
                "sanctions_hit": False,
                "document_mismatch": False,
                "device_trust": "new",
            },
            expected_action_id="lower_limit_temporarily",
            supported=True,
            ood=True,
        )
    )

    assert result.selected_action_id == "lower_limit_temporarily"
    assert result.final_status == FinalStatus.EXECUTED
    assert result.correct is True


def test_finance_registry_has_no_supported_overlap_cases():
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
        fallback_action_id="manual_review",
    )
    result = runtime.decide_and_execute(
        DecisionInput(
            case_id="unsupported",
            features={
                "transaction_amount": "mega",
                "jurisdiction_risk": "low",
                "anomaly_score": "low",
                "account_history": "clean",
                "kyc_completeness": "complete",
                "velocity_indicator": "normal",
                "sanctions_hit": False,
                "document_mismatch": False,
                "device_trust": "trusted",
            },
            supported=False,
            ood=True,
        )
    )
    assert result.final_status in {FinalStatus.FALLBACK_EXECUTED, FinalStatus.FAIL_CLOSED}
