from __future__ import annotations

from pathlib import Path

from kvrm_core.context import feature_key
from kvrm_core.execution import DictionaryExecutor
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.selectors import BaseSelector, ConstantAbstainSelector, EvidenceFusionHybridSelector, RetrievalSelector, RuleSelector
from kvrm_core.types import ActionSpec, DecisionCandidate, DecisionInput, FinalStatus, RegistrySpec
from kvrm_core.validation import DeterministicValidator

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "kvrm-core" / "examples" / "toy_registry.json"


def build_executor():
    return DictionaryExecutor(
        handlers={
            "allow_low_risk": lambda params: {"decision": "allowed"},
            "collect_more_context": lambda params: {"decision": "collect"},
            "block_request": lambda params: {"decision": "blocked"},
            "request_human_review": lambda params: {"decision": "handoff", "reason": params.get("reason")},
        }
    )


class StaticSelector(BaseSelector):
    def __init__(self, candidate: DecisionCandidate):
        self._candidate = candidate

    def select(self, decision_input: DecisionInput):
        return [self._candidate]


def test_rule_selector_returns_known_action():
    registry = load_registry(REGISTRY_PATH)
    key = feature_key({"risk": "low", "anomaly": 0.1})
    selector = RuleSelector(rules={key: ("allow_low_risk", 0.9)})
    result = selector.select(DecisionInput(case_id="x", features={"risk": "low", "anomaly": 0.1}))
    assert result[0].action_id == "allow_low_risk"


def test_retrieval_selector_returns_supported_action():
    key = feature_key({"risk": "high", "anomaly": 0.9})
    selector = RetrievalSelector(support_bank={key: ("block_request", 0.92)})
    result = selector.select(DecisionInput(case_id="x", features={"risk": "high", "anomaly": 0.9}))
    assert result[0].action_id == "block_request"


def test_selector_can_abstain():
    selector = ConstantAbstainSelector(confidence=0.1)
    result = selector.select(DecisionInput(case_id="x", features={}))
    assert result[0].confidence == 0.1


def test_runtime_returns_executed_result_for_valid_high_confidence_case():
    registry = load_registry(REGISTRY_PATH)
    key = feature_key({"risk": "low", "anomaly": 0.1})
    selector = RuleSelector(rules={key: ("allow_low_risk", 0.95)})
    runtime = KVRMRuntime(registry, selector, DeterministicValidator(registry), build_executor(), threshold=0.5)
    result = runtime.decide_and_execute(DecisionInput(case_id="c1", features={"risk": "low", "anomaly": 0.1}, expected_action_id="allow_low_risk"))
    assert result.final_status == FinalStatus.EXECUTED
    assert result.correct is True


def test_runtime_abstains_to_fallback_on_low_confidence_case():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(registry, ConstantAbstainSelector(confidence=0.2), DeterministicValidator(registry), build_executor(), threshold=0.5)
    result = runtime.decide_and_execute(DecisionInput(case_id="c2", features={"risk": "unknown"}))
    assert result.final_status == FinalStatus.FALLBACK_EXECUTED
    assert result.fallback_used is True


def test_runtime_falls_back_when_selector_picks_action_outside_support_envelope():
    registry = load_registry(REGISTRY_PATH)
    key = feature_key({"risk": "high", "anomaly": 0.9})
    selector = RuleSelector(rules={key: ("allow_low_risk", 0.95)})
    runtime = KVRMRuntime(registry, selector, DeterministicValidator(registry), build_executor(), threshold=0.5)
    result = runtime.decide_and_execute(DecisionInput(case_id="c3", features={"risk": "high", "anomaly": 0.9}))
    assert result.final_status == FinalStatus.FALLBACK_EXECUTED
    assert result.selected_action_id == "request_human_review"
    assert result.fallback_used is True


def test_runtime_treats_selected_fallback_tag_action_as_handoff():
    registry = load_registry(REGISTRY_PATH)
    selector = StaticSelector(
        DecisionCandidate(
            action_id="request_human_review",
            confidence=0.95,
            parameters={"reason": "manual_review"},
            source="test_selector",
        )
    )
    runtime = KVRMRuntime(registry, selector, DeterministicValidator(registry), build_executor(), threshold=0.5)
    result = runtime.decide_and_execute(
        DecisionInput(
            case_id="c4",
            features={"risk": "medium", "anomaly": 0.7},
            expected_action_id="request_human_review",
        )
    )
    assert result.final_status == FinalStatus.FALLBACK_EXECUTED
    assert result.execution_result is not None
    assert result.execution_result.status.value == "handoff"
    assert result.correct is True
    assert result.fallback_used is False


