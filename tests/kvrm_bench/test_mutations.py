from __future__ import annotations

from kvrm_bench.mutations import append_action, classify_registry_compatibility, make_incompatible_mutation, reorder_actions


def base_registry():
    return {
        'registry_name': 'toy',
        'version': '1.0.0',
        'actions': [
            {'action_id': 'a', 'name': 'A', 'description': 'A'},
            {'action_id': 'b', 'name': 'B', 'description': 'B'},
        ],
    }


def test_append_only_mutation_classified_correctly():
    updated = append_action(base_registry(), {'action_id': 'c', 'name': 'C', 'description': 'C'})
    assert classify_registry_compatibility(base_registry(), updated) == 'append_only'


def test_reorder_only_mutation_classified_correctly():
    updated = reorder_actions(base_registry(), [1, 0])
    assert classify_registry_compatibility(base_registry(), updated) == 'reorder_only'


def test_incompatible_mutation_classified_correctly():
    updated = make_incompatible_mutation(base_registry(), 'a', 'different')
    assert classify_registry_compatibility(base_registry(), updated) == 'incompatible'
