"""Tests for the `kvrm verify` SMT registry verifier (kvrm_core.verify).

One minimal, self-contained fixture registry per finding code, plus the
passed()/--strict semantics, the overlap witness, and the --coverage paths.
Registries are raw dicts (the verifier reads registry.json directly and does not
depend on the rest of kvrm_core), so these tests are portable and need no data files.
"""
from __future__ import annotations

import pytest

pytest.importorskip("z3")  # `kvrm verify` needs the optional [verify] extra (z3-solver)

from kvrm_core.verify import verify_registry_dict


# --- helpers -------------------------------------------------------------

def _codes(report) -> set:
    return {f.code for f in report.findings}


def _one(report, code):
    matches = [f for f in report.findings if f.code == code]
    assert len(matches) == 1, f"expected exactly one {code!r}, got {len(matches)}: {matches}"
    return matches[0]


def _reg(schema: dict, actions: list) -> dict:
    return {
        "registry_name": "test",
        "version": "0.0.0",
        "context_schema": schema,
        "actions": actions,
    }


NUM = {"type": "number"}


# --- clean / structural --------------------------------------------------

def test_clean_disjoint_registry_passes():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [
            {"action_id": "a", "support_spec": {"feature": "x", "op": "lte", "value": 0}},
            {"action_id": "b", "support_spec": {"feature": "x", "op": "gt", "value": 0}},
        ],
    ))
    assert report.passed() is True
    assert report.error_count == 0
    assert "dead_action" not in _codes(report)
    assert "overlap" not in _codes(report)
    summary = _one(report, "disjointness_summary")
    assert summary.detail["n_overlap"] == 0
    assert summary.detail["n_primary"] == 2


def test_schema_enforcement_note_always_present():
    # Even an empty registry surfaces the architectural unknown-extra-feature note.
    report = verify_registry_dict(_reg({}, []))
    assert "schema_enforcement_note" in _codes(report)
    assert report.passed() is True


# --- errors --------------------------------------------------------------

def test_dead_action_is_an_error():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [{"action_id": "dead", "support_spec": {"all": [
            {"feature": "x", "op": "gt", "value": 1},
            {"feature": "x", "op": "lt", "value": -1},
        ]}}],
    ))
    f = _one(report, "dead_action")
    assert f.severity == "ERROR"
    assert f.detail["action"] == "dead"
    assert report.passed() is False


def test_undeclared_feature_is_an_error():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [{"action_id": "a", "support_spec": {"feature": "ghost", "op": "gt", "value": 5}}],
    ))
    f = _one(report, "undeclared_feature")
    assert f.severity == "ERROR"
    assert "ghost" in f.detail["features"]
    assert report.passed() is False


def test_primary_without_spec_is_an_error():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [
            {"action_id": "a", "support_spec": {"feature": "x", "op": "gt", "value": 0}},
            {"action_id": "no_spec"},  # primary, no support_spec -> would accept anything
        ],
    ))
    f = _one(report, "primary_without_spec")
    assert f.severity == "ERROR"
    assert f.detail["action"] == "no_spec"
    assert report.passed() is False


def test_malformed_spec_is_an_error():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [{"action_id": "a", "support_spec": {"bogus": True}}],
    ))
    f = _one(report, "malformed_spec")
    assert f.severity == "ERROR"
    assert report.passed() is False


# --- warnings ------------------------------------------------------------

def test_negation_warns_and_strict_fails():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [{"action_id": "a", "support_spec": {"feature": "x", "op": "neq", "value": 5}}],
    ))
    f = _one(report, "negation_failclosure")
    assert f.severity == "WARNING"
    assert "a" in f.detail["actions"]
    assert report.passed() is True             # warnings alone still pass
    assert report.passed(strict=True) is False  # ...but not under --strict


def test_existence_op_warns():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [{"action_id": "a", "support_spec": {"feature": "x", "op": "exists"}}],
    ))
    f = _one(report, "existence_failclosure")
    assert f.severity == "WARNING"
    assert report.passed() is True


def test_ordinal_on_enum_warns():
    report = verify_registry_dict(_reg(
        {"color": {"type": "string", "enum": ["red", "green", "blue"]}},
        # numeric comparison applied to a categorical feature: a modeling mistake.
        [{"action_id": "a", "support_spec": {"feature": "color", "op": "gt", "value": "red"}}],
    ))
    f = _one(report, "ordinal_on_enum")
    assert f.severity == "WARNING"
    assert report.passed() is True


# --- overlap (INFO, never fails a registry) ------------------------------

def test_overlap_is_info_with_witness():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [
            {"action_id": "a", "support_spec": {"feature": "x", "op": "lte", "value": 10}},
            {"action_id": "b", "support_spec": {"feature": "x", "op": "gte", "value": 5}},
        ],
    ))
    f = _one(report, "overlap")
    assert f.severity == "INFO"
    assert sorted(f.detail["pair"]) == ["a", "b"]
    assert isinstance(f.detail.get("witness"), dict) and f.detail["witness"]
    assert _one(report, "disjointness_summary").detail["n_overlap"] == 1
    assert report.passed() is True


# --- fallback ------------------------------------------------------------

def test_catch_all_fallback_is_info():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [
            {"action_id": "a", "support_spec": {"feature": "x", "op": "gt", "value": 0}},
            {"action_id": "human", "tags": ["fallback"]},  # no support_spec, fallback-tagged
        ],
    ))
    f = _one(report, "catch_all_fallback")
    assert f.severity == "INFO"
    assert "human" in report.fallback_actions
    assert "primary_without_spec" not in _codes(report)  # a fallback is not a primary
    assert report.passed() is True


# --- coverage (optional, --coverage) -------------------------------------

def test_coverage_reports_abstention_region():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [{"action_id": "a", "support_spec": {"feature": "x", "op": "gt", "value": 100}}],
    ), coverage=True)
    assert "abstention_region" in _codes(report)


def test_coverage_reports_full_coverage():
    report = verify_registry_dict(_reg(
        {"x": NUM},
        [
            {"action_id": "a", "support_spec": {"feature": "x", "op": "lte", "value": 0}},
            {"action_id": "b", "support_spec": {"feature": "x", "op": "gt", "value": 0}},
        ],
    ), coverage=True)
    assert "full_coverage" in _codes(report)
