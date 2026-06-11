from __future__ import annotations

import importlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.context_schema import build_registry_unsupported_predicate, evaluate_registry_context
from kvrm_core.registry import load_registry
from kvrm_core.types import DecisionCandidate, DecisionInput
from kvrm_core.validation import DeterministicValidator

from .counterfactual import DEFAULT_CASE_PACK_DIR_NAME, load_or_generate_boundary_counterfactual_cases
from .demo import DOMAIN_CONFIG, STRATEGY_ORDER, _cached_runtime_for_strategy, load_cases
from .metrics import DEFAULT_DECISION_COSTS, DEFAULT_REGRET_COSTS, compute_metrics, compute_regret_metrics
from .temporal import _decision_to_case_result, _is_safe_reject, _outcome_score, _resolve_learned_model_path

DEFAULT_REPLAY_THRESHOLD = 0.60
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_REPORT_JSON = "incident_replay_report.json"
DEFAULT_REPORT_MD = "incident_replay_report.md"
DEFAULT_EPISODES_JSON = "incident_replay_episodes.json"
AUTHORED_REPLAY_EPISODES_FILE = "replay_episodes.json"

EPISODE_TYPE_ORDER = (
    "switch_fail_closed_recover",
    "fail_closed_recover_stabilize",
)


def generate_incident_replay_episodes(
    *,
    repo_root: str | Path,
    domain: str,
    artifact_dir: str | Path | None = None,
    refresh_counterfactual_cases: bool = False,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported replay domain: {domain}")

    results_dir = repo_root / DEFAULT_RESULTS_DIR if artifact_dir is None else Path(artifact_dir)
    counterfactual_case_dir = results_dir / DEFAULT_CASE_PACK_DIR_NAME
    counterfactual_payload = load_or_generate_boundary_counterfactual_cases(
        repo_root=repo_root,
        domain=domain,
        artifact_dir=counterfactual_case_dir,
        refresh=refresh_counterfactual_cases,
    )

    data_dir = repo_root / DOMAIN_CONFIG[domain]["data_dir"]
    registry = load_registry(data_dir / "registry.json")
    validator = DeterministicValidator(registry)
    selectors_module = importlib.import_module(DOMAIN_CONFIG[domain]["selectors_module"])
    unsupported_predicate = getattr(selectors_module, "_looks_unsupported", None)
    if unsupported_predicate is None:
        unsupported_predicate = build_registry_unsupported_predicate(registry)
    base_cases = {
        case["case_id"]: case
        for case in load_cases(data_dir / "cases.jsonl")
        if case.get("supported", True)
    }

    supported_switches: dict[str, list[dict[str, Any]]] = {}
    unsupported_cases: dict[str, list[dict[str, Any]]] = {}
    for case in counterfactual_payload["cases"]:
        base_case = base_cases.get(case["base_case_id"])
        if base_case is None:
            continue
        if not case.get("supported", True):
            unsupported_cases.setdefault(base_case["case_id"], []).append(case)
            continue
        if case.get("expected_action_id") != base_case.get("expected_action_id"):
            supported_switches.setdefault(base_case["case_id"], []).append(case)

    episodes: list[dict[str, Any]] = []
    episode_type_counts: Counter[str] = Counter()
    mutated_feature_counts: Counter[str] = Counter()
    event_kind_counts: Counter[str] = Counter()

    for base_case_id in sorted(base_cases):
        base_case = base_cases[base_case_id]
        unsupported_case = _representative_case(unsupported_cases.get(base_case_id, []))
        if unsupported_case is None:
            continue
        switch_case = _representative_case(supported_switches.get(base_case_id, []))
        if switch_case is not None:
            episode_type = "switch_fail_closed_recover"
            steps = [
                _event_step(base_case, minute_offset=0, event_kind="baseline", event_note="baseline supported operating state"),
                _event_step(
                    switch_case,
                    minute_offset=5,
                    event_kind="degradation_switch",
                    event_note="conditions change but a different supported action remains available",
                ),
                _event_step(
                    unsupported_case,
                    minute_offset=11,
                    event_kind="unsupported_checkpoint",
                    event_note="intermediate state leaves the audited action space and should fail closed",
                ),
                _event_step(
                    base_case,
                    minute_offset=19,
                    event_kind="recovery",
                    event_note="incident stabilizes and the original supported action becomes valid again",
                ),
            ]
            event_kind_counts.update(("baseline", "degradation_switch", "unsupported_checkpoint", "recovery"))
            episode_type_counts[episode_type] += 1
            mutated_feature_counts[switch_case["mutated_feature"]] += 1
            mutated_feature_counts[unsupported_case["mutated_feature"]] += 1
        else:
            episode_type = "fail_closed_recover_stabilize"
            steps = [
                _event_step(base_case, minute_offset=0, event_kind="baseline", event_note="baseline supported operating state"),
                _event_step(
                    unsupported_case,
                    minute_offset=7,
                    event_kind="unsupported_checkpoint",
                    event_note="the state leaves the audited action space and should fail closed",
                ),
                _event_step(
                    base_case,
                    minute_offset=15,
                    event_kind="recovery",
                    event_note="the system recovers back into a supported operating region",
                ),
                _event_step(
                    base_case,
                    minute_offset=27,
                    event_kind="stabilize",
                    event_note="the supported recovery action should remain stable at a later checkpoint",
                ),
            ]
            event_kind_counts.update(("baseline", "unsupported_checkpoint", "recovery", "stabilize"))
            episode_type_counts[episode_type] += 1
            mutated_feature_counts[unsupported_case["mutated_feature"]] += 1

        episodes.append(
            {
                "episode_id": f"{base_case_id}:{episode_type}",
                "episode_type": episode_type,
                "episode_source": "counterfactual_derived",
                "base_case_id": base_case_id,
                "switch_case_id": switch_case["case_id"] if switch_case is not None else None,
                "unsupported_case_id": unsupported_case["case_id"],
                "counterfactual_case_pack_path": counterfactual_payload["case_pack_path"],
                "counterfactual_case_pack_signature": counterfactual_payload["case_pack_signature"],
                "steps": steps,
            }
        )

    authored = _load_authored_replay_episodes(
        data_dir=data_dir,
        registry=registry,
        validator=validator,
        unsupported_predicate=unsupported_predicate,
    )
    episodes.extend(authored["episodes"])
    episode_type_counts.update(authored["episode_type_counts"])
    mutated_feature_counts.update(authored["driver_feature_counts"])
    event_kind_counts.update(authored["event_kind_counts"])

    source_counts = Counter(episode["episode_source"] for episode in episodes)

    return {
        "domain": domain,
        "source_supported_case_count": len(base_cases),
        "source_counterfactual_case_count": counterfactual_payload["generated_case_count"],
        "source_authored_episode_count": len(authored["episodes"]),
        "episode_count": len(episodes),
        "episode_type_counts": {
            episode_type: episode_type_counts.get(episode_type, 0)
            for episode_type in EPISODE_TYPE_ORDER
        },
        "episode_source_counts": dict(sorted(source_counts.items())),
        "event_kind_counts": dict(sorted(event_kind_counts.items())),
        "mutated_feature_counts": dict(sorted(mutated_feature_counts.items())),
        "counterfactual_case_pack_path": counterfactual_payload["case_pack_path"],
        "counterfactual_case_pack_signature": counterfactual_payload["case_pack_signature"],
        "counterfactual_case_pack_source": counterfactual_payload["case_pack_source"],
        "episodes": episodes,
    }


def run_incident_replay_benchmark(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_REPLAY_THRESHOLD,
    learned_model_paths: dict[str, str | Path] | None = None,
    output_dir: str | Path | None = None,
    refresh_counterfactual_cases: bool = False,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    active_domains = list(domains or DOMAIN_CONFIG.keys())
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "domains": {},
        "summary": {},
    }
    episodes_payload: dict[str, Any] = {}

    hybrid_wins = 0
    hybrid_ties = 0
    hybrid_losses = 0

    for domain in active_domains:
        episode_pack = generate_incident_replay_episodes(
            repo_root=repo_root,
            domain=domain,
            artifact_dir=results_dir,
            refresh_counterfactual_cases=refresh_counterfactual_cases,
        )
        episodes = episode_pack["episodes"]
        episodes_payload[domain] = episodes
        strategy_payloads: dict[str, dict[str, Any]] = {}
        learned_model_path = _resolve_learned_model_path(repo_root, domain, learned_model_paths)

        for strategy in STRATEGY_ORDER:
            runtime, _ = _cached_runtime_for_strategy(
                str(repo_root),
                domain,
                "cases.jsonl",
                strategy,
                str(learned_model_path) if learned_model_path is not None else None,
                threshold,
            )
            if runtime is None:
                continue

            step_case_results: list[dict[str, Any]] = []
            episode_results: list[dict[str, Any]] = []
            for episode in episodes:
                step_results: list[dict[str, Any]] = []
                for step_index, step in enumerate(episode["steps"], start=1):
                    case = step["case"]
                    decision = runtime.decide_and_execute(
                        DecisionInput(
                            case_id=case["case_id"],
                            features=case["input_features"],
                            supported=case.get("supported", True),
                            ood=case.get("ood", False),
                            expected_action_id=case.get("expected_action_id"),
                        )
                    )
                    case_result = _decision_to_case_result(case, decision.model_dump(mode="json"))
                    case_result["step_index"] = step_index
                    case_result["episode_id"] = episode["episode_id"]
                    case_result["episode_type"] = episode["episode_type"]
                    case_result["minute_offset"] = step["minute_offset"]
                    case_result["event_kind"] = step["event_kind"]
                    case_result["event_note"] = step["event_note"]
                    step_case_results.append(case_result)
                    step_results.append(case_result)
                episode_results.append(_evaluate_episode(episode, step_results))

            strategy_payloads[strategy] = {
                "episode_count": len(episode_results),
                "step_case_count": len(step_case_results),
                "metrics": compute_metrics(step_case_results),
                "regret": compute_regret_metrics(step_case_results),
                "episode_metrics": compute_incident_replay_metrics(episode_results),
                "episode_metrics_by_source": compute_incident_replay_metrics_by_source(episode_results),
            }

        best_non_hybrid_strategy = _best_non_hybrid_strategy(strategy_payloads)
        hybrid_payload = strategy_payloads["hybrid"]
        baseline_payload = strategy_payloads[best_non_hybrid_strategy]
        hybrid_episode_regret = hybrid_payload["episode_metrics"]["mean_episode_regret"]
        baseline_episode_regret = baseline_payload["episode_metrics"]["mean_episode_regret"]
        if hybrid_episode_regret < baseline_episode_regret:
            hybrid_wins += 1
        elif hybrid_episode_regret > baseline_episode_regret:
            hybrid_losses += 1
        else:
            hybrid_ties += 1

        payload["domains"][domain] = {
            **{key: value for key, value in episode_pack.items() if key != "episodes"},
            "strategies": strategy_payloads,
            "comparison": {
                "best_non_hybrid_strategy": best_non_hybrid_strategy,
                "hybrid_episode_regret_gain": baseline_episode_regret - hybrid_episode_regret,
                "hybrid_episode_cost_reduction": (
                    baseline_payload["episode_metrics"]["mean_episode_cost"]
                    - hybrid_payload["episode_metrics"]["mean_episode_cost"]
                ),
                "hybrid_episode_success_gain": (
                    hybrid_payload["episode_metrics"]["episode_success_rate"]
                    - baseline_payload["episode_metrics"]["episode_success_rate"]
                ),
                "hybrid_fail_closed_checkpoint_gain": (
                    hybrid_payload["episode_metrics"]["fail_closed_checkpoint_success_rate"]
                    - baseline_payload["episode_metrics"]["fail_closed_checkpoint_success_rate"]
                ),
            },
        }

    payload["summary"] = {
        "domain_count": len(active_domains),
        "hybrid_win_count": hybrid_wins,
        "hybrid_tie_count": hybrid_ties,
        "hybrid_loss_count": hybrid_losses,
    }
    report_paths = write_incident_replay_reports(payload, episodes_payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    payload["episodes_json"] = str(report_paths["episodes"])
    return payload


def compute_incident_replay_metrics(episode_results: list[dict[str, Any]]) -> dict[str, float]:
    def rate(items: list[dict[str, Any]], pred) -> float:
        if not items:
            return 0.0
        return sum(1 for item in items if pred(item)) / len(items)

    def mean(items: list[dict[str, Any]], key: str) -> float:
        if not items:
            return 0.0
        return sum(float(item[key]) for item in items) / len(items)

    def subset(episode_type: str) -> list[dict[str, Any]]:
        return [item for item in episode_results if item["episode_type"] == episode_type]

    switch_episodes = subset("switch_fail_closed_recover")
    stabilize_episodes = subset("fail_closed_recover_stabilize")

    return {
        "mean_episode_regret": mean(episode_results, "episode_regret"),
        "mean_episode_cost": mean(episode_results, "episode_cost"),
        "all_steps_success_rate": rate(episode_results, lambda item: bool(item["all_steps_success"])),
        "episode_success_rate": rate(episode_results, lambda item: bool(item["episode_success"])),
        "fail_closed_checkpoint_success_rate": rate(
            episode_results,
            lambda item: bool(item["fail_closed_checkpoint_success"]),
        ),
        "recovery_terminal_success_rate": rate(
            episode_results,
            lambda item: bool(item["recovery_terminal_success"]),
        ),
        "action_change_success_rate": rate(
            switch_episodes,
            lambda item: bool(item["action_change_success"]),
        ),
        "stabilization_success_rate": rate(
            stabilize_episodes,
            lambda item: bool(item["stabilization_success"]),
        ),
        "any_fallback_rate": rate(episode_results, lambda item: bool(item["any_fallback_used"])),
        "any_invalid_output_rate": rate(episode_results, lambda item: bool(item["any_invalid_output"])),
    }


def compute_incident_replay_metrics_by_source(
    episode_results: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    sources = sorted({str(item.get("episode_source", "unknown")) for item in episode_results})
    return {
        source: compute_incident_replay_metrics(
            [item for item in episode_results if str(item.get("episode_source", "unknown")) == source]
        )
        for source in sources
    }


def render_incident_replay_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Incident Replay Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "This replay-style benchmark converts live counterfactual boundary cases into timestamped event-log "
            "episodes so the runtime is evaluated as an incident progresses rather than only on isolated snapshots."
        ),
        "",
        (
            "Each episode contains baseline operation, a possible supported action switch, an unsupported checkpoint "
            "that should fail closed, and a recovery or stabilization checkpoint."
        ),
        "",
        (
            f"Hybrid comparison summary: wins={payload['summary']['hybrid_win_count']}, "
            f"ties={payload['summary']['hybrid_tie_count']}, "
            f"losses={payload['summary']['hybrid_loss_count']}."
        ),
        "",
        "| Domain | Episodes | Switch->Fail->Recover | Fail->Recover->Stabilize | Hybrid Episode Success | Hybrid Episode Regret | Best Non-Hybrid | Baseline Episode Regret | Gain |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]

    for domain, domain_payload in payload["domains"].items():
        hybrid = domain_payload["strategies"]["hybrid"]
        baseline_name = domain_payload["comparison"]["best_non_hybrid_strategy"]
        baseline = domain_payload["strategies"][baseline_name]
        source_metrics = hybrid.get("episode_metrics_by_source", {})
        lines.append(
            "| "
            f"{domain} | "
            f"{domain_payload['episode_count']} | "
            f"{domain_payload['episode_type_counts']['switch_fail_closed_recover']} | "
            f"{domain_payload['episode_type_counts']['fail_closed_recover_stabilize']} | "
            f"{hybrid['episode_metrics']['episode_success_rate']:.4f} | "
            f"{hybrid['episode_metrics']['mean_episode_regret']:.4f} | "
            f"{baseline_name} | "
            f"{baseline['episode_metrics']['mean_episode_regret']:.4f} | "
            f"{domain_payload['comparison']['hybrid_episode_regret_gain']:.4f} |"
        )
        lines.append(
            f"Events `{domain}`: "
            + ", ".join(
                f"{event_kind}={count}"
                for event_kind, count in domain_payload["event_kind_counts"].items()
            )
        )
        lines.append(
            f"Sources `{domain}`: "
            + ", ".join(
                f"{source}={count}"
                for source, count in domain_payload["episode_source_counts"].items()
            )
        )
        if source_metrics:
            lines.append(
                f"Hybrid Replay Slices `{domain}`: "
                + "; ".join(
                    (
                        f"{source}"
                        f" success={metrics['episode_success_rate']:.4f}"
                        f" regret={metrics['mean_episode_regret']:.4f}"
                        f" fail_closed={metrics['fail_closed_checkpoint_success_rate']:.4f}"
                    )
                    for source, metrics in source_metrics.items()
                )
            )
        lines.append(
            f"Features `{domain}`: "
            + ", ".join(
                f"{feature}={count}"
                for feature, count in domain_payload["mutated_feature_counts"].items()
            )
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_incident_replay_reports(
    payload: dict[str, Any],
    episodes_payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / DEFAULT_REPORT_JSON
    report_md = output_dir / DEFAULT_REPORT_MD
    episodes_json = output_dir / DEFAULT_EPISODES_JSON
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_incident_replay_markdown(payload), encoding="utf-8")
    episodes_json.write_text(json.dumps(episodes_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"json": report_json, "md": report_md, "episodes": episodes_json}


def _event_step(case: dict[str, Any], *, minute_offset: int, event_kind: str, event_note: str) -> dict[str, Any]:
    return {
        "minute_offset": minute_offset,
        "event_kind": event_kind,
        "event_note": event_note,
        "case": dict(case),
    }


def _evaluate_episode(episode: dict[str, Any], step_results: list[dict[str, Any]]) -> dict[str, Any]:
    if len(step_results) != 4:
        raise ValueError("incident replay benchmark expects exactly four steps per episode")

    episode_type = episode["episode_type"]
    all_steps_success = all(_step_success(step_result) for step_result in step_results)
    fail_closed_checkpoint_success = _is_safe_reject(step_results[2 if episode_type == "switch_fail_closed_recover" else 1])
    recovery_terminal_success = bool(step_results[3 if episode_type == "switch_fail_closed_recover" else 2].get("correct", False))
    action_change_success = False
    stabilization_success = False

    if episode_type == "switch_fail_closed_recover":
        action_change_success = (
            bool(step_results[1].get("correct", False))
            and step_results[0].get("selected_action_id") != step_results[1].get("selected_action_id")
        )
        episode_success = (
            bool(step_results[0].get("correct", False))
            and action_change_success
            and _is_safe_reject(step_results[2])
            and bool(step_results[3].get("correct", False))
            and step_results[3].get("selected_action_id") == step_results[0].get("selected_action_id")
        )
    elif episode_type == "fail_closed_recover_stabilize":
        stabilization_success = (
            bool(step_results[2].get("correct", False))
            and bool(step_results[3].get("correct", False))
            and step_results[2].get("selected_action_id") == step_results[3].get("selected_action_id")
        )
        episode_success = (
            bool(step_results[0].get("correct", False))
            and _is_safe_reject(step_results[1])
            and bool(step_results[2].get("correct", False))
            and stabilization_success
        )
    else:
        raise ValueError(f"unsupported replay episode type: {episode_type}")

    return {
        "episode_id": episode["episode_id"],
        "episode_type": episode_type,
        "episode_source": episode.get("episode_source", "unknown"),
        "episode_regret": sum(_regret_score(step_result) for step_result in step_results),
        "episode_cost": sum(_decision_cost(step_result) for step_result in step_results),
        "all_steps_success": all_steps_success,
        "episode_success": episode_success,
        "fail_closed_checkpoint_success": fail_closed_checkpoint_success,
        "recovery_terminal_success": recovery_terminal_success,
        "action_change_success": action_change_success,
        "stabilization_success": stabilization_success,
        "any_fallback_used": any(bool(step_result.get("fallback_used", False)) for step_result in step_results),
        "any_invalid_output": any(not bool(step_result.get("valid", False)) for step_result in step_results),
    }


def _step_success(step_result: dict[str, Any]) -> bool:
    if bool(step_result.get("supported", True)):
        return bool(step_result.get("correct", False))
    return _is_safe_reject(step_result)


def _decision_cost(case_result: dict[str, Any]) -> float:
    return _outcome_score(case_result, DEFAULT_DECISION_COSTS)


def _regret_score(case_result: dict[str, Any]) -> float:
    return _outcome_score(case_result, DEFAULT_REGRET_COSTS)


def _best_non_hybrid_strategy(strategy_payloads: dict[str, dict[str, Any]]) -> str:
    non_hybrid = {
        strategy: payload
        for strategy, payload in strategy_payloads.items()
        if strategy != "hybrid"
    }
    if not non_hybrid:
        raise ValueError("incident replay benchmark requires at least one non-hybrid strategy")
    return min(
        non_hybrid,
        key=lambda strategy: (
            non_hybrid[strategy]["episode_metrics"]["mean_episode_regret"],
            non_hybrid[strategy]["episode_metrics"]["mean_episode_cost"],
            -non_hybrid[strategy]["episode_metrics"]["episode_success_rate"],
        ),
    )


def _representative_case(cases: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not cases:
        return None
    return min(
        cases,
        key=lambda case: (
            case["mutated_feature"],
            case["case_id"],
        ),
    )


def _load_authored_replay_episodes(
    *,
    data_dir: Path,
    registry,
    validator: DeterministicValidator,
    unsupported_predicate,
) -> dict[str, Any]:
    path = data_dir / AUTHORED_REPLAY_EPISODES_FILE
    if not path.exists():
        return {
            "episodes": [],
            "episode_type_counts": Counter(),
            "driver_feature_counts": Counter(),
            "event_kind_counts": Counter(),
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_episodes = payload.get("episodes")
    if not isinstance(raw_episodes, list):
        raise ValueError(f"{path} must contain an 'episodes' list")

    episodes: list[dict[str, Any]] = []
    episode_type_counts: Counter[str] = Counter()
    driver_feature_counts: Counter[str] = Counter()
    event_kind_counts: Counter[str] = Counter()
    seen_episode_ids: set[str] = set()

    for raw_episode in raw_episodes:
        episode = _normalize_authored_episode(
            raw_episode=raw_episode,
            registry=registry,
            validator=validator,
            unsupported_predicate=unsupported_predicate,
        )
        episode_id = episode["episode_id"]
        if episode_id in seen_episode_ids:
            raise ValueError(f"duplicate authored replay episode_id: {episode_id}")
        seen_episode_ids.add(episode_id)
        episodes.append(episode)
        episode_type_counts[episode["episode_type"]] += 1
        driver_feature_counts.update(episode.get("driver_features", []))
        event_kind_counts.update(step["event_kind"] for step in episode["steps"])

    return {
        "episodes": episodes,
        "episode_type_counts": episode_type_counts,
        "driver_feature_counts": driver_feature_counts,
        "event_kind_counts": event_kind_counts,
    }


def _normalize_authored_episode(
    *,
    raw_episode: dict[str, Any],
    registry,
    validator: DeterministicValidator,
    unsupported_predicate,
) -> dict[str, Any]:
    episode_id = raw_episode.get("episode_id")
    episode_type = raw_episode.get("episode_type")
    if not isinstance(episode_id, str) or not episode_id:
        raise ValueError("authored replay episode requires a non-empty episode_id")
    if episode_type not in EPISODE_TYPE_ORDER:
        raise ValueError(f"unsupported authored replay episode_type: {episode_type!r}")

    raw_steps = raw_episode.get("steps")
    if not isinstance(raw_steps, list) or len(raw_steps) != 4:
        raise ValueError(f"authored replay episode {episode_id} must have exactly four steps")

    driver_features = raw_episode.get("driver_features") or []
    if not isinstance(driver_features, list) or any(not isinstance(item, str) or not item for item in driver_features):
        raise ValueError(f"authored replay episode {episode_id} has invalid driver_features")

    steps: list[dict[str, Any]] = []
    last_minute_offset = -1
    for index, raw_step in enumerate(raw_steps, start=1):
        step = _normalize_authored_step(
            raw_step=raw_step,
            episode_id=episode_id,
            step_index=index,
            registry=registry,
            validator=validator,
            unsupported_predicate=unsupported_predicate,
        )
        if step["minute_offset"] <= last_minute_offset:
            raise ValueError(f"authored replay episode {episode_id} must use strictly increasing minute_offset values")
        last_minute_offset = step["minute_offset"]
        steps.append(step)

    return {
        "episode_id": episode_id,
        "episode_type": episode_type,
        "episode_source": "authored",
        "episode_note": raw_episode.get("episode_note"),
        "driver_features": driver_features,
        "steps": steps,
    }


def _normalize_authored_step(
    *,
    raw_step: dict[str, Any],
    episode_id: str,
    step_index: int,
    registry,
    validator: DeterministicValidator,
    unsupported_predicate,
) -> dict[str, Any]:
    minute_offset = raw_step.get("minute_offset")
    event_kind = raw_step.get("event_kind")
    event_note = raw_step.get("event_note")
    case = raw_step.get("case")

    if type(minute_offset) is not int:
        raise ValueError(f"authored replay episode {episode_id} step {step_index} requires integer minute_offset")
    if not isinstance(event_kind, str) or not event_kind:
        raise ValueError(f"authored replay episode {episode_id} step {step_index} requires event_kind")
    if not isinstance(event_note, str) or not event_note:
        raise ValueError(f"authored replay episode {episode_id} step {step_index} requires event_note")
    if not isinstance(case, dict):
        raise ValueError(f"authored replay episode {episode_id} step {step_index} requires a case object")

    case_id = case.get("case_id")
    features = case.get("input_features")
    supported = bool(case.get("supported", True))
    ood = bool(case.get("ood", True))
    expected_action_id = case.get("expected_action_id")
    expected_parameters = case.get("expected_parameters")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError(f"authored replay episode {episode_id} step {step_index} requires case_id")
    if not isinstance(features, dict) or not features:
        raise ValueError(f"authored replay episode {episode_id} step {step_index} requires input_features")
    if expected_parameters is None:
        expected_parameters = {}
    if not isinstance(expected_parameters, dict):
        raise ValueError(
            f"authored replay episode {episode_id} step {step_index} expected_parameters must be an object when provided"
        )

    context_valid, context_reason = evaluate_registry_context(registry, features)
    looks_unsupported = unsupported_predicate(features)
    if supported:
        if expected_action_id is None:
            raise ValueError(f"authored replay episode {episode_id} step {step_index} supported cases require expected_action_id")
        if not context_valid:
            raise ValueError(
                f"authored replay episode {episode_id} step {step_index} supported case violates context schema: {context_reason}"
            )
        if looks_unsupported:
            raise ValueError(
                f"authored replay episode {episode_id} step {step_index} supported case is marked unsupported by the live predicate"
            )
        validation = validator.validate(
            DecisionCandidate(
                action_id=expected_action_id,
                confidence=1.0,
                parameters=expected_parameters,
            ),
            features,
        )
        if not validation.valid:
            raise ValueError(
                f"authored replay episode {episode_id} step {step_index} expected action {expected_action_id!r} is not supported: {validation.reason}"
            )
    else:
        if expected_action_id is not None:
            raise ValueError(
                f"authored replay episode {episode_id} step {step_index} unsupported cases must use expected_action_id=null"
            )
        if expected_parameters:
            raise ValueError(
                f"authored replay episode {episode_id} step {step_index} unsupported cases must not define expected_parameters"
            )
        if not looks_unsupported and _supported_non_fallback_action_ids(
            registry=registry,
            validator=validator,
            features=features,
        ):
            raise ValueError(
                f"authored replay episode {episode_id} step {step_index} unsupported case is still supportable under the live predicate"
            )

    return {
        "minute_offset": minute_offset,
        "event_kind": event_kind,
        "event_note": event_note,
        "case": {
            "case_id": case_id,
            "expected_action_id": expected_action_id,
            "expected_parameters": expected_parameters,
            "input_features": features,
            "supported": supported,
            "ood": ood,
        },
    }


def _supported_non_fallback_action_ids(*, registry, validator: DeterministicValidator, features: dict[str, Any]) -> list[str]:
    action_ids: list[str] = []
    for action in registry.actions:
        if "fallback" in action.tags:
            continue
        validation = validator.validate(
            DecisionCandidate(
                action_id=action.action_id,
                confidence=1.0,
                parameters=_probe_parameters_for_action(action),
            ),
            features,
        )
        if validation.valid:
            action_ids.append(action.action_id)
    return action_ids


def _probe_parameters_for_action(action) -> dict[str, Any]:
    schema = action.parameters_schema or {}
    properties = schema.get("properties", {}) or {}
    parameters: dict[str, Any] = {}
    for key in schema.get("required", []) or []:
        spec = properties.get(key, {})
        enum_values = spec.get("enum")
        if isinstance(enum_values, list) and enum_values:
            parameters[key] = enum_values[0]
            continue
        value_type = spec.get("type")
        if value_type == "boolean":
            parameters[key] = False
        elif value_type in {"integer", "number"}:
            minimum = spec.get("minimum")
            parameters[key] = minimum if minimum is not None else 0
        elif value_type == "array":
            parameters[key] = []
        elif value_type == "object":
            parameters[key] = {}
        else:
            parameters[key] = f"{action.action_id}_{key}"
    return parameters
