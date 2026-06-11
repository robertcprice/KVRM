import json

import pytest

from kvrm_core import (
    DecisionInput,
    DomainDirError,
    build_domain_runtime,
    evaluate_domain,
    load_domain_dir,
    scaffold_domain,
)
from kvrm_core.cli import main as cli_main
from kvrm_core.learned import save_compact_model_artifact, train_compact_model
from kvrm_core.registry import validate_registry


@pytest.fixture()
def scaffolded(tmp_path):
    root = scaffold_domain(tmp_path / "loan-review")
    return load_domain_dir(root)


def test_scaffold_produces_valid_loadable_domain(scaffolded):
    validate_registry(scaffolded.registry)
    assert scaffolded.registry.registry_name == "loan_review"
    assert len(scaffolded.registry.actions) == 3
    assert scaffolded.config.fallback_action_id == "escalate_to_human"
    assert scaffolded.config.feature_order == ["risk_level", "amount", "account_verified"]
    assert scaffolded.config.categorical_values == {"risk_level": ["low", "medium", "high"]}
    assert scaffolded.config.numeric_feature_ranges == {"amount": (0.0, 10000.0)}
    assert len(scaffolded.config.rules) == 8


def test_scaffold_refuses_to_overwrite(tmp_path):
    scaffold_domain(tmp_path / "domain")
    with pytest.raises(DomainDirError, match="refusing to overwrite"):
        scaffold_domain(tmp_path / "domain")


def test_load_domain_dir_requires_registry_and_train_cases(tmp_path):
    with pytest.raises(DomainDirError, match="registry.json"):
        load_domain_dir(tmp_path)
    (tmp_path / "registry.json").write_text("{}")
    with pytest.raises(DomainDirError, match="train_cases.jsonl"):
        load_domain_dir(tmp_path)


def test_supported_input_executes(scaffolded):
    runtime = build_domain_runtime(scaffolded)
    decision = runtime.decide_and_execute(
        DecisionInput(
            case_id="t1",
            features={"risk_level": "low", "amount": 100.0, "account_verified": True},
        )
    )
    assert decision.selected_action_id == "approve_request"
    assert str(decision.final_status) == "FinalStatus.EXECUTED"
    assert decision.valid


def test_out_of_envelope_input_fails_closed(scaffolded):
    runtime = build_domain_runtime(scaffolded)
    decision = runtime.decide_and_execute(
        DecisionInput(
            case_id="t2",
            features={"risk_level": "low", "amount": 999999.0, "account_verified": True},
        )
    )
    # Outside every automatic envelope: must land on the audited fallback or
    # abstain — never silently execute approve/deny.
    assert decision.selected_action_id != "approve_request"
    assert decision.selected_action_id != "deny_request"
    assert decision.final_status.value in ("fallback_executed", "fail_closed", "abstained")


def test_evaluate_domain_with_trained_model_is_perfect(scaffolded):
    train_cases = [
        json.loads(line)
        for line in scaffolded.train_cases_path.read_text().splitlines()
        if line.strip()
    ]
    artifact = train_compact_model(train_cases=train_cases, registry=scaffolded.registry)
    save_compact_model_artifact(scaffolded.default_model_path, artifact)

    runtime = build_domain_runtime(scaffolded)
    metrics = evaluate_domain(scaffolded, runtime)
    assert metrics["total_cases"] == 4
    assert metrics["semantic_correctness_rate"] == 1.0
    assert metrics["false_accept_rate"] == 0.0
    assert metrics["unsupported_case_rejection_rate"] == 1.0
    assert metrics["invalid_output_rate"] == 0.0
    assert metrics["failures"] == []


def test_cli_full_workflow(tmp_path, capsys):
    domain_dir = str(tmp_path / "wf")
    cli_main(["init", domain_dir])
    cli_main(["validate", domain_dir])
    cli_main(["train", domain_dir])
    cli_main(["eval", domain_dir, "--json"])
    out = capsys.readouterr().out
    assert "validation passed" in out
    assert '"semantic_correctness_rate": 1.0' in out
    assert '"false_accept_rate": 0.0' in out


def test_cli_route_unsupported_fails_closed(tmp_path, capsys):
    domain_dir = str(tmp_path / "fc")
    cli_main(["init", domain_dir])
    capsys.readouterr()
    cli_main(
        [
            "route",
            domain_dir,
            "-f",
            json.dumps(
                {"risk_level": "low", "amount": 999999.0, "account_verified": True}
            ),
            "--json",
        ]
    )
    decision = json.loads(capsys.readouterr().out)
    assert decision["selected_action_id"] not in ("approve_request", "deny_request")
    assert decision["final_status"] in ("fallback_executed", "fail_closed", "abstained")


def test_cli_validate_rejects_unknown_expected_action(tmp_path, capsys):
    root = scaffold_domain(tmp_path / "bad")
    cases_path = root / "cases.jsonl"
    cases = cases_path.read_text().splitlines()
    broken = json.loads(cases[0])
    broken["expected_action_id"] = "not_a_real_action"
    cases[0] = json.dumps(broken)
    cases_path.write_text("\n".join(cases) + "\n")
    with pytest.raises(SystemExit, match="validation failed"):
        cli_main(["validate", str(root)])
