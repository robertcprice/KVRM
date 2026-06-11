from __future__ import annotations

from pathlib import Path

from kvrm_bench.ceiling import load_cases, support_overlap_cases
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.types import DecisionInput, FinalStatus
from kvrm_core.validation import DeterministicValidator
from medical_workflow_router import build_executor
from medical_workflow_router import build_hybrid_selector, build_rule_selector

ROOT = Path(__file__).resolve().parents[2] / "medical-workflow-router"
REGISTRY_PATH = ROOT / "data" / "registry.json"
TRAIN_CASES_PATH = ROOT / "data" / "train_cases.jsonl"


def test_rule_selector_routes_stroke_case():
    selector = build_rule_selector()
    result = selector.select(
        DecisionInput(
            case_id="x",
            features={
                "age_bracket": "older_adult",
                "acuity_score": "critical",
                "fever_bucket": "none",
                "hypotension": False,
                "focal_neuro_deficit": True,
                "chest_pain": False,
                "respiratory_distress": False,
                "infection_risk": "low",
                "symptom_onset": "sudden",
                "clinician_note_flag": "stroke_concern",
            },
        )
    )
    assert result[0].action_id == "stroke_alert_pathway"


def test_hybrid_selector_generalizes_cardiac_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(
        DecisionInput(
            case_id="cardiac",
            features={
                "age_bracket": "older_adult",
                "acuity_score": "critical",
                "fever_bucket": "none",
                "hypotension": False,
                "focal_neuro_deficit": False,
                "chest_pain": True,
                "respiratory_distress": True,
                "infection_risk": "low",
                "symptom_onset": "sudden",
                "clinician_note_flag": "cardiac_concern",
            },
        )
    )
    assert result[0].action_id == "cardiac_chest_pain_pathway"


def test_runtime_prefers_sepsis_pathway_over_supervisor_fallback_when_fever_spikes():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(
        registry,
        build_hybrid_selector(TRAIN_CASES_PATH),
        DeterministicValidator(registry),
        build_executor(),
        threshold=0.6,
        fallback_action_id="escalate_supervisor_review",
    )
    result = runtime.decide_and_execute(
        DecisionInput(
            case_id="counterfactual_sepsis_pathway",
            features={
                "age_bracket": "adult",
                "acuity_score": "critical",
                "fever_bucket": "high",
                "hypotension": True,
                "focal_neuro_deficit": True,
                "chest_pain": True,
                "respiratory_distress": True,
                "infection_risk": "high",
                "symptom_onset": "unclear",
                "clinician_note_flag": "complex",
            },
            supported=True,
            ood=True,
            expected_action_id="sepsis_screen_pathway",
        )
    )

    assert result.selected_action_id == "sepsis_screen_pathway"
    assert result.final_status == FinalStatus.EXECUTED
    assert result.correct is True


def test_medical_registry_has_no_supported_overlap_cases():
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
        fallback_action_id="escalate_supervisor_review",
    )
    result = runtime.decide_and_execute(
        DecisionInput(
            case_id="unsupported",
            features={
                "age_bracket": "ancient",
                "acuity_score": "low",
                "fever_bucket": "none",
                "hypotension": False,
                "focal_neuro_deficit": False,
                "chest_pain": False,
                "respiratory_distress": False,
                "infection_risk": "low",
                "symptom_onset": "progressive",
                "clinician_note_flag": "none",
            },
            supported=False,
            ood=True,
        )
    )
    assert result.final_status in {FinalStatus.FALLBACK_EXECUTED, FinalStatus.FAIL_CLOSED}
