from __future__ import annotations

import os
from pathlib import Path

import kvrm_bench.operator_pipeline as operator_pipeline


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_operator_refresh_plan_for_focused_domain() -> None:
    steps = operator_pipeline.build_operator_refresh_plan(REPO_ROOT, domains=["finance"])

    assert [step.key for step in steps] == [
        "train:finance",
        "benchmark:finance",
        "compare",
    ]
    assert steps[0].label == "Train FINANCE compact model"
    assert steps[1].label == "Benchmark FINANCE demo"
    assert steps[0].command[:4] == ["python3", "train_kvrm_model.py", "--domain", "finance"]
    assert steps[1].command[-1].endswith("kvrm-demos/finance-risk-router/scripts/run_benchmark.py")
    assert steps[2].command == ["python3", "kvrm-demos/compare_demos.py"]


def test_resolve_operator_pipeline_domains_filters_ready_domains(monkeypatch) -> None:
    statuses = {
        "soc": "ready",
        "sre": "stale_artifact",
        "drone": "ready",
        "grid": "missing_artifact",
    }

    def _fake_summary(repo_root, domain):
        return {"status": statuses[domain]}

    monkeypatch.setattr(operator_pipeline, "load_domain_training_artifact_summary", _fake_summary)

    resolved = operator_pipeline.resolve_operator_pipeline_domains(
        REPO_ROOT,
        domains=["soc", "sre", "drone", "grid"],
        stale_only=True,
    )

    assert resolved == ["sre", "grid"]


def test_build_operator_environment_preserves_existing_pythonpath() -> None:
    env = operator_pipeline.build_operator_environment(REPO_ROOT, {"PATH": "x", "PYTHONPATH": "existing"})

    assert env["PYTHONPATH"] == "existing"
