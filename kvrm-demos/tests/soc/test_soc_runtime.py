from __future__ import annotations

from pathlib import Path

from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.types import DecisionInput, FinalStatus
from kvrm_core.validation import DeterministicValidator
from soc_playbook_router import build_executor
from soc_playbook_router import build_retrieval_selector, build_rule_selector, build_prototype_selector, build_hybrid_selector

ROOT = Path(__file__).resolve().parents[2] / 'soc-playbook-router'
REGISTRY_PATH = ROOT / 'data' / 'registry.json'
TRAIN_CASES_PATH = ROOT / 'data' / 'train_cases.jsonl'
CASES_PATH = ROOT / 'data' / 'cases.jsonl'


def test_rule_selector_routes_high_severity_host_case():
    selector = build_rule_selector()
    result = selector.select(DecisionInput(case_id='x', features={
        'severity': 'high',
        'threat_confidence': 'high',
        'asset_criticality': 'tier2',
        'lateral_movement': False,
        'blast_radius': 'contained',
        'internet_exposed': True,
        'credential_exposure': False,
        'endpoint_type': 'host',
    }))
    assert result[0].action_id == 'isolate_host'


def test_runtime_falls_back_for_unsupported_case():
    registry = load_registry(REGISTRY_PATH)
    selector = build_rule_selector()
    runtime = KVRMRuntime(registry, selector, DeterministicValidator(registry), build_executor(), threshold=0.8, fallback_action_id='request_human_triage')
    result = runtime.decide_and_execute(DecisionInput(case_id='unsupported', features={
        'severity': 'critical',
        'threat_confidence': 'unknown',
        'asset_criticality': 'tier1',
        'lateral_movement': True,
        'blast_radius': 'wide',
        'internet_exposed': False,
        'credential_exposure': False,
        'endpoint_type': 'saas',
    }, supported=False, ood=True))
    assert result.final_status in {FinalStatus.FALLBACK_EXECUTED, FinalStatus.FAIL_CLOSED}


def test_retrieval_selector_supports_known_case():
    selector = build_retrieval_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='soc_001', features={
        'severity': 'critical',
        'threat_confidence': 'high',
        'asset_criticality': 'tier1',
        'lateral_movement': True,
        'blast_radius': 'wide',
        'internet_exposed': True,
        'credential_exposure': True,
        'endpoint_type': 'server',
    }))
    assert result[0].action_id == 'escalate_p1'


def test_prototype_selector_generalizes_supported_ood_case():
    selector = build_prototype_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='ood_supported', features={
        'severity': 'low',
        'threat_confidence': 'high',
        'asset_criticality': 'tier2',
        'lateral_movement': False,
        'blast_radius': 'narrow',
        'internet_exposed': False,
        'credential_exposure': True,
        'endpoint_type': 'cloud_identity',
    }))
    assert result[0].action_id == 'rotate_credentials'
    assert result[0].confidence >= 0.6


def test_hybrid_selector_uses_prototype_for_supported_ood_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='ood_supported', features={
        'severity': 'low',
        'threat_confidence': 'high',
        'asset_criticality': 'tier2',
        'lateral_movement': False,
        'blast_radius': 'narrow',
        'internet_exposed': False,
        'credential_exposure': True,
        'endpoint_type': 'server',
    }))
    assert result[0].action_id == 'rotate_credentials'
    assert 'prototype' in result[0].source


def test_hybrid_selector_emits_semantic_noop_for_benign_informational_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='noop_supported', features={
        'severity': 'informational',
        'threat_confidence': 'medium',
        'asset_criticality': 'tier3',
        'lateral_movement': False,
        'blast_radius': 'none',
        'internet_exposed': False,
        'credential_exposure': False,
        'endpoint_type': 'host',
    }))
    assert result[0].action_id == 'do_nothing_validated'
    assert 'semantic' in result[0].source


def test_hybrid_selector_emits_semantic_fallback_for_low_confidence_identity_case():
    selector = build_hybrid_selector(TRAIN_CASES_PATH)
    result = selector.select(DecisionInput(case_id='handoff_supported', features={
        'severity': 'medium',
        'threat_confidence': 'low',
        'asset_criticality': 'tier2',
        'lateral_movement': False,
        'blast_radius': 'contained',
        'internet_exposed': True,
        'credential_exposure': True,
        'endpoint_type': 'cloud_identity',
    }))
    assert result[0].action_id == 'request_human_triage'
    assert 'semantic' in result[0].source


def test_runtime_prefers_collect_forensics_over_fallback_when_exposure_drops():
    registry = load_registry(REGISTRY_PATH)
    runtime = KVRMRuntime(
        registry,
        build_hybrid_selector(TRAIN_CASES_PATH),
        DeterministicValidator(registry),
        build_executor(),
        threshold=0.6,
        fallback_action_id='request_human_triage',
    )
    result = runtime.decide_and_execute(DecisionInput(case_id='counterfactual_collect_forensics', features={
        'severity': 'medium',
        'threat_confidence': 'medium',
        'asset_criticality': 'tier1',
        'lateral_movement': False,
        'blast_radius': 'wide',
        'internet_exposed': False,
        'credential_exposure': False,
        'endpoint_type': 'server',
    }, supported=True, ood=True, expected_action_id='collect_forensics'))

    assert result.selected_action_id == 'collect_forensics'
    assert result.final_status == FinalStatus.EXECUTED
    assert result.correct is True
