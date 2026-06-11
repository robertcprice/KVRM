from __future__ import annotations

import json
from pathlib import Path

from kvrm_bench.demo import (
    assess_case_promotion_readiness,
    append_case_draft,
    build_case_review_queue,
    build_draft_case_queue,
    clear_demo_caches,
    diagnose_case_promotion_readiness,
    export_draft_case_bundle,
    export_selected_draft_cases,
    find_adjacent_draft_group_index,
    load_domain_action_ids,
    load_domain_artifact_summary,
    load_domain_training_artifact_summary,
    load_draft_case_counts,
    load_incident_replay_episodes,
    promote_ready_draft_cases,
    promote_draft_case,
    run_demo_case_matrix,
    run_incident_replay_episode_matrix,
    summarize_draft_group,
    summarize_draft_cases,
    update_draft_case,
    update_selected_draft_cases,
    write_draft_export_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _prepend_demo_paths(monkeypatch) -> None:
    for rel in (
        "kvrm-core/src",
        "kvrm-bench/src",
        "kvrm-demos/soc-playbook-router",
        "kvrm-demos/sre-policy-router",
        "kvrm-demos/drone-mission-router",
        "kvrm-demos/grid-ops-router",
        "kvrm-demos/finance-risk-router",
        "kvrm-demos/medical-workflow-router",
    ):
        monkeypatch.syspath_prepend(str(REPO_ROOT / rel))


def test_run_demo_case_matrix_returns_strategy_comparison(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    learned_model_path = REPO_ROOT / "kvrm-models" / "finance_compact_selector_v1.joblib"
    payload = run_demo_case_matrix(
        repo_root=REPO_ROOT,
        domain="finance",
        eval_filename="cases.jsonl",
        case_index=16,
        learned_model_path=str(learned_model_path),
    )

    assert payload["case"]["case_id"] == "finance_case_017"
    assert payload["decision"]["selected_action_id"] == "manual_review"
    strategy_results = {row["strategy"]: row["decision"] for row in payload["strategy_results"]}
    assert {"rule", "retrieval", "prototype", "semantic", "hybrid"} <= set(strategy_results)
    if learned_model_path.exists():
        assert "learned" in strategy_results
    assert strategy_results["hybrid"]["selected_action_id"] == "manual_review"


def test_load_domain_artifact_summary_reports_schema_counts() -> None:
    summary = load_domain_artifact_summary(REPO_ROOT, "medical")

    assert summary["registry_name"] == "medical-workflow-router"
    assert summary["registry_version"] == "1.2.0"
    assert summary["required_feature_count"] == 10
    assert summary["context_field_count"] == 10
    assert summary["train_case_count"] == 35
    assert summary["eval_case_count"] == 24
    assert summary["supported_case_count"] == 18
    assert summary["unsupported_case_count"] == 6


def test_load_domain_training_artifact_summary_reports_ready_artifacts() -> None:
    for domain in ("soc", "sre", "drone", "grid", "finance", "medical", "iam"):
        summary = load_domain_training_artifact_summary(REPO_ROOT, domain)

        assert summary["domain"] == domain
        assert summary["report_exists"] is True
        assert summary["model_exists"] is True
        assert summary["report_domain_matches"] is True
        assert summary["registry_digest_matches"] is True
        assert summary["train_case_count_matches"] is True
        assert summary["model_fresh"] is True
        assert summary["report_fresh"] is True
        assert summary["status"] == "ready"
        assert summary["model_size_bytes"] > 0
        assert summary["metadata"]["n_estimators"] == 256


def test_build_case_review_queue_includes_boundary_cases(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    queue = build_case_review_queue(
        repo_root=REPO_ROOT,
        domain="finance",
        eval_filename="cases.jsonl",
        learned_model_path=str(REPO_ROOT / "kvrm-models" / "finance_compact_selector_v1.joblib"),
    )

    assert queue[0]["case_id"] == "finance_case_002"
    assert "strategy_disagreement" in queue[0]["review_flags"]

    boundary = next(row for row in queue if row["case_id"] == "finance_case_017")
    assert "supported_ood" in boundary["review_flags"]
    assert boundary["selected_action_id"] == "manual_review"


def test_run_incident_replay_episode_matrix_returns_strategy_comparison(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    episodes = load_incident_replay_episodes(REPO_ROOT, "drone")
    authored_index = next(
        index for index, episode in enumerate(episodes) if episode.get("episode_source") == "authored"
    )
    payload = run_incident_replay_episode_matrix(
        repo_root=REPO_ROOT,
        domain="drone",
        episode_index=authored_index,
        step_index=0,
        learned_model_path=str(REPO_ROOT / "kvrm-models" / "drone_compact_selector_v1.joblib"),
    )

    replay_entry = payload["replay_entry"]
    assert replay_entry["episode_source"] == "authored"
    assert replay_entry["step_count"] == 4
    assert replay_entry["step_index"] == 0
    assert payload["case"]["case_id"] == replay_entry["step"]["case"]["case_id"]
    strategy_results = {row["strategy"]: row["decision"] for row in payload["strategy_results"]}
    assert {"rule", "retrieval", "prototype", "semantic", "hybrid"} <= set(strategy_results)
    assert strategy_results["hybrid"]["selected_action_id"] == payload["decision"]["selected_action_id"]


def test_append_case_draft_writes_pending_review_record(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    data_dir.mkdir(parents=True)
    case = {
        "case_id": "finance_case_x",
        "input_features": {"transaction_amount": "high"},
        "expected_action_id": None,
        "supported": False,
        "ood": True,
    }
    decision = {
        "selected_action_id": "manual_review",
        "confidence": 1.0,
        "final_status": "fallback_executed",
    }
    strategy_results = [
        {"strategy": "hybrid", "decision": {"selected_action_id": "manual_review", "confidence": 1.0, "final_status": "fallback_executed", "correct": False}},
    ]

    result = append_case_draft(
        repo_root=tmp_path,
        domain="finance",
        eval_filename="cases.jsonl",
        case=case,
        decision=decision,
        strategy_results=strategy_results,
        target="review",
        review_flags=["unsupported_case", "fallback_path"],
    )

    draft_path = Path(result["path"])
    assert draft_path.exists()
    rows = [json.loads(line) for line in draft_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["draft_meta"]["review_status"] == "pending"
    assert rows[0]["draft_meta"]["proposed_expected_action_id"] == "manual_review"
    assert load_draft_case_counts(tmp_path, "finance")["review"] == 1


def test_update_and_promote_draft_case_round_trip(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    draft_path = drafts_dir / "train_candidate_cases.jsonl"
    draft_row = {
        "case_id": "finance_draft_train_001",
        "input_features": {"transaction_amount": "high"},
        "expected_action_id": None,
        "supported": True,
        "ood": False,
        "draft_meta": {
            "target_split": "train",
            "source_case_id": "finance_case_x",
            "source_eval_filename": "cases.jsonl",
            "proposed_expected_action_id": "manual_review",
            "review_status": "pending",
            "review_flags": ["fallback_path"],
        },
    }
    draft_path.write_text(json.dumps(draft_row) + "\n", encoding="utf-8")

    updated = update_draft_case(
        repo_root=tmp_path,
        domain="finance",
        target="train",
        draft_index=0,
        expected_action_id="manual_review",
        supported=True,
        review_status="reviewed",
    )
    assert updated["draft_case"]["expected_action_id"] == "manual_review"
    assert updated["draft_case"]["draft_meta"]["review_status"] == "reviewed"
    assert load_domain_action_ids(tmp_path, "finance") == ["manual_review"]

    promoted = promote_draft_case(
        repo_root=tmp_path,
        domain="finance",
        target="train",
        draft_index=0,
    )
    train_rows = [json.loads(line) for line in (data_dir / "train_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    draft_rows = [json.loads(line) for line in draft_path.read_text(encoding="utf-8").splitlines()]

    assert promoted["promoted_case"]["expected_action_id"] == "manual_review"
    assert train_rows[0]["case_id"] == "finance_draft_train_001"
    assert draft_rows[0]["draft_meta"]["review_status"] == "promoted_train"


def test_assess_case_promotion_readiness_distinguishes_train_vs_eval(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    supported_case = {
        "case_id": "finance_case_002",
        "input_features": {
            "transaction_amount": "medium",
            "jurisdiction_risk": "low",
            "anomaly_score": "low",
            "account_history": "clean",
            "kyc_completeness": "complete",
            "velocity_indicator": "normal",
            "sanctions_hit": False,
            "document_mismatch": False,
            "device_trust": "new",
        },
        "expected_action_id": "approve_low_risk",
        "supported": True,
        "ood": True,
    }
    unsupported_case = {
        "case_id": "finance_case_019",
        "input_features": {
            "transaction_amount": "mega",
            "jurisdiction_risk": "low",
            "anomaly_score": "low",
            "account_history": "clean",
            "kyc_completeness": "complete",
            "velocity_indicator": "normal",
            "sanctions_hit": False,
            "document_mismatch": False,
            "device_trust": "trusted",
        },
        "expected_action_id": None,
        "supported": False,
        "ood": True,
    }

    supported = assess_case_promotion_readiness(REPO_ROOT, "finance", supported_case)
    unsupported = assess_case_promotion_readiness(REPO_ROOT, "finance", unsupported_case)

    assert supported["train_ready"] is True
    assert supported["recommended_target"] == "train"
    assert unsupported["context_valid"] is False
    assert unsupported["eval_ready"] is True
    assert unsupported["recommended_target"] == "eval"


def test_diagnose_case_promotion_readiness_describes_context_and_action_issues(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount", "jurisdiction_risk"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high", "low"]},
                    "jurisdiction_risk": {"type": "string", "enum": ["low", "high"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    missing_feature = diagnose_case_promotion_readiness(
        tmp_path,
        "finance",
        {
            "case_id": "finance_diag_001",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
        },
    )
    assert missing_feature["primary_diagnostic"]["code"] == "missing_required_feature"
    assert "missing required feature jurisdiction_risk" == missing_feature["primary_diagnostic"]["message"]

    unsupported_action = diagnose_case_promotion_readiness(
        tmp_path,
        "finance",
        {
            "case_id": "finance_diag_002",
            "input_features": {"transaction_amount": "low", "jurisdiction_risk": "low"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
        },
    )
    assert unsupported_action["primary_diagnostic"]["code"] == "unsupported_feature_value"
    assert "manual_review requires transaction_amount = high" == unsupported_action["primary_diagnostic"]["message"]

    unknown_action = diagnose_case_promotion_readiness(
        tmp_path,
        "finance",
        {
            "case_id": "finance_diag_003",
            "input_features": {"transaction_amount": "high", "jurisdiction_risk": "low"},
            "expected_action_id": "not_in_registry",
            "supported": True,
            "ood": False,
        },
    )
    assert unknown_action["primary_diagnostic"]["code"] == "unknown_expected_action"
    assert "expected action not_in_registry is not declared in the registry" == unknown_action["primary_diagnostic"]["message"]


def test_review_draft_defaults_to_recommended_promotion_target(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_path = drafts_dir / "review_cases.jsonl"
    review_path.write_text(
        json.dumps(
            {
                "case_id": "finance_draft_review_001",
                "input_features": {"transaction_amount": "high"},
                "expected_action_id": "manual_review",
                "supported": True,
                "ood": False,
                "draft_meta": {
                    "target_split": "review",
                    "source_case_id": "finance_case_x",
                    "source_eval_filename": "cases.jsonl",
                    "proposed_expected_action_id": "manual_review",
                    "review_status": "reviewed",
                    "review_flags": ["supported_ood"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    promoted = promote_draft_case(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_index=0,
    )
    train_rows = [json.loads(line) for line in (data_dir / "train_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert promoted["destination_path"].endswith("train_cases.jsonl")
    assert train_rows[0]["case_id"] == "finance_draft_review_001"


def test_review_draft_requires_explicit_label_before_train_promotion(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_path = drafts_dir / "review_cases.jsonl"
    review_path.write_text(
        json.dumps(
            {
                "case_id": "finance_draft_review_002",
                "input_features": {"transaction_amount": "high"},
                "expected_action_id": None,
                "supported": True,
                "ood": False,
                "draft_meta": {
                    "target_split": "review",
                    "source_case_id": "finance_case_y",
                    "source_eval_filename": "cases.jsonl",
                    "proposed_expected_action_id": "manual_review",
                    "review_status": "reviewed",
                    "review_flags": ["supported_ood"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        promote_draft_case(
            repo_root=tmp_path,
            domain="finance",
            target="review",
            draft_index=0,
        )
    except ValueError as exc:
        assert str(exc) == "draft is not ready for train or eval promotion"
    else:
        raise AssertionError("promotion should require an explicit expected action label")


def test_unsupported_review_draft_promotes_to_eval_without_action_label(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_path = drafts_dir / "review_cases.jsonl"
    review_path.write_text(
        json.dumps(
            {
                "case_id": "finance_draft_review_003",
                "input_features": {"transaction_amount": "mega"},
                "expected_action_id": None,
                "supported": False,
                "ood": True,
                "draft_meta": {
                    "target_split": "review",
                    "source_case_id": "finance_case_z",
                    "source_eval_filename": "cases.jsonl",
                    "proposed_expected_action_id": "manual_review",
                    "review_status": "reviewed",
                    "review_flags": ["unsupported_case"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    promoted = promote_draft_case(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_index=0,
    )
    eval_rows = [json.loads(line) for line in (data_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()]

    assert promoted["destination_path"].endswith("cases.jsonl")
    assert eval_rows[0]["case_id"] == "finance_draft_review_003"
    assert eval_rows[0]["expected_action_id"] is None


def test_summarize_and_batch_promote_ready_review_drafts(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_path = drafts_dir / "review_cases.jsonl"
    review_rows = [
        {
            "case_id": "finance_draft_review_101",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {
                "target_split": "review",
                "source_case_id": "finance_case_a",
                "source_eval_filename": "cases.jsonl",
                "proposed_expected_action_id": "manual_review",
                "review_status": "reviewed",
                "review_flags": ["supported_ood"],
            },
        },
        {
            "case_id": "finance_draft_review_102",
            "input_features": {"transaction_amount": "mega"},
            "expected_action_id": None,
            "supported": False,
            "ood": True,
            "draft_meta": {
                "target_split": "review",
                "source_case_id": "finance_case_b",
                "source_eval_filename": "cases.jsonl",
                "proposed_expected_action_id": "manual_review",
                "review_status": "reviewed",
                "review_flags": ["unsupported_case"],
            },
        },
        {
            "case_id": "finance_draft_review_103",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {
                "target_split": "review",
                "source_case_id": "finance_case_c",
                "source_eval_filename": "cases.jsonl",
                "proposed_expected_action_id": "manual_review",
                "review_status": "pending",
                "review_flags": ["supported_ood"],
            },
        },
    ]
    review_path.write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    summary_before = summarize_draft_cases(tmp_path, "finance", "review")
    assert summary_before == {
        "target": "review",
        "total_count": 3,
        "pending_count": 1,
        "reviewed_count": 2,
        "promoted_count": 0,
        "train_ready_count": 2,
        "eval_ready_count": 3,
        "blocked_count": 0,
        "promotable_count": 2,
        "blocked_diagnostic_counts": [],
    }

    promoted = promote_ready_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
    )
    assert promoted["promoted_count"] == 2
    assert promoted["eligible_count"] == 2
    assert promoted["skipped_count"] == 1
    assert promoted["destination_counts"] == {"train": 1, "eval": 1}
    assert promoted["promoted_case_ids"] == [
        "finance_draft_review_101",
        "finance_draft_review_102",
    ]

    train_rows = [json.loads(line) for line in (data_dir / "train_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    eval_rows = [json.loads(line) for line in (data_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    updated_review_rows = [json.loads(line) for line in review_path.read_text(encoding="utf-8").splitlines()]

    assert [row["case_id"] for row in train_rows] == ["finance_draft_review_101"]
    assert [row["case_id"] for row in eval_rows] == ["finance_draft_review_102"]
    assert updated_review_rows[0]["draft_meta"]["review_status"] == "promoted_train"
    assert updated_review_rows[1]["draft_meta"]["review_status"] == "promoted_eval"
    assert updated_review_rows[2]["draft_meta"]["review_status"] == "pending"

    summary_after = summarize_draft_cases(tmp_path, "finance", "review")
    assert summary_after == {
        "target": "review",
        "total_count": 3,
        "pending_count": 1,
        "reviewed_count": 0,
        "promoted_count": 2,
        "train_ready_count": 2,
        "eval_ready_count": 3,
        "blocked_count": 0,
        "promotable_count": 0,
        "blocked_diagnostic_counts": [],
    }


def test_promote_ready_draft_cases_can_scope_to_visible_group(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high", "mega"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_rows = [
        {
            "case_id": "finance_draft_review_301",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_302",
            "input_features": {"transaction_amount": "mega"},
            "expected_action_id": None,
            "supported": False,
            "ood": True,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_303",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_304",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
    ]
    (drafts_dir / "review_cases.jsonl").write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    promoted = promote_ready_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_filter="reviewed",
        draft_sort="target",
        group_label="train",
    )
    assert promoted["draft_filter"] == "reviewed"
    assert promoted["draft_sort"] == "target"
    assert promoted["group_label"] == "train"
    assert promoted["selected_count"] == 2
    assert promoted["eligible_count"] == 2
    assert promoted["promoted_count"] == 2
    assert promoted["skipped_count"] == 0
    assert promoted["unselected_count"] == 2
    assert promoted["destination_counts"] == {"train": 2, "eval": 0}
    assert promoted["promoted_case_ids"] == [
        "finance_draft_review_301",
        "finance_draft_review_303",
    ]

    train_rows = [json.loads(line) for line in (data_dir / "train_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    eval_rows = [json.loads(line) for line in (data_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    updated_review_rows = [json.loads(line) for line in (drafts_dir / "review_cases.jsonl").read_text(encoding="utf-8").splitlines()]

    assert [row["case_id"] for row in train_rows] == [
        "finance_draft_review_301",
        "finance_draft_review_303",
    ]
    assert eval_rows == []
    assert updated_review_rows[0]["draft_meta"]["review_status"] == "promoted_train"
    assert updated_review_rows[1]["draft_meta"]["review_status"] == "reviewed"
    assert updated_review_rows[2]["draft_meta"]["review_status"] == "promoted_train"
    assert updated_review_rows[3]["draft_meta"]["review_status"] == "pending"


def test_update_selected_draft_cases_can_mark_current_group_reviewed(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high", "mega"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_rows = [
        {
            "case_id": "finance_draft_review_401",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_402",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_403",
            "input_features": {"transaction_amount": "mega"},
            "expected_action_id": None,
            "supported": False,
            "ood": True,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_404",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "promoted_train"},
        },
    ]
    (drafts_dir / "review_cases.jsonl").write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    updated = update_selected_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_filter="all",
        draft_sort="target",
        group_label="train",
        review_status="reviewed",
    )
    assert updated["group_label"] == "train"
    assert updated["selected_count"] == 3
    assert updated["updated_count"] == 2
    assert updated["unchanged_count"] == 0
    assert updated["skipped_promoted_count"] == 1
    assert updated["updated_case_ids"] == [
        "finance_draft_review_401",
        "finance_draft_review_402",
    ]
    assert updated["skipped_promoted_case_ids"] == ["finance_draft_review_404"]

    updated_review_rows = [json.loads(line) for line in (drafts_dir / "review_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert updated_review_rows[0]["draft_meta"]["review_status"] == "reviewed"
    assert updated_review_rows[1]["draft_meta"]["review_status"] == "reviewed"
    assert updated_review_rows[2]["draft_meta"]["review_status"] == "reviewed"
    assert updated_review_rows[3]["draft_meta"]["review_status"] == "promoted_train"


def test_update_selected_draft_cases_can_apply_group_flags(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high", "mega"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_rows = [
        {
            "case_id": "finance_draft_review_421",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_422",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_423",
            "input_features": {"transaction_amount": "mega"},
            "expected_action_id": None,
            "supported": False,
            "ood": True,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_424",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "promoted_train"},
        },
    ]
    (drafts_dir / "review_cases.jsonl").write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    updated = update_selected_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_filter="all",
        draft_sort="target",
        group_label="train",
        supported=False,
        ood=True,
    )
    assert updated["group_label"] == "train"
    assert updated["selected_count"] == 3
    assert updated["updated_count"] == 2
    assert updated["unchanged_count"] == 0
    assert updated["skipped_promoted_count"] == 1
    assert updated["updated_case_ids"] == [
        "finance_draft_review_421",
        "finance_draft_review_422",
    ]
    assert updated["skipped_promoted_case_ids"] == ["finance_draft_review_424"]

    updated_review_rows = [json.loads(line) for line in (drafts_dir / "review_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert updated_review_rows[0]["supported"] is False
    assert updated_review_rows[0]["ood"] is True
    assert updated_review_rows[1]["supported"] is False
    assert updated_review_rows[1]["ood"] is True
    assert updated_review_rows[2]["supported"] is False
    assert updated_review_rows[2]["ood"] is True
    assert updated_review_rows[3]["supported"] is True
    assert updated_review_rows[3]["ood"] is False


def test_update_selected_draft_cases_can_mark_visible_slice_pending(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high", "mega"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_rows = [
        {
            "case_id": "finance_draft_review_451",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_452",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_453",
            "input_features": {"transaction_amount": "mega"},
            "expected_action_id": None,
            "supported": False,
            "ood": True,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_454",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "promoted_train"},
        },
    ]
    (drafts_dir / "review_cases.jsonl").write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    updated = update_selected_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_filter="all",
        draft_sort="queue",
        review_status="pending",
    )
    assert updated["group_label"] is None
    assert updated["selected_count"] == 4
    assert updated["updated_count"] == 2
    assert updated["unchanged_count"] == 1
    assert updated["skipped_promoted_count"] == 1
    assert updated["updated_case_ids"] == [
        "finance_draft_review_451",
        "finance_draft_review_452",
    ]
    assert updated["skipped_promoted_case_ids"] == ["finance_draft_review_454"]

    updated_review_rows = [json.loads(line) for line in (drafts_dir / "review_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert updated_review_rows[0]["draft_meta"]["review_status"] == "pending"
    assert updated_review_rows[1]["draft_meta"]["review_status"] == "pending"
    assert updated_review_rows[2]["draft_meta"]["review_status"] == "pending"
    assert updated_review_rows[3]["draft_meta"]["review_status"] == "promoted_train"


def test_update_selected_draft_cases_can_apply_visible_slice_flags(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high", "mega"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_rows = [
        {
            "case_id": "finance_draft_review_461",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_462",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_463",
            "input_features": {"transaction_amount": "mega"},
            "expected_action_id": None,
            "supported": False,
            "ood": True,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_464",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "promoted_train"},
        },
    ]
    (drafts_dir / "review_cases.jsonl").write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    updated = update_selected_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_filter="all",
        draft_sort="queue",
        supported=False,
        ood=True,
    )
    assert updated["group_label"] is None
    assert updated["selected_count"] == 4
    assert updated["updated_count"] == 2
    assert updated["unchanged_count"] == 1
    assert updated["skipped_promoted_count"] == 1
    assert updated["updated_case_ids"] == [
        "finance_draft_review_461",
        "finance_draft_review_462",
    ]
    assert updated["skipped_promoted_case_ids"] == ["finance_draft_review_464"]

    updated_review_rows = [json.loads(line) for line in (drafts_dir / "review_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert updated_review_rows[0]["supported"] is False
    assert updated_review_rows[0]["ood"] is True
    assert updated_review_rows[1]["supported"] is False
    assert updated_review_rows[1]["ood"] is True
    assert updated_review_rows[2]["supported"] is False
    assert updated_review_rows[2]["ood"] is True
    assert updated_review_rows[3]["supported"] is True
    assert updated_review_rows[3]["ood"] is False


def test_export_selected_draft_cases_writes_slice_and_group_artifacts(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high", "mega"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_rows = [
        {
            "case_id": "finance_draft_review_471",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_472",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_473",
            "input_features": {"transaction_amount": "mega"},
            "expected_action_id": None,
            "supported": False,
            "ood": True,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_474",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "promoted_train"},
        },
    ]
    (drafts_dir / "review_cases.jsonl").write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    slice_export = export_selected_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_filter="all",
        draft_sort="queue",
    )
    assert slice_export["scope"] == "slice"
    assert slice_export["selection_count"] == 4
    assert Path(slice_export["json_path"]).exists()
    assert Path(slice_export["jsonl_path"]).exists()
    slice_payload = json.loads(Path(slice_export["json_path"]).read_text(encoding="utf-8"))
    assert slice_payload["scope"] == "slice"
    assert slice_payload["selection_summary"]["count"] == 4
    assert slice_payload["group_summary"] is None
    assert len(slice_payload["entries"]) == 4

    group_export = export_selected_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_filter="all",
        draft_sort="target",
        group_label="train",
    )
    assert group_export["scope"] == "group"
    assert group_export["selection_count"] == 3
    assert Path(group_export["json_path"]).exists()
    assert Path(group_export["jsonl_path"]).exists()
    assert "scope-group-train" in group_export["json_path"]
    group_payload = json.loads(Path(group_export["json_path"]).read_text(encoding="utf-8"))
    assert group_payload["scope"] == "group"
    assert group_payload["group_label"] == "train"
    assert group_payload["selection_summary"]["count"] == 3
    assert group_payload["group_summary"]["label"] == "train"
    assert group_payload["group_summary"]["count"] == 3
    assert len(group_payload["entries"]) == 3
    group_jsonl_rows = [json.loads(line) for line in Path(group_export["jsonl_path"]).read_text(encoding="utf-8").splitlines()]
    assert [row["draft_case"]["case_id"] for row in group_jsonl_rows] == [
        "finance_draft_review_471",
        "finance_draft_review_472",
        "finance_draft_review_474",
    ]


def test_write_draft_export_manifest_indexes_existing_packets(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high", "mega"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_rows = [
        {
            "case_id": "finance_draft_review_481",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_482",
            "input_features": {"transaction_amount": "mega"},
            "expected_action_id": None,
            "supported": False,
            "ood": True,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
    ]
    (drafts_dir / "review_cases.jsonl").write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    export_selected_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_filter="all",
        draft_sort="queue",
    )
    export_selected_draft_cases(
        repo_root=tmp_path,
        domain="finance",
        target="review",
        draft_filter="all",
        draft_sort="target",
        group_label="eval",
    )

    manifest_result = write_draft_export_manifest(tmp_path)
    manifest_path = Path(manifest_result["path"])
    markdown_path = Path(manifest_result["markdown_path"])
    assert manifest_path.exists()
    assert markdown_path.exists()
    assert manifest_result["export_count"] == 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["export_root"] == "kvrm-bench/results/draft_exports"
    assert manifest["export_count"] == 2
    assert manifest["domain_counts"] == [{"domain": "finance", "export_count": 2}]
    assert manifest["target_counts"] == [{"domain": "finance", "target": "review", "export_count": 2}]
    assert [item["scope"] for item in manifest["exports"]] == ["slice", "group"]
    assert manifest["exports"][0]["json_path"].endswith(
        "kvrm-bench/results/draft_exports/finance/review/finance_review_filter-all_sort-queue_scope-slice.json"
    )
    assert manifest["exports"][1]["json_path"].endswith(
        "kvrm-bench/results/draft_exports/finance/review/finance_review_filter-all_sort-target_scope-group-eval.json"
    )
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# KVRM Draft Export Manifest" in markdown
    assert "| finance | review | 2 |" in markdown
    assert "`kvrm-bench/results/draft_exports/finance/review/finance_review_filter-all_sort-queue_scope-slice.json`" in markdown


def test_export_draft_case_bundle_writes_slice_group_packets_and_manifest(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high", "mega"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_rows = [
        {
            "case_id": "finance_draft_review_491",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_492",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_493",
            "input_features": {"transaction_amount": "mega"},
            "expected_action_id": None,
            "supported": False,
            "ood": True,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
    ]
    (drafts_dir / "review_cases.jsonl").write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    bundle = export_draft_case_bundle(
        repo_root=tmp_path,
        domains=["finance"],
        targets=["review", "eval"],
        draft_filters=["all"],
        draft_sorts=["queue", "target"],
        include_group_exports=True,
    )

    assert bundle["export_count"] == 4
    assert bundle["slice_export_count"] == 2
    assert bundle["group_export_count"] == 2
    assert bundle["selection_count_total"] == 9
    assert bundle["skipped_count"] == 2
    assert bundle["manifest_export_count"] == 4
    assert [item["reason"] for item in bundle["skipped"]] == ["no_matching_cases", "no_matching_cases"]
    assert {item["scope"] for item in bundle["exports"]} == {"slice", "group"}
    assert Path(bundle["manifest_path"]).exists()
    assert Path(bundle["manifest_markdown_path"]).exists()

    exported_json_paths = {Path(item["json_path"]).name for item in bundle["exports"]}
    assert exported_json_paths == {
        "finance_review_filter-all_sort-queue_scope-slice.json",
        "finance_review_filter-all_sort-target_scope-slice.json",
        "finance_review_filter-all_sort-target_scope-group-train.json",
        "finance_review_filter-all_sort-target_scope-group-eval.json",
    }

    manifest = json.loads(Path(bundle["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["export_count"] == 4
    assert manifest["domain_counts"] == [{"domain": "finance", "export_count": 4}]
    assert manifest["target_counts"] == [{"domain": "finance", "target": "review", "export_count": 4}]


def test_build_draft_case_queue_filters_status_and_blocked_cases(tmp_path: Path) -> None:
    data_dir = tmp_path / "kvrm-demos" / "finance-risk-router" / "data"
    drafts_dir = data_dir / "drafts"
    drafts_dir.mkdir(parents=True)
    (data_dir / "registry.json").write_text(
        json.dumps(
            {
                "registry_name": "finance-risk-router",
                "version": "1.1.0",
                "required_features": ["transaction_amount"],
                "context_schema": {
                    "transaction_amount": {"type": "string", "enum": ["high"]},
                },
                "actions": [
                    {
                        "action_id": "manual_review",
                        "name": "Manual Review",
                        "description": "Fallback",
                        "parameters_schema": {"type": "object", "properties": {}, "required": []},
                        "support_spec": {"all": [{"feature": "transaction_amount", "op": "eq", "value": "high"}]},
                        "tags": ["fallback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "train_cases.jsonl").write_text("", encoding="utf-8")
    (data_dir / "cases.jsonl").write_text("", encoding="utf-8")

    review_rows = [
        {
            "case_id": "finance_draft_review_201",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_202",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "pending"},
        },
        {
            "case_id": "finance_draft_review_203",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "unknown_action",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
        {
            "case_id": "finance_draft_review_204",
            "input_features": {"transaction_amount": "high"},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "promoted_train"},
        },
        {
            "case_id": "finance_draft_review_205",
            "input_features": {},
            "expected_action_id": "manual_review",
            "supported": True,
            "ood": False,
            "draft_meta": {"target_split": "review", "review_status": "reviewed"},
        },
    ]
    (drafts_dir / "review_cases.jsonl").write_text(
        "\n".join(json.dumps(row) for row in review_rows) + "\n",
        encoding="utf-8",
    )

    promotable_queue = build_draft_case_queue(tmp_path, "finance", "review", draft_filter="promotable")
    assert [row["draft_case"]["case_id"] for row in promotable_queue] == ["finance_draft_review_201"]
    assert promotable_queue[0]["draft_index"] == 0

    blocked_queue = build_draft_case_queue(tmp_path, "finance", "review", draft_filter="blocked")
    assert [row["draft_case"]["case_id"] for row in blocked_queue] == [
        "finance_draft_review_203",
        "finance_draft_review_205",
    ]
    assert blocked_queue[0]["draft_index"] == 2
    assert blocked_queue[0]["primary_diagnostic"]["code"] == "unknown_expected_action"
    assert blocked_queue[1]["primary_diagnostic"]["code"] == "empty_context"

    diagnostic_queue = build_draft_case_queue(
        tmp_path,
        "finance",
        "review",
        draft_filter="blocked",
        draft_sort="diagnostic",
    )
    assert [row["draft_case"]["case_id"] for row in diagnostic_queue] == [
        "finance_draft_review_205",
        "finance_draft_review_203",
    ]

    status_queue = build_draft_case_queue(
        tmp_path,
        "finance",
        "review",
        draft_filter="all",
        draft_sort="status",
    )
    assert [row["draft_case"]["case_id"] for row in status_queue] == [
        "finance_draft_review_202",
        "finance_draft_review_201",
        "finance_draft_review_205",
        "finance_draft_review_203",
        "finance_draft_review_204",
    ]

    pending_queue = build_draft_case_queue(tmp_path, "finance", "review", draft_filter="pending")
    assert [row["draft_case"]["case_id"] for row in pending_queue] == ["finance_draft_review_202"]

    promoted_queue = build_draft_case_queue(tmp_path, "finance", "review", draft_filter="promoted")
    assert [row["draft_case"]["case_id"] for row in promoted_queue] == ["finance_draft_review_204"]

    next_group = find_adjacent_draft_group_index(
        tmp_path,
        "finance",
        "review",
        draft_index=0,
        draft_filter="blocked",
        draft_sort="diagnostic",
        step=1,
    )
    assert next_group == {
        "draft_index": 1,
        "group_label": "unknown_expected_action",
        "group_count": 1,
    }

    previous_group = find_adjacent_draft_group_index(
        tmp_path,
        "finance",
        "review",
        draft_index=1,
        draft_filter="all",
        draft_sort="status",
        step=-1,
    )
    assert previous_group == {
        "draft_index": 0,
        "group_label": "pending",
        "group_count": 1,
    }

    diagnostic_summary = summarize_draft_group(
        tmp_path,
        "finance",
        "review",
        draft_filter="blocked",
        draft_sort="diagnostic",
        group_label="unknown_expected_action",
    )
    assert diagnostic_summary == {
        "label": "unknown_expected_action",
        "count": 1,
        "supported_count": 1,
        "unsupported_count": 0,
        "ood_count": 0,
        "review_status_counts": [{"label": "reviewed", "count": 1}],
        "recommended_target_counts": [{"label": "unassigned", "count": 1}],
        "diagnostic_counts": [{"label": "unknown_expected_action", "count": 1}],
        "expected_action_counts": [{"label": "unknown_action", "count": 1}],
        "proposed_action_counts": [{"label": "none", "count": 1}],
        "diagnostic_feature_counts": [],
    }
