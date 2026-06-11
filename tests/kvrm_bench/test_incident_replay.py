from __future__ import annotations

from pathlib import Path

from kvrm_bench.demo import clear_demo_caches
from kvrm_bench.incident_replay import (
    generate_incident_replay_episodes,
    run_incident_replay_benchmark,
)

ROOT = Path(__file__).resolve().parents[2]


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
        "kvrm-demos/iam-access-router",
    ):
        monkeypatch.syspath_prepend(str(ROOT / rel))


def test_generate_finance_replay_episodes_include_timestamps_and_event_kinds(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = generate_incident_replay_episodes(
        repo_root=ROOT,
        domain="finance",
    )

    assert payload["episode_count"] > 0
    assert payload["source_authored_episode_count"] == 4
    assert payload["episode_source_counts"]["authored"] == 4
    assert sum(payload["episode_type_counts"].values()) == payload["episode_count"]
    episode = payload["episodes"][0]
    assert len(episode["steps"]) == 4
    assert episode["steps"][0]["minute_offset"] == 0
    assert episode["steps"][1]["minute_offset"] > episode["steps"][0]["minute_offset"]
    assert "event_kind" in episode["steps"][2]
    assert "event_note" in episode["steps"][3]


def test_incident_replay_benchmark_finance_generates_artifacts(monkeypatch, tmp_path: Path) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = run_incident_replay_benchmark(
        repo_root=ROOT,
        domains=["finance"],
        output_dir=tmp_path,
    )

    finance_payload = payload["domains"]["finance"]
    comparison = finance_payload["comparison"]
    strategies = finance_payload["strategies"]
    best_non_hybrid = comparison["best_non_hybrid_strategy"]

    assert finance_payload["episode_count"] > 0
    assert strategies["hybrid"]["episode_metrics"]["fail_closed_checkpoint_success_rate"] == 1.0
    assert strategies["hybrid"]["episode_metrics"]["recovery_terminal_success_rate"] == 1.0
    assert strategies["hybrid"]["episode_metrics"]["mean_episode_regret"] <= strategies[best_non_hybrid]["episode_metrics"]["mean_episode_regret"]
    assert comparison["hybrid_fail_closed_checkpoint_gain"] >= 0.0
    assert (tmp_path / "incident_replay_report.json").exists()
    assert (tmp_path / "incident_replay_report.md").exists()
    assert (tmp_path / "incident_replay_episodes.json").exists()


def test_generate_iam_replay_episodes_include_authored_pack(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = generate_incident_replay_episodes(
        repo_root=ROOT,
        domain="iam",
    )

    assert payload["source_authored_episode_count"] == 4
    assert payload["episode_source_counts"]["authored"] == 4
    authored = [episode for episode in payload["episodes"] if episode["episode_source"] == "authored"]
    assert len(authored) == 4
    assert any("ticket_state" in episode.get("driver_features", []) for episode in authored)


def test_generate_sre_replay_episodes_include_authored_pack(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = generate_incident_replay_episodes(
        repo_root=ROOT,
        domain="sre",
    )

    assert payload["source_authored_episode_count"] == 4
    assert payload["episode_source_counts"]["authored"] == 4
    authored = [episode for episode in payload["episodes"] if episode["episode_source"] == "authored"]
    assert len(authored) == 4
    assert any("node_locality_score" in episode.get("driver_features", []) for episode in authored)


def test_generate_drone_replay_episodes_include_authored_pack(monkeypatch) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = generate_incident_replay_episodes(
        repo_root=ROOT,
        domain="drone",
    )

    assert payload["source_authored_episode_count"] == 4
    assert payload["episode_source_counts"]["authored"] == 4
    authored = [episode for episode in payload["episodes"] if episode["episode_source"] == "authored"]
    assert len(authored) == 4
    assert any("battery" in episode.get("driver_features", []) for episode in authored)
    assert any(
        step["case"].get("expected_action_id") == "manual_handoff"
        and step["case"].get("expected_parameters", {}).get("reason") == "high_threat_supervised_takeover"
        for episode in authored
        for step in episode["steps"]
    )


def test_incident_replay_benchmark_iam_authored_slice_is_safe(monkeypatch, tmp_path: Path) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = run_incident_replay_benchmark(
        repo_root=ROOT,
        domains=["iam"],
        output_dir=tmp_path,
    )

    iam_payload = payload["domains"]["iam"]
    hybrid = iam_payload["strategies"]["hybrid"]["episode_metrics"]

    assert iam_payload["source_authored_episode_count"] == 4
    assert iam_payload["episode_source_counts"]["authored"] == 4
    assert hybrid["fail_closed_checkpoint_success_rate"] == 1.0
    assert hybrid["episode_success_rate"] == 1.0


def test_incident_replay_benchmark_sre_authored_slice_is_safe(monkeypatch, tmp_path: Path) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = run_incident_replay_benchmark(
        repo_root=ROOT,
        domains=["sre"],
        output_dir=tmp_path,
    )

    sre_payload = payload["domains"]["sre"]
    hybrid = sre_payload["strategies"]["hybrid"]["episode_metrics"]

    assert sre_payload["source_authored_episode_count"] == 4
    assert sre_payload["episode_source_counts"]["authored"] == 4
    assert hybrid["fail_closed_checkpoint_success_rate"] == 1.0
    assert hybrid["episode_success_rate"] == 1.0


def test_incident_replay_benchmark_drone_authored_slice_is_safe(monkeypatch, tmp_path: Path) -> None:
    _prepend_demo_paths(monkeypatch)
    clear_demo_caches()

    payload = run_incident_replay_benchmark(
        repo_root=ROOT,
        domains=["drone"],
        output_dir=tmp_path,
    )

    drone_payload = payload["domains"]["drone"]
    hybrid = drone_payload["strategies"]["hybrid"]["episode_metrics"]
    authored = drone_payload["strategies"]["hybrid"]["episode_metrics_by_source"]["authored"]

    assert drone_payload["source_authored_episode_count"] == 4
    assert drone_payload["episode_source_counts"]["authored"] == 4
    assert hybrid["fail_closed_checkpoint_success_rate"] == 1.0
    assert authored["fail_closed_checkpoint_success_rate"] == 1.0
    assert authored["episode_success_rate"] == 1.0