def test_runtime_records_fused_selection_evidence():
    registry = load_registry(REGISTRY_PATH)

    class MultiCandidateSelector(BaseSelector):
        def select(self, decision_input: DecisionInput):
            return [
                DecisionCandidate(action_id="allow_low_risk", confidence=0.58, source="hybrid:retrieval"),
                DecisionCandidate(action_id="allow_low_risk", confidence=0.57, source="hybrid:prototype", agreement=1.0, margin=2.0),
                DecisionCandidate(action_id="collect_more_context", confidence=0.61, source="hybrid:semantic"),
            ]

    runtime = KVRMRuntime(registry, MultiCandidateSelector(), DeterministicValidator(registry), build_executor(), threshold=0.6)
    result = runtime.decide_and_execute(DecisionInput(case_id="c5", features={"risk": "low", "anomaly": 0.1}))

    assert result.selected_action_id == "allow_low_risk"
    assert result.audit_record.selected_evidence["fused_source_families"] == ["prototype", "retrieval"]
    assert result.audit_record.selected_evidence["fused_candidate_count"] == 2


def test_runtime_executes_supported_candidate_after_hybrid_support_gate_filters_invalid_candidate():
    registry = load_registry(REGISTRY_PATH)
    selector = EvidenceFusionHybridSelector(
        retrieval_selector=StaticSelector(DecisionCandidate(action_id="block_request", confidence=0.96, source="retrieval")),
        rule_selector=StaticSelector(DecisionCandidate(action_id="collect_more_context", confidence=0.20, source="rule")),
        semantic_selector=StaticSelector(DecisionCandidate(action_id="allow_low_risk", confidence=0.81, source="semantic")),
        prototype_selector=StaticSelector(DecisionCandidate(action_id="allow_low_risk", confidence=0.72, source="prototype")),
        registry=registry,
        fallback_action_id="request_human_review",
        name="fusion_test_selector",
    )

    runtime = KVRMRuntime(registry, selector, DeterministicValidator(registry), build_executor(), threshold=0.6)
    result = runtime.decide_and_execute(
        DecisionInput(
            case_id="c6",
            features={"risk": "low", "anomaly": 0.1},
            expected_action_id="allow_low_risk",
        )
    )

    assert result.final_status == FinalStatus.EXECUTED
    assert result.selected_action_id == "allow_low_risk"
    assert result.fallback_used is False
    assert {row["action_id"] for row in result.audit_record.candidate_scores} == {"allow_low_risk"}
    assert result.audit_record.selected_evidence["support_gate_filtered_count"] == 1
    assert result.audit_record.selected_evidence["support_gate_filtered_actions"] == ["block_request"]


def test_runtime_fail_closes_when_fallback_action_is_outside_support_envelope():
    registry = RegistrySpec(
        registry_name="test-registry",
        version="1.0.0",
        actions=[
            ActionSpec(
                action_id="safe_action",
                name="Safe Action",
                description="Compatible action.",
                support_spec={"feature": "kind", "op": "eq", "value": "safe"},
            ),
            ActionSpec(
                action_id="request_human_review",
                name="Request Human Review",
                description="Fallback action with feasibility constraints.",
                parameters_schema={"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
                support_spec={"feature": "handoff_ready", "op": "eq", "value": True},
                tags=["fallback", "safe"],
            ),
        ],
    )
    runtime = KVRMRuntime(
        registry,
        ConstantAbstainSelector(confidence=0.2),
        DeterministicValidator(registry),
        DictionaryExecutor(handlers={"request_human_review": lambda params: {"decision": "handoff"}}),
        threshold=0.5,
    )
    result = runtime.decide_and_execute(
        DecisionInput(case_id="c7", features={"kind": "unknown", "handoff_ready": False})
    )
    assert result.final_status == FinalStatus.FAIL_CLOSED
    assert result.selected_action_id == "request_human_review"
    assert result.fallback_used is True
