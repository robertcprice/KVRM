from __future__ import annotations

from copy import deepcopy


def append_action(registry: dict, action: dict) -> dict:
    updated = deepcopy(registry)
    updated['actions'].append(action)
    return updated


def reorder_actions(registry: dict, order: list[int]) -> dict:
    updated = deepcopy(registry)
    updated['actions'] = [updated['actions'][i] for i in order]
    return updated


def make_incompatible_mutation(registry: dict, action_id: str, new_name: str) -> dict:
    updated = deepcopy(registry)
    for action in updated['actions']:
        if action['action_id'] == action_id:
            action['name'] = new_name
            action['description'] = f'incompatible:{new_name}'
            break
    return updated


def classify_registry_compatibility(old: dict, new: dict) -> str:
    old_ids = [a['action_id'] for a in old['actions']]
    new_ids = [a['action_id'] for a in new['actions']]
    if old_ids == new_ids:
        for old_action, new_action in zip(old['actions'], new['actions']):
            if old_action != new_action:
                return 'incompatible'
        return 'identical'
    if set(old_ids) == set(new_ids):
        return 'reorder_only'
    if all(action_id in new_ids for action_id in old_ids):
        return 'append_only'
    return 'incompatible'
