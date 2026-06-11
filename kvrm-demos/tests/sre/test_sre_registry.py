from __future__ import annotations

from pathlib import Path

from kvrm_core.registry import load_registry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / 'sre-policy-router' / 'data' / 'registry.json'


def test_sre_registry_loads_and_has_expected_actions():
    registry = load_registry(REGISTRY_PATH)
    action_ids = {action.action_id for action in registry.actions}
    assert 'rollback_deploy' in action_ids
    assert 'page_human_operator' in action_ids
    assert len(action_ids) == 8
    assert 'operator_response_eta' in registry.required_features
    assert 'mitigation_window_remaining' in registry.required_features
    assert 'quorum_health' in registry.required_features
    assert 'control_plane_availability' in registry.required_features
