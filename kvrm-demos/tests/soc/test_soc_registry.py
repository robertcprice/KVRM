from __future__ import annotations

from pathlib import Path

from kvrm_core.registry import load_registry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / 'soc-playbook-router' / 'data' / 'registry.json'


def test_soc_registry_loads_and_has_expected_actions():
    registry = load_registry(REGISTRY_PATH)
    action_ids = {action.action_id for action in registry.actions}
    assert 'escalate_p1' in action_ids
    assert 'request_human_triage' in action_ids
    assert len(action_ids) == 8
