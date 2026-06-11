from __future__ import annotations

import json

from kvrm_core.artifacts import write_run_artifacts


def test_artifact_directory_and_files_are_created(tmp_path):
    write_run_artifacts(
        tmp_path,
        config={"run_name": "toy"},
        registry={"registry_name": "toy"},
        metrics={"structural_validity_rate": 1.0},
        cases=[{"case_id": "c1"}],
        summary_markdown="# Summary\n",
    )
    for name in ["config.json", "registry.json", "metrics.json", "per_case_results.jsonl", "summary.md"]:
        assert (tmp_path / name).exists()
    assert json.loads((tmp_path / "config.json").read_text())["run_name"] == "toy"
