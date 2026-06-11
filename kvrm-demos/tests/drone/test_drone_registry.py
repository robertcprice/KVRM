from __future__ import annotations

from pathlib import Path

from kvrm_core.registry import load_registry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / 'drone-mission-router' / 'data' / 'registry.json'


def test_drone_registry_loads_and_has_expected_actions():
    registry = load_registry(REGISTRY_PATH)
    action_ids = {action.action_id for action in registry.actions}
    assert 'return_to_home' in action_ids
    assert 'manual_handoff' in action_ids
    assert len(action_ids) == 8
    assert 'pilot_response_eta' in registry.required_features
    assert 'takeover_window_remaining' in registry.required_features
    assert 'airspace_deconfliction_status' in registry.required_features
    assert 'operator_control_latency_budget' in registry.required_features
