"""Property test for the core fail-closed invariants.

Routes a few hundred randomized inputs — valid, boundary, and schema-violating
— through a scaffolded domain and asserts the invariants the paper claims:

1. The runtime never emits an action that is not in the registry.
2. An input outside every action's support envelope never executes a
   non-fallback action ("false accept").
3. Every decision carries an audit record bound to the registry digest.
"""

import random

import pytest

from kvrm_core import (
    DecisionInput,
    build_domain_runtime,
    load_domain_dir,
    scaffold_domain,
)
from kvrm_core.support import evaluate_support_spec

RISK_LEVELS = ["low", "medium", "high"]
AMOUNTS = [0.0, 1.0, 250.0, 4999.99, 5000.0, 5000.01, 9999.0, 10000.0, 15000.0, 1e9]
BOOLS = [True, False]


@pytest.fixture(scope="module")
def domain(tmp_path_factory):
    root = scaffold_domain(tmp_path_factory.mktemp("fuzz") / "domain")
    return load_domain_dir(root)


@pytest.fixture(scope="module")
def runtime(domain):
    return build_domain_runtime(domain)


def _supported_by_any_action(domain, features) -> bool:
    return any(
        evaluate_support_spec(action.support_spec, features)[0]
        for action in domain.registry.actions
        if "fallback" not in action.tags
    )


def test_fuzz_fail_closed_invariants(domain, runtime):
    rng = random.Random(1337)
    action_ids = {action.action_id for action in domain.registry.actions}
    fallback_id = domain.config.fallback_action_id

    checked = false_accept_candidates = 0
    for index in range(300):
        features = {
            "risk_level": rng.choice(RISK_LEVELS),
            "amount": rng.choice(AMOUNTS),
            "account_verified": rng.choice(BOOLS),
        }
        decision = runtime.decide_and_execute(
            DecisionInput(case_id=f"fuzz_{index}", features=features)
        )
        checked += 1

        # Invariant 1: output is a registered action or nothing.
        assert decision.selected_action_id is None or decision.selected_action_id in action_ids

        # Invariant 3: audit record present and digest-bound.
        assert decision.audit_record is not None
        assert decision.audit_record.registry_digest

        # Invariant 2: out-of-envelope inputs never execute a non-fallback action.
        if not _supported_by_any_action(domain, features):
            false_accept_candidates += 1
            executed_real = (
                str(decision.final_status) == "FinalStatus.EXECUTED"
                and decision.selected_action_id != fallback_id
            )
            assert not executed_real, (
                f"false accept on {features}: executed {decision.selected_action_id}"
            )

    assert checked == 300
    # The amount grid intentionally includes out-of-envelope values; make sure
    # the unsupported branch was actually exercised.
    assert false_accept_candidates > 20


def test_fuzz_schema_violating_inputs_never_execute_unregistered(domain, runtime):
    rng = random.Random(7)
    action_ids = {action.action_id for action in domain.registry.actions}
    garbage_values = ["bogus", -1.0, None, 1e18, "HIGH", [], {}, "∅"]

    for index in range(100):
        features = {
            "risk_level": rng.choice(RISK_LEVELS + ["bogus", "HIGH", None]),
            "amount": rng.choice(AMOUNTS + [-5.0, None, "lots"]),
            "account_verified": rng.choice(BOOLS + [None, "yes"]),
        }
        if rng.random() < 0.3:
            features[rng.choice(["extra_field", "risk", ""])] = rng.choice(garbage_values)
        if rng.random() < 0.2:
            features.pop(rng.choice(list(features)), None)

        decision = runtime.decide_and_execute(
            DecisionInput(case_id=f"garbage_{index}", features=features)
        )
        assert decision.selected_action_id is None or decision.selected_action_id in action_ids
        assert decision.audit_record is not None
