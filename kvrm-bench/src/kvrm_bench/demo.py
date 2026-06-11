from __future__ import annotations

import importlib
import json
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.types import DecisionCandidate, DecisionInput
from kvrm_core.context_schema import evaluate_registry_context
from kvrm_core.validation import DeterministicValidator


DOMAIN_CONFIG = {
    "soc": {
        "data_dir": "kvrm-demos/soc-playbook-router/data",
        "selectors_module": "soc_playbook_router",
        "executor_module": "soc_playbook_router",
        "fallback_action_id": "request_human_triage",
    },
    "sre": {
        "data_dir": "kvrm-demos/sre-policy-router/data",
        "selectors_module": "sre_policy_router",
        "executor_module": "sre_policy_router",
        "fallback_action_id": "page_human_operator",
    },
    "drone": {
        "data_dir": "kvrm-demos/drone-mission-router/data",
        "selectors_module": "drone_mission_router",
        "executor_module": "drone_mission_router",
        "fallback_action_id": "manual_handoff",
    },
    "grid": {
        "data_dir": "kvrm-demos/grid-ops-router/data",
        "selectors_module": "grid_ops_router",
        "executor_module": "grid_ops_router",
        "fallback_action_id": "escalate_grid_supervisor",
    },
    "finance": {
        "data_dir": "kvrm-demos/finance-risk-router/data",
        "selectors_module": "finance_risk_router",
        "executor_module": "finance_risk_router",
        "fallback_action_id": "manual_review",
    },
    "medical": {
        "data_dir": "kvrm-demos/medical-workflow-router/data",
        "selectors_module": "medical_workflow_router",
        "executor_module": "medical_workflow_router",
        "fallback_action_id": "escalate_supervisor_review",
    },
    "iam": {
        "data_dir": "kvrm-demos/iam-access-router/data",
        "selectors_module": "iam_access_router",
        "executor_module": "iam_access_router",
        "fallback_action_id": "escalate_identity_admin",
    },
    "customer_support": {
        "data_dir": "kvrm-demos/customer-support-router/data",
        "selectors_module": "customer_support_router",
        "executor_module": "customer_support_router",
        "fallback_action_id": "request_human_review",
    },
    "content_moderation": {
        "data_dir": "kvrm-demos/content-moderation-router/data",
        "selectors_module": "content_moderation_router",
        "executor_module": "content_moderation_router",
        "fallback_action_id": "request_human_review",
    },
    "legal": {
        "data_dir": "kvrm-demos/legal-compliance-router/data",
        "selectors_module": "legal_compliance_router",
        "executor_module": "legal_compliance_router",
        "fallback_action_id": "escalate_to_counsel",
    },
    "cicd": {
        "data_dir": "kvrm-demos/cicd-pipeline-router/data",
        "selectors_module": "cicd_pipeline_router",
        "executor_module": "cicd_pipeline_router",
        "fallback_action_id": "escalate_to_oncall",
    },
    "insurance": {
        "data_dir": "kvrm-demos/insurance-claims-router/data",
        "selectors_module": "insurance_claims_router",
        "executor_module": "insurance_claims_router",
        "fallback_action_id": "escalate_to_supervisor",
    },
}

STRATEGY_ORDER = ("rule", "retrieval", "prototype", "semantic", "learned", "hybrid")
DRAFT_FILE_NAMES = {
    "review": "review_cases.jsonl",
    "train": "train_candidate_cases.jsonl",
    "eval": "eval_candidate_cases.jsonl",
}
DRAFT_FILTERS = ("all", "pending", "reviewed", "promotable", "blocked", "promoted")
DRAFT_SORTS = ("queue", "diagnostic", "status", "target")
INCIDENT_REPLAY_FILENAME = "kvrm-bench/results/incident_replay_episodes.json"
DEFAULT_DRAFT_EXPORT_MANIFEST_MD = "manifest.md"
_UNSET = object()


def load_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def available_demo_case_files(repo_root: str | Path, domain: str) -> list[str]:
    config = DOMAIN_CONFIG[domain]
    data_dir = Path(repo_root) / config["data_dir"]
    return ["cases.jsonl"] if (data_dir / "cases.jsonl").exists() else []


def _domain_paths(repo_root: str | Path, domain: str, eval_filename: str) -> dict[str, Path | str]:
    config = DOMAIN_CONFIG[domain]
    data_dir = Path(repo_root) / config["data_dir"]
    return {
        "registry": data_dir / "registry.json",
        "train_cases": data_dir / "train_cases.jsonl",
        "cases": data_dir / eval_filename,
        "selectors_module": config["selectors_module"],
        "executor_module": config["executor_module"],
        "fallback_action_id": config["fallback_action_id"],
    }


@lru_cache(maxsize=12)
def _cached_runtime_for_strategy(
    repo_root: str,
    domain: str,
    eval_filename: str,
    strategy: str,
    learned_model_path: str | None,
    threshold: float,
):
    config = _domain_paths(repo_root, domain, eval_filename)
    registry = load_registry(config["registry"])
    validator = DeterministicValidator(registry)
    selectors_module = importlib.import_module(config["selectors_module"])
    executor_module = importlib.import_module(config["executor_module"])
    executor = executor_module.build_executor()
    selector = _build_selector(
        selectors_module=selectors_module,
        strategy=strategy,
        train_cases_path=config["train_cases"],
        learned_model_path=learned_model_path,
    )
    if selector is None:
        return None, config
    return (
        KVRMRuntime(
            registry=registry,
            selector=selector,
            validator=validator,
            executor=executor,
            threshold=threshold,
            fallback_action_id=config["fallback_action_id"],
        ),
        config,
    )


def _build_selector(
    *,
    selectors_module,
    strategy: str,
    train_cases_path: Path,
    learned_model_path: str | None,
):
    if strategy == "rule":
        return selectors_module.build_rule_selector()
    if strategy == "retrieval":
        return selectors_module.build_retrieval_selector(train_cases_path)
    if strategy == "prototype":
        return selectors_module.build_prototype_selector(train_cases_path)
    if strategy == "semantic":
        return selectors_module.build_semantic_selector(train_cases_path)
    if strategy == "learned":
        if not learned_model_path or not Path(learned_model_path).exists():
            return None
        return selectors_module.build_learned_selector(train_cases_path, learned_model_path)
    if strategy == "hybrid":
        return selectors_module.build_hybrid_selector(
            train_cases_path,
            learned_model_path=learned_model_path,
        )
    raise ValueError(f"unsupported strategy: {strategy}")


@lru_cache(maxsize=4)
def _cached_incident_replay_payload(repo_root: str) -> dict[str, Any]:
    path = Path(repo_root) / INCIDENT_REPLAY_FILENAME
    if not path.exists():
        raise ValueError(f"incident replay artifact not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"incident replay artifact is malformed: {path}")
    return payload


def clear_demo_caches() -> None:
    _cached_runtime_for_strategy.cache_clear()
    _cached_review_queue.cache_clear()
    _cached_incident_replay_payload.cache_clear()
    _cached_training_artifact_summary.cache_clear()


def load_domain_artifact_summary(
    repo_root: str | Path,
    domain: str,
    *,
    eval_filename: str = "cases.jsonl",
) -> dict[str, Any]:
    config = _domain_paths(repo_root, domain, eval_filename)
    registry = load_registry(config["registry"])
    train_cases = load_cases(config["train_cases"])
    eval_cases = load_cases(config["cases"])
    supported_cases = sum(1 for row in eval_cases if row.get("supported", True))
    unsupported_cases = len(eval_cases) - supported_cases
    ood_supported_cases = sum(1 for row in eval_cases if row.get("supported", True) and row.get("ood", False))
    return {
        "domain": domain,
        "registry_name": registry.registry_name,
        "registry_version": registry.version,
        "registry_digest": registry.digest,
        "action_count": len(registry.actions),
        "required_feature_count": len(registry.required_features),
        "context_field_count": len(registry.context_schema),
        "train_case_count": len(train_cases),
        "eval_case_count": len(eval_cases),
        "supported_case_count": supported_cases,
        "unsupported_case_count": unsupported_cases,
        "ood_supported_case_count": ood_supported_cases,
        "registry_path": str(config["registry"]),
        "train_cases_path": str(config["train_cases"]),
        "eval_cases_path": str(config["cases"]),
        "draft_counts": load_draft_case_counts(repo_root, domain),
    }


@lru_cache(maxsize=24)
def _cached_training_artifact_summary(
    repo_root: str,
    domain: str,
) -> dict[str, Any]:
    config = _domain_paths(repo_root, domain, "cases.jsonl")
    registry = load_registry(config["registry"])
    train_cases = load_cases(config["train_cases"])
    eval_cases = load_cases(config["cases"])
    report_path = Path(repo_root) / "kvrm-bench" / "results" / f"{domain}_compact_training_report_v1.json"
    model_path = Path(repo_root) / "kvrm-models" / f"{domain}_compact_selector_v1.joblib"
    report_payload = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    metadata = report_payload.get("metadata") or {}

    registry_mtime = _path_mtime(config["registry"])
    train_cases_mtime = _path_mtime(config["train_cases"])
    eval_cases_mtime = _path_mtime(config["cases"])
    report_mtime = _path_mtime(report_path)
    model_mtime = _path_mtime(model_path)

    latest_model_source_mtime = _max_mtime(
        registry_mtime,
        train_cases_mtime,
    )
    latest_report_source_mtime = _max_mtime(
        latest_model_source_mtime,
        eval_cases_mtime,
    )

    report_domain_matches = bool(report_payload) and report_payload.get("domain") == domain
    reported_train_case_count = metadata.get("train_case_count")
    train_case_count_matches = (
        reported_train_case_count == len(train_cases)
        if reported_train_case_count is not None
        else False
    )
    registry_digest_matches = (
        metadata.get("registry_digest") == registry.digest
        if metadata.get("registry_digest") is not None
        else False
    )
    model_fresh = (
        model_mtime is not None
        and latest_model_source_mtime is not None
        and model_mtime >= latest_model_source_mtime
        and registry_digest_matches
        and train_case_count_matches
    )
    report_fresh = (
        report_mtime is not None
        and latest_report_source_mtime is not None
        and report_mtime >= latest_report_source_mtime
        and report_domain_matches
        and registry_digest_matches
        and train_case_count_matches
    )
    status = "ready"
    if not report_path.exists() or not model_path.exists():
        status = "missing_artifact"
    elif not report_domain_matches:
        status = "report_domain_mismatch"
    elif not registry_digest_matches:
        status = "registry_mismatch"
    elif not train_case_count_matches:
        status = "dataset_mismatch"
    elif not model_fresh or not report_fresh:
        status = "stale_artifact"

    return {
        "domain": domain,
        "registry_name": registry.registry_name,
        "registry_version": registry.version,
        "registry_digest": registry.digest,
        "registry_path": str(config["registry"]),
        "train_cases_path": str(config["train_cases"]),
        "eval_cases_path": str(config["cases"]),
        "report_path": str(report_path),
        "model_path": str(model_path),
        "report_exists": report_path.exists(),
        "model_exists": model_path.exists(),
        "report_domain_matches": report_domain_matches,
        "registry_digest_matches": registry_digest_matches,
        "train_case_count": len(train_cases),
        "reported_train_case_count": reported_train_case_count,
        "train_case_count_matches": train_case_count_matches,
        "eval_case_count": len(eval_cases),
        "model_size_bytes": model_path.stat().st_size if model_path.exists() else None,
        "registry_mtime": registry_mtime,
        "train_cases_mtime": train_cases_mtime,
        "eval_cases_mtime": eval_cases_mtime,
        "report_mtime": report_mtime,
        "model_mtime": model_mtime,
        "latest_model_source_mtime": latest_model_source_mtime,
        "latest_report_source_mtime": latest_report_source_mtime,
        "model_fresh": model_fresh,
        "report_fresh": report_fresh,
        "sources_newer_than_model": (
            latest_model_source_mtime is not None
            and model_mtime is not None
            and latest_model_source_mtime > model_mtime
        ),
        "sources_newer_than_report": (
            latest_report_source_mtime is not None
            and report_mtime is not None
            and latest_report_source_mtime > report_mtime
        ),
        "status": status,
        "recommended_action": None if status == "ready" else "rerun_refresh_pipeline",
        "metadata": metadata,
        "selector_only": report_payload.get("selector_only") or {},
        "hybrid_augmented": report_payload.get("hybrid_augmented") or {},
    }


def load_domain_training_artifact_summary(
    repo_root: str | Path,
    domain: str,
) -> dict[str, Any]:
    return _cached_training_artifact_summary(str(Path(repo_root)), domain)


def _decision_input_from_case(case: dict[str, Any]) -> DecisionInput:
    return DecisionInput(
        case_id=case["case_id"],
        features=case["input_features"],
        supported=case.get("supported", True),
        ood=case.get("ood", False),
        expected_action_id=case.get("expected_action_id"),
    )


def run_demo_case(
    *,
    repo_root: str | Path,
    domain: str,
    eval_filename: str,
    case_index: int,
    threshold: float = 0.60,
    learned_model_path: str | None = None,
) -> dict[str, Any]:
    runtime, config = _cached_runtime_for_strategy(
        str(Path(repo_root)),
        domain,
        eval_filename,
        "hybrid",
        learned_model_path,
        threshold,
    )
    if runtime is None:
        raise ValueError(f"hybrid selector unavailable for {domain}")
    cases = load_cases(config["cases"])
    if not cases:
        raise ValueError(f"no demo cases found in {config['cases']}")
    bounded_index = case_index % len(cases)
    case = cases[bounded_index]
    decision = runtime.decide_and_execute(_decision_input_from_case(case))
    return {
        "domain": domain,
        "eval_filename": eval_filename,
        "case_index": bounded_index,
        "case_count": len(cases),
        "case": case,
        "decision": json.loads(decision.model_dump_json()),
    }


def run_demo_case_matrix(
    *,
    repo_root: str | Path,
    domain: str,
    eval_filename: str,
    case_index: int,
    threshold: float = 0.60,
    learned_model_path: str | None = None,
) -> dict[str, Any]:
    config = _domain_paths(repo_root, domain, eval_filename)
    cases = load_cases(config["cases"])
    if not cases:
        raise ValueError(f"no demo cases found in {config['cases']}")
    bounded_index = case_index % len(cases)
    case = cases[bounded_index]
    strategy_results, hybrid_payload = _run_strategy_matrix(
        repo_root=repo_root,
        domain=domain,
        eval_filename=eval_filename,
        decision_input=_decision_input_from_case(case),
        threshold=threshold,
        learned_model_path=learned_model_path,
    )

    return {
        "domain": domain,
        "eval_filename": eval_filename,
        "case_index": bounded_index,
        "case_count": len(cases),
        "case": case,
        "decision": hybrid_payload,
        "strategy_results": strategy_results,
    }


def load_incident_replay_episodes(
    repo_root: str | Path,
    domain: str,
) -> list[dict[str, Any]]:
    payload = _cached_incident_replay_payload(str(Path(repo_root)))
    episodes = payload.get(domain)
    if episodes is None:
        raise ValueError(f"incident replay artifact has no domain slice for {domain}")
    if not isinstance(episodes, list):
        raise ValueError(f"incident replay domain slice is malformed for {domain}")
    return episodes


def run_incident_replay_episode_matrix(
    *,
    repo_root: str | Path,
    domain: str,
    episode_index: int,
    step_index: int = 0,
    threshold: float = 0.60,
    learned_model_path: str | None = None,
) -> dict[str, Any]:
    episodes = load_incident_replay_episodes(repo_root, domain)
    if not episodes:
        raise ValueError(f"no incident replay episodes for {domain}")
    bounded_episode_index = episode_index % len(episodes)
    episode = episodes[bounded_episode_index]
    steps = episode.get("steps") or []
    if not steps:
        raise ValueError(f"incident replay episode has no steps: {episode.get('episode_id')}")
    bounded_step_index = step_index % len(steps)
    step = steps[bounded_step_index]
    case = step.get("case")
    if not isinstance(case, dict):
        raise ValueError(f"incident replay step is missing case payload: {episode.get('episode_id')}")

    strategy_results, hybrid_payload = _run_strategy_matrix(
        repo_root=repo_root,
        domain=domain,
        eval_filename="cases.jsonl",
        decision_input=_decision_input_from_case(case),
        threshold=threshold,
        learned_model_path=learned_model_path,
    )

    replay_entry = {
        "episode_id": episode.get("episode_id"),
        "episode_type": episode.get("episode_type"),
        "episode_source": episode.get("episode_source"),
        "base_case_id": episode.get("base_case_id"),
        "switch_case_id": episode.get("switch_case_id"),
        "unsupported_case_id": episode.get("unsupported_case_id"),
        "counterfactual_case_pack_path": episode.get("counterfactual_case_pack_path"),
        "counterfactual_case_pack_signature": episode.get("counterfactual_case_pack_signature"),
        "episode_index": bounded_episode_index,
        "episode_count": len(episodes),
        "step_index": bounded_step_index,
        "step_count": len(steps),
        "step": step,
    }
    return {
        "domain": domain,
        "eval_filename": "cases.jsonl",
        "case_index": bounded_step_index,
        "case_count": len(steps),
        "case": case,
        "decision": hybrid_payload,
        "strategy_results": strategy_results,
        "replay_entry": replay_entry,
    }


def load_draft_case_counts(repo_root: str | Path, domain: str) -> dict[str, int]:
    drafts_dir = _drafts_dir(repo_root, domain)
    counts: dict[str, int] = {}
    for target, filename in DRAFT_FILE_NAMES.items():
        path = drafts_dir / filename
        counts[target] = len(load_cases(path)) if path.exists() else 0
    return counts


def load_draft_cases(
    repo_root: str | Path,
    domain: str,
    target: str,
) -> list[dict[str, Any]]:
    if target not in DRAFT_FILE_NAMES:
        raise ValueError(f"unsupported draft target: {target}")
    path = _drafts_dir(repo_root, domain) / DRAFT_FILE_NAMES[target]
    if not path.exists():
        return []
    return load_cases(path)


def load_domain_action_ids(repo_root: str | Path, domain: str) -> list[str]:
    registry = load_registry(_domain_paths(repo_root, domain, "cases.jsonl")["registry"])
    return [action.action_id for action in registry.actions]


def build_draft_case_queue(
    repo_root: str | Path,
    domain: str,
    target: str,
    draft_filter: str = "all",
    draft_sort: str = "queue",
) -> list[dict[str, Any]]:
    if draft_filter not in DRAFT_FILTERS:
        raise ValueError(f"unsupported draft filter: {draft_filter}")
    if draft_sort not in DRAFT_SORTS:
        raise ValueError(f"unsupported draft sort: {draft_sort}")
    drafts = load_draft_cases(repo_root, domain, target)
    registry = load_registry(_domain_paths(repo_root, domain, "cases.jsonl")["registry"])
    validator = DeterministicValidator(registry)
    queue: list[dict[str, Any]] = []
    for original_index, draft_case in enumerate(drafts):
        review_status = _draft_review_status(draft_case)
        diagnosis = _diagnose_case_promotion_readiness_with_registry(registry, validator, draft_case)
        readiness = diagnosis["readiness"]
        promotable = _draft_is_promotable(target, review_status, readiness)
        if not _draft_matches_filter(draft_filter, review_status, readiness, promotable):
            continue
        queue.append(
            {
                "draft_index": original_index,
                "draft_case": draft_case,
                "review_status": review_status,
                "readiness": readiness,
                "diagnostics": diagnosis["diagnostics"],
                "primary_diagnostic": diagnosis["primary_diagnostic"],
                "promotable": promotable,
                "group_label": None,
            }
        )
    queue.sort(key=lambda entry: _draft_queue_sort_key(entry, draft_sort))
    for entry in queue:
        entry["group_label"] = _draft_queue_group_label(entry, draft_sort)
    return queue


def find_adjacent_draft_group_index(
    repo_root: str | Path,
    domain: str,
    target: str,
    draft_index: int,
    draft_filter: str = "all",
    draft_sort: str = "queue",
    step: int = 1,
) -> dict[str, Any]:
    if step == 0:
        raise ValueError("draft group navigation step cannot be zero")
    if draft_sort == "queue":
        raise ValueError("draft group navigation requires grouped sort mode")
    queue = build_draft_case_queue(
        repo_root,
        domain,
        target,
        draft_filter=draft_filter,
        draft_sort=draft_sort,
    )
    if not queue:
        raise ValueError(f"no {target} draft cases for {domain} matching filter {draft_filter}")
    bounded_index = draft_index % len(queue)
    current_label = queue[bounded_index].get("group_label")
    if current_label is None:
        raise ValueError("current queue does not expose draft groups")
    target_label = None
    direction = 1 if step > 0 else -1
    for offset in range(1, len(queue)):
        candidate_index = (bounded_index + direction * offset) % len(queue)
        candidate_label = queue[candidate_index].get("group_label")
        if candidate_label != current_label:
            target_label = candidate_label
            break
    if target_label is None:
        raise ValueError("no adjacent draft group available")
    first_index = next(
        index
        for index, entry in enumerate(queue)
        if entry.get("group_label") == target_label
    )
    group_count = sum(1 for entry in queue if entry.get("group_label") == target_label)
    return {
        "draft_index": first_index,
        "group_label": target_label,
        "group_count": group_count,
    }


def summarize_draft_group(
    repo_root: str | Path,
    domain: str,
    target: str,
    draft_filter: str = "all",
    draft_sort: str = "queue",
    group_label: str | None = None,
) -> dict[str, Any] | None:
    queue = build_draft_case_queue(
        repo_root,
        domain,
        target,
        draft_filter=draft_filter,
        draft_sort=draft_sort,
    )
    if not queue:
        return None
    if group_label is None:
        group_label = queue[0].get("group_label")
    return _summarize_draft_group_entries(queue, group_label)


def assess_case_promotion_readiness(
    repo_root: str | Path,
    domain: str,
    case: dict[str, Any],
) -> dict[str, Any]:
    registry = load_registry(_domain_paths(repo_root, domain, "cases.jsonl")["registry"])
    validator = DeterministicValidator(registry)
    return _assess_case_promotion_readiness_with_registry(registry, validator, case)


def diagnose_case_promotion_readiness(
    repo_root: str | Path,
    domain: str,
    case: dict[str, Any],
) -> dict[str, Any]:
    registry = load_registry(_domain_paths(repo_root, domain, "cases.jsonl")["registry"])
    validator = DeterministicValidator(registry)
    return _diagnose_case_promotion_readiness_with_registry(registry, validator, case)


def _summarize_draft_group_entries(
    queue: list[dict[str, Any]],
    group_label: str | None,
) -> dict[str, Any] | None:
    if group_label is None:
        return None
    group_entries = [entry for entry in queue if entry.get("group_label") == group_label]
    if not group_entries:
        return None

    review_status_counts: Counter[str] = Counter()
    recommended_target_counts: Counter[str] = Counter()
    diagnostic_counts: Counter[str] = Counter()
    expected_action_counts: Counter[str] = Counter()
    proposed_action_counts: Counter[str] = Counter()
    diagnostic_feature_counts: Counter[str] = Counter()
    supported_count = 0
    unsupported_count = 0
    ood_count = 0

    for entry in group_entries:
        draft_case = entry.get("draft_case") or {}
        draft_meta = draft_case.get("draft_meta") or {}
        readiness = entry.get("readiness") or {}
        primary_diagnostic = entry.get("primary_diagnostic") or {}

        review_status_counts[str(entry.get("review_status") or "pending")] += 1
        recommended_target_counts[str(readiness.get("recommended_target") or "unassigned")] += 1
        diagnostic_counts[str(primary_diagnostic.get("code") or "ready_or_unclassified")] += 1
        expected_action_counts[str(draft_case.get("expected_action_id") or "none")] += 1
        proposed_action_counts[str(draft_meta.get("proposed_expected_action_id") or "none")] += 1
        feature_name = primary_diagnostic.get("feature")
        if feature_name is not None:
            diagnostic_feature_counts[str(feature_name)] += 1
        if bool(draft_case.get("supported", True)):
            supported_count += 1
        else:
            unsupported_count += 1
        if bool(draft_case.get("ood", False)):
            ood_count += 1

    return {
        "label": group_label,
        "count": len(group_entries),
        "supported_count": supported_count,
        "unsupported_count": unsupported_count,
        "ood_count": ood_count,
        "review_status_counts": _draft_group_count_rows(review_status_counts),
        "recommended_target_counts": _draft_group_count_rows(recommended_target_counts),
        "diagnostic_counts": _draft_group_count_rows(diagnostic_counts),
        "expected_action_counts": _draft_group_count_rows(expected_action_counts),
        "proposed_action_counts": _draft_group_count_rows(proposed_action_counts),
        "diagnostic_feature_counts": _draft_group_count_rows(diagnostic_feature_counts),
    }


def _summarize_selected_draft_entries(queue: list[dict[str, Any]]) -> dict[str, Any]:
    review_status_counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()
    recommended_target_counts: Counter[str] = Counter()
    diagnostic_counts: Counter[str] = Counter()
    supported_count = 0
    unsupported_count = 0
    ood_count = 0
    promotable_count = 0

    for entry in queue:
        draft_case = entry.get("draft_case") or {}
        readiness = entry.get("readiness") or {}
        primary_diagnostic = entry.get("primary_diagnostic") or {}
        review_status_counts[str(entry.get("review_status") or "pending")] += 1
        group_label = entry.get("group_label")
        if group_label is not None:
            group_counts[str(group_label)] += 1
        recommended_target_counts[str(readiness.get("recommended_target") or "unassigned")] += 1
        diagnostic_counts[str(primary_diagnostic.get("code") or "ready_or_unclassified")] += 1
        if bool(draft_case.get("supported", True)):
            supported_count += 1
        else:
            unsupported_count += 1
        if bool(draft_case.get("ood", False)):
            ood_count += 1
        if bool(entry.get("promotable")):
            promotable_count += 1

    return {
        "count": len(queue),
        "supported_count": supported_count,
        "unsupported_count": unsupported_count,
        "ood_count": ood_count,
        "promotable_count": promotable_count,
        "review_status_counts": _draft_group_count_rows(review_status_counts),
        "group_counts": _draft_group_count_rows(group_counts),
        "recommended_target_counts": _draft_group_count_rows(recommended_target_counts),
        "diagnostic_counts": _draft_group_count_rows(diagnostic_counts),
    }


def _draft_group_count_rows(counter: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"label": label, "count": count}
        for label, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _assess_case_promotion_readiness_with_registry(
    registry,
    validator: DeterministicValidator,
    case: dict[str, Any],
) -> dict[str, Any]:
    action_ids = {action.action_id for action in registry.actions}

    context_valid, context_reason = evaluate_registry_context(
        registry,
        case.get("input_features", {}),
    )
    expected_action_id = case.get("expected_action_id")
    expected_action_known = expected_action_id is None or expected_action_id in action_ids
    expected_action_supported = None
    expected_action_reason = None
    if expected_action_id is not None and expected_action_known:
        validation = validator.validate(
            DecisionCandidate(action_id=expected_action_id, confidence=1.0),
            case.get("input_features", {}),
        )
        expected_action_supported = validation.valid
        expected_action_reason = validation.reason

    supported = bool(case.get("supported", True))
    unsupported_eval_ready = (not supported) and expected_action_id is None
    supported_eval_ready = (
        supported
        and context_valid
        and expected_action_id is not None
        and expected_action_known
        and bool(expected_action_supported)
    )
    train_ready = supported_eval_ready
    eval_ready = supported_eval_ready or unsupported_eval_ready

    recommended_target = None
    if train_ready:
        recommended_target = "train"
    elif eval_ready:
        recommended_target = "eval"

    return {
        "context_valid": context_valid,
        "context_reason": context_reason,
        "expected_action_known": expected_action_known,
        "expected_action_supported": expected_action_supported,
        "expected_action_reason": expected_action_reason,
        "train_ready": train_ready,
        "eval_ready": eval_ready,
        "unsupported_eval_ready": unsupported_eval_ready,
        "supported_eval_ready": supported_eval_ready,
        "recommended_target": recommended_target,
    }


def _diagnose_case_promotion_readiness_with_registry(
    registry,
    validator: DeterministicValidator,
    case: dict[str, Any],
) -> dict[str, Any]:
    readiness = _assess_case_promotion_readiness_with_registry(registry, validator, case)
    diagnostics: list[dict[str, Any]] = []

    context_reason = readiness.get("context_reason")
    if context_reason:
        diagnostics.append(_diagnose_context_reason(registry, context_reason))

    expected_action_id = case.get("expected_action_id")
    if readiness.get("expected_action_known") is False:
        diagnostics.append(
            {
                "category": "expected_action",
                "code": "unknown_expected_action",
                "message": f"expected action {expected_action_id} is not declared in the registry",
                "detail": "choose a registry action id or leave the expected action empty for unsupported eval cases",
                "expected_action_id": expected_action_id,
            }
        )
    elif readiness.get("expected_action_reason"):
        diagnostics.append(
            _diagnose_expected_action_reason(
                registry,
                expected_action_id,
                readiness["expected_action_reason"],
            )
        )

    return {
        "readiness": readiness,
        "diagnostics": diagnostics,
        "primary_diagnostic": diagnostics[0] if diagnostics else None,
    }


def _diagnose_context_reason(registry, reason: str) -> dict[str, Any]:
    schema = registry.context_schema or {}
    tokens = reason.split(":")
    if reason == "context:empty":
        return {
            "category": "context",
            "code": "empty_context",
            "message": "context is empty",
            "detail": "populate the required registry features before promoting this draft",
        }
    if len(tokens) >= 3 and tokens[0] == "context":
        issue = tokens[1]
        feature_name = tokens[2]
        field_spec = schema.get(feature_name) or {}
        if issue == "missing":
            return {
                "category": "context",
                "code": "missing_required_feature",
                "message": f"missing required feature {feature_name}",
                "detail": f"add {feature_name} to satisfy the registry contract",
                "feature": feature_name,
            }
        if issue == "unknown":
            return {
                "category": "context",
                "code": "unknown_feature",
                "message": f"unknown feature {feature_name}",
                "detail": f"{feature_name} is not declared in the registry context schema",
                "feature": feature_name,
            }
        if issue == "type" and len(tokens) >= 4:
            expected_type = tokens[3]
            return {
                "category": "context",
                "code": "feature_type_mismatch",
                "message": f"{feature_name} has the wrong type",
                "detail": f"{feature_name} must be a {expected_type}",
                "feature": feature_name,
                "expected_type": expected_type,
            }
        if issue == "enum":
            allowed = field_spec.get("enum") or []
            return {
                "category": "context",
                "code": "feature_enum_mismatch",
                "message": f"{feature_name} is outside the allowed enum",
                "detail": f"allowed values: {', '.join(str(value) for value in allowed) or '--'}",
                "feature": feature_name,
            }
        if issue == "minimum":
            return {
                "category": "context",
                "code": "feature_below_minimum",
                "message": f"{feature_name} is below the allowed minimum",
                "detail": f"minimum value: {field_spec.get('minimum')}",
                "feature": feature_name,
            }
        if issue == "maximum":
            return {
                "category": "context",
                "code": "feature_above_maximum",
                "message": f"{feature_name} is above the allowed maximum",
                "detail": f"maximum value: {field_spec.get('maximum')}",
                "feature": feature_name,
            }
    return {
        "category": "context",
        "code": "context_validation_error",
        "message": reason,
        "detail": "the draft context does not satisfy the registry schema",
    }


def _diagnose_expected_action_reason(
    registry,
    expected_action_id: str | None,
    reason: str,
) -> dict[str, Any]:
    if reason == "unknown_action":
        return {
            "category": "expected_action",
            "code": "unknown_expected_action",
            "message": f"expected action {expected_action_id} is not declared in the registry",
            "detail": "choose a registry action id or clear the label for unsupported eval cases",
            "expected_action_id": expected_action_id,
        }
    if reason.startswith("missing_required_parameter:"):
        parameter_name = reason.split(":", 1)[1]
        return {
            "category": "expected_action",
            "code": "missing_required_parameter",
            "message": f"expected action {expected_action_id} is missing required parameter {parameter_name}",
            "detail": f"add parameter {parameter_name} before promoting this draft",
            "expected_action_id": expected_action_id,
        }
    if reason.startswith("unexpected_parameter:"):
        parameter_name = reason.split(":", 1)[1]
        return {
            "category": "expected_action",
            "code": "unexpected_parameter",
            "message": f"expected action {expected_action_id} includes unexpected parameter {parameter_name}",
            "detail": f"remove parameter {parameter_name} because it is not declared by the action schema",
            "expected_action_id": expected_action_id,
        }
    if reason.startswith("unsupported_features:"):
        support_reason = reason.split(":", 1)[1]
        return _diagnose_support_reason(registry, expected_action_id, support_reason)
    if reason == "precondition_failed":
        return {
            "category": "expected_action",
            "code": "precondition_failed",
            "message": f"expected action {expected_action_id} fails an action precondition",
            "detail": "the action label is present but its required precondition is not met",
            "expected_action_id": expected_action_id,
        }
    return {
        "category": "expected_action",
        "code": "expected_action_validation_error",
        "message": f"expected action {expected_action_id} is not promotable",
        "detail": reason,
        "expected_action_id": expected_action_id,
    }


def _diagnose_support_reason(
    registry,
    expected_action_id: str | None,
    support_reason: str,
) -> dict[str, Any]:
    action = next((candidate for candidate in registry.actions if candidate.action_id == expected_action_id), None)
    detail = support_reason
    code = "unsupported_expected_action"
    message = f"expected action {expected_action_id} is unsupported for this draft"

    tokens = support_reason.split(":")
    if len(tokens) >= 3 and action is not None:
        node_path = tokens[0]
        feature_name = tokens[1]
        op = tokens[2]
        node = _lookup_support_node(action.support_spec or {}, node_path)
        expected_value = node.get("value") if isinstance(node, dict) else None
        if op == "missing":
            code = "unsupported_missing_feature"
            message = f"{expected_action_id} requires feature {feature_name}"
            detail = f"add feature {feature_name} so the action can be validated"
        elif op == "eq":
            code = "unsupported_feature_value"
            message = f"{expected_action_id} requires {feature_name} = {expected_value}"
            detail = f"update {feature_name} to {expected_value} or choose another expected action"
        elif op == "neq":
            code = "unsupported_feature_value"
            message = f"{expected_action_id} requires {feature_name} != {expected_value}"
            detail = f"change {feature_name} away from {expected_value} or choose another expected action"
        elif op in {"gt", "gte", "lt", "lte"}:
            code = "unsupported_feature_range"
            message = f"{expected_action_id} requires {feature_name} {op} {expected_value}"
            detail = f"adjust {feature_name} or choose an action whose support envelope matches this case"
        elif op in {"in", "not_in"}:
            code = "unsupported_feature_set"
            rendered = ", ".join(str(value) for value in (expected_value or []))
            message = f"{expected_action_id} requires {feature_name} {op} [{rendered}]"
            detail = f"set {feature_name} to an allowed value or choose another expected action"
        elif op in {"exists", "not_exists"}:
            code = "unsupported_feature_presence"
            requirement = "present" if op == "exists" else "absent"
            message = f"{expected_action_id} requires {feature_name} to be {requirement}"
            detail = f"make {feature_name} {requirement} or choose another expected action"

    return {
        "category": "expected_action",
        "code": code,
        "message": message,
        "detail": detail,
        "expected_action_id": expected_action_id,
    }


def _lookup_support_node(spec: dict[str, Any], path: str) -> dict[str, Any] | None:
    if not spec or path == "support_spec":
        return spec
    current: Any = spec
    for segment in path.split(".")[1:]:
        if segment.startswith("all["):
            current = current.get("all", [])[int(segment[4:-1])]
            continue
        if segment.startswith("any["):
            current = current.get("any", [])[int(segment[4:-1])]
            continue
        if segment == "not":
            current = current.get("not")
            continue
        return None
    return current if isinstance(current, dict) else None


def append_case_draft(
    *,
    repo_root: str | Path,
    domain: str,
    eval_filename: str,
    case: dict[str, Any],
    decision: dict[str, Any],
    strategy_results: list[dict[str, Any]],
    target: str,
    review_flags: list[str] | None = None,
) -> dict[str, Any]:
    if target not in DRAFT_FILE_NAMES:
        raise ValueError(f"unsupported draft target: {target}")
    drafts_dir = _drafts_dir(repo_root, domain)
    drafts_dir.mkdir(parents=True, exist_ok=True)
    path = drafts_dir / DRAFT_FILE_NAMES[target]
    existing_count = len(load_cases(path)) if path.exists() else 0
    draft_case = {
        "case_id": f"{domain}_draft_{target}_{existing_count + 1:03d}",
        "input_features": case["input_features"],
        "expected_action_id": case.get("expected_action_id"),
        "supported": case.get("supported", True),
        "ood": case.get("ood", False),
        "draft_meta": {
            "target_split": target,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_case_id": case.get("case_id"),
            "source_eval_filename": eval_filename,
            "proposed_expected_action_id": decision.get("selected_action_id"),
            "hybrid_confidence": decision.get("confidence"),
            "hybrid_final_status": decision.get("final_status"),
            "review_flags": review_flags or [],
            "review_status": "pending",
            "strategy_snapshot": [
                {
                    "strategy": row.get("strategy"),
                    "selected_action_id": (row.get("decision") or {}).get("selected_action_id"),
                    "confidence": (row.get("decision") or {}).get("confidence"),
                    "final_status": (row.get("decision") or {}).get("final_status"),
                    "correct": (row.get("decision") or {}).get("correct"),
                }
                for row in strategy_results
            ],
        },
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(draft_case, sort_keys=True) + "\n")
    _cached_review_queue.cache_clear()
    return {
        "path": str(path),
        "draft_case": draft_case,
        "count": existing_count + 1,
    }


def run_draft_case_matrix(
    *,
    repo_root: str | Path,
    domain: str,
    target: str,
    draft_index: int,
    draft_filter: str = "all",
    draft_sort: str = "queue",
    threshold: float = 0.60,
    learned_model_path: str | None = None,
) -> dict[str, Any]:
    drafts = load_draft_cases(repo_root, domain, target)
    if not drafts:
        raise ValueError(f"no {target} draft cases for {domain}")
    queue = build_draft_case_queue(
        repo_root,
        domain,
        target,
        draft_filter=draft_filter,
        draft_sort=draft_sort,
    )
    if not queue:
        raise ValueError(f"no {target} draft cases for {domain} matching filter {draft_filter}")
    bounded_index = draft_index % len(queue)
    queue_entry = queue[bounded_index]
    original_index = int(queue_entry["draft_index"])
    group_label = _draft_queue_group_label(queue_entry, draft_sort)
    group_position = None
    group_count = None
    group_counts: list[dict[str, Any]] = []
    if group_label is not None:
        group_position = 1
        for earlier_entry in queue[:bounded_index]:
            if _draft_queue_group_label(earlier_entry, draft_sort) == group_label:
                group_position += 1
        counts: Counter[str] = Counter()
        for candidate in queue:
            label = _draft_queue_group_label(candidate, draft_sort)
            if label is not None:
                counts[label] += 1
        group_count = counts[group_label]
        group_counts = [
            {"label": label, "count": count}
            for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]
    group_summary = _summarize_draft_group_entries(queue, group_label)
    case = drafts[original_index]
    source_eval_filename = ((case.get("draft_meta") or {}).get("source_eval_filename")) or "cases.jsonl"
    strategy_results, hybrid_payload = _run_strategy_matrix(
        repo_root=repo_root,
        domain=domain,
        eval_filename=source_eval_filename,
        decision_input=_decision_input_from_case(case),
        threshold=threshold,
        learned_model_path=learned_model_path,
    )
    return {
        "domain": domain,
        "eval_filename": source_eval_filename,
        "case_index": original_index,
        "case_count": len(drafts),
        "case": case,
        "decision": hybrid_payload,
        "strategy_results": strategy_results,
        "draft_target": target,
        "draft_index": bounded_index,
        "draft_original_index": original_index,
        "draft_count": len(drafts),
        "draft_filtered_count": len(queue),
        "draft_filter": draft_filter,
        "draft_sort": draft_sort,
        "draft_group_label": group_label,
        "draft_group_position": group_position,
        "draft_group_count": group_count,
        "draft_group_counts": group_counts,
        "draft_group_summary": group_summary,
        "draft_entry": case,
        "draft_queue_entry": queue_entry,
        "draft_readiness": queue_entry["readiness"],
        "draft_diagnostics": queue_entry["diagnostics"],
        "draft_primary_diagnostic": queue_entry["primary_diagnostic"],
        "draft_summary": summarize_draft_cases(repo_root, domain, target),
    }


def _run_strategy_matrix(
    *,
    repo_root: str | Path,
    domain: str,
    eval_filename: str,
    decision_input: DecisionInput,
    threshold: float,
    learned_model_path: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    strategy_results: list[dict[str, Any]] = []
    hybrid_payload: dict[str, Any] | None = None
    for strategy in STRATEGY_ORDER:
        runtime, _ = _cached_runtime_for_strategy(
            str(Path(repo_root)),
            domain,
            eval_filename,
            strategy,
            learned_model_path,
            threshold,
        )
        if runtime is None:
            continue
        decision = runtime.decide_and_execute(decision_input)
        decision_payload = json.loads(decision.model_dump_json())
        strategy_results.append(
            {
                "strategy": strategy,
                "decision": decision_payload,
            }
        )
        if strategy == "hybrid":
            hybrid_payload = decision_payload
    if hybrid_payload is None:
        raise ValueError(f"hybrid selector unavailable for {domain}")
    return strategy_results, hybrid_payload


def _path_mtime(path: str | Path) -> float | None:
    target = Path(path)
    if not target.exists():
        return None
    return target.stat().st_mtime


def _max_mtime(*values: float | None) -> float | None:
    candidates = [value for value in values if value is not None]
    if not candidates:
        return None
    return max(candidates)


def update_draft_case(
    *,
    repo_root: str | Path,
    domain: str,
    target: str,
    draft_index: int,
    expected_action_id: str | None | object = _UNSET,
    supported: bool | object = _UNSET,
    ood: bool | object = _UNSET,
    review_status: str | object = _UNSET,
    review_flags: list[str] | object = _UNSET,
) -> dict[str, Any]:
    drafts = load_draft_cases(repo_root, domain, target)
    if not drafts:
        raise ValueError(f"no {target} draft cases for {domain}")
    bounded_index = draft_index % len(drafts)
    draft_case = dict(drafts[bounded_index])
    draft_meta = dict(draft_case.get("draft_meta") or {})

    if expected_action_id is not _UNSET:
        draft_case["expected_action_id"] = expected_action_id
    if supported is not _UNSET:
        draft_case["supported"] = bool(supported)
    if ood is not _UNSET:
        draft_case["ood"] = bool(ood)
    if review_status is not _UNSET:
        draft_meta["review_status"] = review_status
    if review_flags is not _UNSET:
        draft_meta["review_flags"] = list(review_flags)

    draft_meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    draft_case["draft_meta"] = draft_meta
    drafts[bounded_index] = draft_case

    path = _drafts_dir(repo_root, domain) / DRAFT_FILE_NAMES[target]
    _write_jsonl_rows(path, drafts)
    _cached_review_queue.cache_clear()
    return {
        "path": str(path),
        "draft_case": draft_case,
        "draft_index": bounded_index,
    }


def update_selected_draft_cases(
    *,
    repo_root: str | Path,
    domain: str,
    target: str,
    draft_filter: str = "all",
    draft_sort: str = "queue",
    group_label: str | None = None,
    supported: bool | object = _UNSET,
    ood: bool | object = _UNSET,
    review_status: str | object = _UNSET,
) -> dict[str, Any]:
    if supported is _UNSET and ood is _UNSET and review_status is _UNSET:
        raise ValueError("no draft field updates requested")
    if review_status is not _UNSET and review_status not in {"pending", "reviewed"}:
        raise ValueError(f"unsupported bulk review status: {review_status}")
    if group_label is not None and draft_sort == "queue":
        raise ValueError("draft group edits require grouped sort mode")

    drafts = load_draft_cases(repo_root, domain, target)
    if not drafts:
        raise ValueError(f"no {target} draft cases for {domain}")

    queue = build_draft_case_queue(
        repo_root,
        domain,
        target,
        draft_filter=draft_filter,
        draft_sort=draft_sort,
    )
    if group_label is not None:
        queue = [
            entry
            for entry in queue
            if entry.get("group_label") == group_label
        ]
        if not queue:
            raise ValueError(f"no {target} draft cases for {domain} in group {group_label}")
    elif not queue:
        raise ValueError(f"no {target} draft cases for {domain} matching filter {draft_filter}")

    selected_indices = [int(entry["draft_index"]) for entry in queue]
    updated_case_ids: list[str] = []
    unchanged_case_ids: list[str] = []
    skipped_promoted_case_ids: list[str] = []

    for index in selected_indices:
        draft_case = dict(drafts[index])
        draft_meta = dict(draft_case.get("draft_meta") or {})
        current_review_status = _draft_review_status(draft_case)
        if current_review_status.startswith("promoted_"):
            skipped_promoted_case_ids.append(str(draft_case.get("case_id")))
            continue

        changed = False
        if supported is not _UNSET:
            new_supported = bool(supported)
            if bool(draft_case.get("supported", True)) != new_supported:
                draft_case["supported"] = new_supported
                changed = True
        if ood is not _UNSET:
            new_ood = bool(ood)
            if bool(draft_case.get("ood", False)) != new_ood:
                draft_case["ood"] = new_ood
                changed = True
        if review_status is not _UNSET and current_review_status != review_status:
            draft_meta["review_status"] = review_status
            changed = True

        if changed:
            draft_meta["updated_at"] = datetime.now(timezone.utc).isoformat()
            draft_case["draft_meta"] = draft_meta
            drafts[index] = draft_case
            updated_case_ids.append(str(draft_case.get("case_id")))
        else:
            unchanged_case_ids.append(str(draft_case.get("case_id")))

    path = _drafts_dir(repo_root, domain) / DRAFT_FILE_NAMES[target]
    if updated_case_ids:
        _write_jsonl_rows(path, drafts)
    _cached_review_queue.cache_clear()
    return {
        "path": str(path),
        "target": target,
        "draft_filter": draft_filter,
        "draft_sort": draft_sort,
        "group_label": group_label,
        "selected_count": len(selected_indices),
        "updated_count": len(updated_case_ids),
        "unchanged_count": len(unchanged_case_ids),
        "skipped_promoted_count": len(skipped_promoted_case_ids),
        "updated_case_ids": updated_case_ids,
        "unchanged_case_ids": unchanged_case_ids,
        "skipped_promoted_case_ids": skipped_promoted_case_ids,
    }


def export_selected_draft_cases(
    *,
    repo_root: str | Path,
    domain: str,
    target: str,
    draft_filter: str = "all",
    draft_sort: str = "queue",
    group_label: str | None = None,
) -> dict[str, Any]:
    if group_label is not None and draft_sort == "queue":
        raise ValueError("draft group exports require grouped sort mode")

    queue = build_draft_case_queue(
        repo_root,
        domain,
        target,
        draft_filter=draft_filter,
        draft_sort=draft_sort,
    )
    if group_label is not None:
        queue = [
            entry
            for entry in queue
            if entry.get("group_label") == group_label
        ]
        if not queue:
            raise ValueError(f"no {target} draft cases for {domain} in group {group_label}")
    elif not queue:
        raise ValueError(f"no {target} draft cases for {domain} matching filter {draft_filter}")

    selection_summary = _summarize_selected_draft_entries(queue)
    selected_group_summary = _summarize_draft_group_entries(queue, group_label)
    export_dir = _draft_export_dir(repo_root, domain, target)
    export_dir.mkdir(parents=True, exist_ok=True)
    basename = _draft_export_basename(
        domain=domain,
        target=target,
        draft_filter=draft_filter,
        draft_sort=draft_sort,
        group_label=group_label,
    )
    json_path = export_dir / f"{basename}.json"
    jsonl_path = export_dir / f"{basename}.jsonl"
    payload = {
        "domain": domain,
        "target": target,
        "draft_filter": draft_filter,
        "draft_sort": draft_sort,
        "scope": "group" if group_label is not None else "slice",
        "group_label": group_label,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "selection_summary": selection_summary,
        "group_summary": selected_group_summary,
        "entries": queue,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _write_jsonl_rows(jsonl_path, queue)
    return {
        "domain": domain,
        "target": target,
        "draft_filter": draft_filter,
        "draft_sort": draft_sort,
        "scope": payload["scope"],
        "group_label": group_label,
        "selection_count": len(queue),
        "json_path": str(json_path),
        "jsonl_path": str(jsonl_path),
        "selection_summary": selection_summary,
        "group_summary": selected_group_summary,
    }


def export_draft_case_bundle(
    *,
    repo_root: str | Path,
    domains: list[str] | None = None,
    targets: list[str] | None = None,
    draft_filters: list[str] | None = None,
    draft_sorts: list[str] | None = None,
    include_group_exports: bool = False,
) -> dict[str, Any]:
    normalized_domains = list(dict.fromkeys(domains or sorted(DOMAIN_CONFIG)))
    normalized_targets = list(dict.fromkeys(targets or list(DRAFT_FILE_NAMES)))
    normalized_filters = list(dict.fromkeys(draft_filters or ["all"]))
    normalized_sorts = list(dict.fromkeys(draft_sorts or ["queue"]))

    invalid_domains = [domain for domain in normalized_domains if domain not in DOMAIN_CONFIG]
    if invalid_domains:
        raise ValueError(f"unsupported bundle domains: {', '.join(invalid_domains)}")
    invalid_targets = [target for target in normalized_targets if target not in DRAFT_FILE_NAMES]
    if invalid_targets:
        raise ValueError(f"unsupported bundle targets: {', '.join(invalid_targets)}")
    invalid_filters = [draft_filter for draft_filter in normalized_filters if draft_filter not in DRAFT_FILTERS]
    if invalid_filters:
        raise ValueError(f"unsupported bundle filters: {', '.join(invalid_filters)}")
    invalid_sorts = [draft_sort for draft_sort in normalized_sorts if draft_sort not in DRAFT_SORTS]
    if invalid_sorts:
        raise ValueError(f"unsupported bundle sorts: {', '.join(invalid_sorts)}")

    exports: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    slice_export_count = 0
    group_export_count = 0
    selection_count_total = 0

    for domain in normalized_domains:
        for target in normalized_targets:
            for draft_filter in normalized_filters:
                for draft_sort in normalized_sorts:
                    queue = build_draft_case_queue(
                        repo_root,
                        domain,
                        target,
                        draft_filter=draft_filter,
                        draft_sort=draft_sort,
                    )
                    if not queue:
                        skipped.append(
                            {
                                "domain": domain,
                                "target": target,
                                "draft_filter": draft_filter,
                                "draft_sort": draft_sort,
                                "reason": "no_matching_cases",
                            }
                        )
                        continue

                    slice_export = export_selected_draft_cases(
                        repo_root=repo_root,
                        domain=domain,
                        target=target,
                        draft_filter=draft_filter,
                        draft_sort=draft_sort,
                    )
                    exports.append(slice_export)
                    slice_export_count += 1
                    selection_count_total += int(slice_export["selection_count"])

                    if not include_group_exports or draft_sort == "queue":
                        continue

                    seen_group_labels: set[str] = set()
                    for entry in queue:
                        group_label = entry.get("group_label")
                        if group_label is None:
                            continue
                        normalized_group_label = str(group_label)
                        if normalized_group_label in seen_group_labels:
                            continue
                        seen_group_labels.add(normalized_group_label)
                        group_export = export_selected_draft_cases(
                            repo_root=repo_root,
                            domain=domain,
                            target=target,
                            draft_filter=draft_filter,
                            draft_sort=draft_sort,
                            group_label=normalized_group_label,
                        )
                        exports.append(group_export)
                        group_export_count += 1
                        selection_count_total += int(group_export["selection_count"])

    manifest_result = write_draft_export_manifest(repo_root)
    return {
        "domains": normalized_domains,
        "targets": normalized_targets,
        "draft_filters": normalized_filters,
        "draft_sorts": normalized_sorts,
        "include_group_exports": include_group_exports,
        "export_count": len(exports),
        "slice_export_count": slice_export_count,
        "group_export_count": group_export_count,
        "selection_count_total": selection_count_total,
        "skipped_count": len(skipped),
        "exports": exports,
        "skipped": skipped,
        "manifest_path": manifest_result["path"],
        "manifest_markdown_path": manifest_result["markdown_path"],
        "manifest_export_count": manifest_result["export_count"],
    }


def write_draft_export_manifest(repo_root: str | Path) -> dict[str, Any]:
    export_root = _draft_export_root(repo_root)
    export_root.mkdir(parents=True, exist_ok=True)
    manifest_path = export_root / "manifest.json"
    markdown_path = export_root / DEFAULT_DRAFT_EXPORT_MANIFEST_MD

    exports: list[dict[str, Any]] = []
    domain_target_counts: Counter[tuple[str, str]] = Counter()
    domain_counts: Counter[str] = Counter()

    for json_path in sorted(export_root.rglob("*.json")):
        if json_path == manifest_path:
            continue
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        domain = str(payload.get("domain") or "unknown")
        target = str(payload.get("target") or "unknown")
        domain_counts[domain] += 1
        domain_target_counts[(domain, target)] += 1
        jsonl_path = json_path.with_suffix(".jsonl")
        exports.append(
            {
                "domain": domain,
                "target": target,
                "scope": payload.get("scope"),
                "draft_filter": payload.get("draft_filter"),
                "draft_sort": payload.get("draft_sort"),
                "group_label": payload.get("group_label"),
                "exported_at": payload.get("exported_at"),
                "selection_count": (payload.get("selection_summary") or {}).get("count"),
                "json_path": str(json_path.relative_to(Path(repo_root))),
                "jsonl_path": str(jsonl_path.relative_to(Path(repo_root))),
            }
        )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "export_root": str(export_root.relative_to(Path(repo_root))),
        "export_count": len(exports),
        "domain_counts": [
            {"domain": domain, "export_count": count}
            for domain, count in sorted(domain_counts.items())
        ],
        "target_counts": [
            {"domain": domain, "target": target, "export_count": count}
            for (domain, target), count in sorted(domain_target_counts.items())
        ],
        "exports": exports,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_draft_export_manifest_markdown(manifest), encoding="utf-8")
    return {
        "path": str(manifest_path),
        "markdown_path": str(markdown_path),
        "export_count": len(exports),
        "manifest": manifest,
    }


def render_draft_export_manifest_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# KVRM Draft Export Manifest",
        "",
        f"Generated: {manifest['generated_at']}",
        "",
        f"Export root: `{manifest['export_root']}`",
        "",
        (
            "This index summarizes the deterministic draft audit packets exported from the "
            "operator review flow so they can be bundled, cited, and re-audited without "
            "walking the directory tree by hand."
        ),
        "",
        f"Total export packets: {manifest['export_count']}",
        "",
    ]

    domain_counts = manifest.get("domain_counts") or []
    if domain_counts:
        lines.extend(
            [
                "## Domain Counts",
                "",
                "| Domain | Export Count |",
                "| --- | ---: |",
            ]
        )
        for item in domain_counts:
            lines.append(f"| {item['domain']} | {item['export_count']} |")
        lines.append("")

    target_counts = manifest.get("target_counts") or []
    if target_counts:
        lines.extend(
            [
                "## Target Counts",
                "",
                "| Domain | Target | Export Count |",
                "| --- | --- | ---: |",
            ]
        )
        for item in target_counts:
            lines.append(f"| {item['domain']} | {item['target']} | {item['export_count']} |")
        lines.append("")

    exports = manifest.get("exports") or []
    if exports:
        lines.extend(
            [
                "## Export Packets",
                "",
                "| Domain | Target | Scope | Filter | Sort | Group | Selected | JSON | JSONL |",
                "| --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for item in exports:
            group_label = item.get("group_label") or "-"
            lines.append(
                "| "
                f"{item['domain']} | "
                f"{item['target']} | "
                f"{item.get('scope') or '-'} | "
                f"{item.get('draft_filter') or '-'} | "
                f"{item.get('draft_sort') or '-'} | "
                f"{group_label} | "
                f"{item.get('selection_count') or 0} | "
                f"`{item['json_path']}` | "
                f"`{item['jsonl_path']}` |"
            )
    else:
        lines.extend(
            [
                "## Export Packets",
                "",
                "No draft export packets were found under the export root.",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def summarize_draft_cases(
    repo_root: str | Path,
    domain: str,
    target: str,
) -> dict[str, Any]:
    drafts = load_draft_cases(repo_root, domain, target)
    summary = {
        "target": target,
        "total_count": len(drafts),
        "pending_count": 0,
        "reviewed_count": 0,
        "promoted_count": 0,
        "train_ready_count": 0,
        "eval_ready_count": 0,
        "blocked_count": 0,
        "promotable_count": 0,
        "blocked_diagnostic_counts": [],
    }
    registry = load_registry(_domain_paths(repo_root, domain, "cases.jsonl")["registry"])
    validator = DeterministicValidator(registry)
    blocked_codes: Counter[str] = Counter()
    for draft_case in drafts:
        review_status = _draft_review_status(draft_case)
        diagnosis = _diagnose_case_promotion_readiness_with_registry(registry, validator, draft_case)
        readiness = diagnosis["readiness"]
        if review_status.startswith("promoted_"):
            summary["promoted_count"] += 1
        elif review_status == "reviewed":
            summary["reviewed_count"] += 1
        else:
            summary["pending_count"] += 1
        if readiness["train_ready"]:
            summary["train_ready_count"] += 1
        if readiness["eval_ready"]:
            summary["eval_ready_count"] += 1
        if not readiness["train_ready"] and not readiness["eval_ready"]:
            summary["blocked_count"] += 1
            primary = diagnosis["primary_diagnostic"] or {}
            blocked_codes[str(primary.get("code") or "unclassified")] += 1
        if _draft_is_promotable(target, review_status, readiness):
            summary["promotable_count"] += 1
    summary["blocked_diagnostic_counts"] = [
        {"code": code, "count": count}
        for code, count in sorted(blocked_codes.items(), key=lambda item: (-item[1], item[0]))
    ]
    return summary


def promote_ready_draft_cases(
    *,
    repo_root: str | Path,
    domain: str,
    target: str,
    draft_filter: str = "all",
    draft_sort: str = "queue",
    group_label: str | None = None,
) -> dict[str, Any]:
    drafts = load_draft_cases(repo_root, domain, target)
    if not drafts:
        raise ValueError(f"no {target} draft cases for {domain}")
    queue = build_draft_case_queue(
        repo_root,
        domain,
        target,
        draft_filter=draft_filter,
        draft_sort=draft_sort,
    )
    if group_label is not None:
        if draft_sort == "queue":
            raise ValueError("draft group promotion requires grouped sort mode")
        queue = [
            entry
            for entry in queue
            if _draft_queue_group_label(entry, draft_sort) == group_label
        ]
        if not queue:
            raise ValueError(f"no {target} draft cases for {domain} in group {group_label}")

    eligible_indices = [int(entry["draft_index"]) for entry in queue if entry.get("promotable")]

    destination_counts = {"train": 0, "eval": 0}
    promoted_case_ids: list[str] = []
    for index in eligible_indices:
        result = promote_draft_case(
            repo_root=repo_root,
            domain=domain,
            target=target,
            draft_index=index,
        )
        promoted_case_ids.append(result["promoted_case"]["case_id"])
        destination_name = "train" if result["destination_path"].endswith("train_cases.jsonl") else "eval"
        destination_counts[destination_name] += 1

    return {
        "target": target,
        "draft_filter": draft_filter,
        "draft_sort": draft_sort,
        "group_label": group_label,
        "total_count": len(drafts),
        "selected_count": len(queue),
        "eligible_count": len(eligible_indices),
        "promoted_count": len(promoted_case_ids),
        "skipped_count": len(queue) - len(promoted_case_ids),
        "unselected_count": len(drafts) - len(queue),
        "destination_counts": destination_counts,
        "promoted_case_ids": promoted_case_ids,
    }


def promote_draft_case(
    *,
    repo_root: str | Path,
    domain: str,
    target: str,
    draft_index: int,
    destination: str | None = None,
) -> dict[str, Any]:
    drafts = load_draft_cases(repo_root, domain, target)
    if not drafts:
        raise ValueError(f"no {target} draft cases for {domain}")
    bounded_index = draft_index % len(drafts)
    draft_case = dict(drafts[bounded_index])
    draft_meta = dict(draft_case.get("draft_meta") or {})
    readiness = assess_case_promotion_readiness(repo_root, domain, draft_case)
    registry = load_registry(_domain_paths(repo_root, domain, "cases.jsonl")["registry"])
    action_ids = {action.action_id for action in registry.actions}

    expected_action_id = draft_case.get("expected_action_id")
    if expected_action_id is not None and expected_action_id not in action_ids:
        raise ValueError(f"unknown expected action: {expected_action_id}")
    if destination is None:
        if target == "review":
            destination = readiness["recommended_target"]
        else:
            destination = target
    if destination is None:
        raise ValueError("draft is not ready for train or eval promotion")
    if destination not in {"train", "eval"}:
        raise ValueError(f"unsupported promotion destination: {destination}")
    if destination == "train" and not readiness["train_ready"]:
        raise ValueError("draft is not train-ready")
    if destination == "eval" and not readiness["eval_ready"]:
        raise ValueError("draft is not eval-ready")

    promoted_case = {
        "case_id": draft_case["case_id"],
        "input_features": draft_case["input_features"],
        "expected_action_id": expected_action_id,
        "supported": draft_case.get("supported", True),
        "ood": draft_case.get("ood", False),
    }

    config = _domain_paths(repo_root, domain, "cases.jsonl")
    destination_path = config["train_cases"] if destination == "train" else config["cases"]
    existing_rows = load_cases(destination_path)
    replaced = False
    for index, row in enumerate(existing_rows):
        if row.get("case_id") == promoted_case["case_id"]:
            existing_rows[index] = promoted_case
            replaced = True
            break
    if not replaced:
        existing_rows.append(promoted_case)
    _write_jsonl_rows(destination_path, existing_rows)

    draft_meta["review_status"] = f"promoted_{destination}"
    draft_meta["promoted_at"] = datetime.now(timezone.utc).isoformat()
    draft_meta["promoted_path"] = str(destination_path)
    draft_meta["promoted_expected_action_id"] = expected_action_id
    draft_meta["promotion_readiness"] = readiness
    draft_case["expected_action_id"] = expected_action_id
    draft_case["draft_meta"] = draft_meta
    drafts[bounded_index] = draft_case
    draft_path = _drafts_dir(repo_root, domain) / DRAFT_FILE_NAMES[target]
    _write_jsonl_rows(draft_path, drafts)

    _cached_review_queue.cache_clear()
    return {
        "draft_path": str(draft_path),
        "destination_path": str(destination_path),
        "promoted_case": promoted_case,
        "replaced": replaced,
    }


def build_case_review_queue(
    *,
    repo_root: str | Path,
    domain: str,
    eval_filename: str,
    threshold: float = 0.60,
    learned_model_path: str | None = None,
) -> list[dict[str, Any]]:
    return list(
        _cached_review_queue(
            str(Path(repo_root)),
            domain,
            eval_filename,
            learned_model_path,
            threshold,
        )
    )


@lru_cache(maxsize=24)
def _cached_review_queue(
    repo_root: str,
    domain: str,
    eval_filename: str,
    learned_model_path: str | None,
    threshold: float,
) -> tuple[dict[str, Any], ...]:
    config = _domain_paths(repo_root, domain, eval_filename)
    cases = load_cases(config["cases"])
    rows: list[dict[str, Any]] = []
    for case_index, case in enumerate(cases):
        payload = run_demo_case_matrix(
            repo_root=repo_root,
            domain=domain,
            eval_filename=eval_filename,
            case_index=case_index,
            threshold=threshold,
            learned_model_path=learned_model_path,
        )
        review_flags = _review_flags_for_payload(payload, threshold=threshold)
        if not review_flags:
            continue
        strategy_results = payload.get("strategy_results", [])
        selected_actions = {
            (row.get("decision") or {}).get("selected_action_id")
            for row in strategy_results
        }
        rows.append(
            {
                "case_index": case_index,
                "case_id": case.get("case_id"),
                "expected_action_id": case.get("expected_action_id"),
                "selected_action_id": payload["decision"].get("selected_action_id"),
                "review_flags": review_flags,
                "priority": _review_priority(review_flags),
                "strategy_action_count": len(selected_actions),
                "confidence": payload["decision"].get("confidence"),
                "supported": case.get("supported", True),
                "ood": case.get("ood", False),
            }
        )
    rows.sort(
        key=lambda row: (
            row["priority"],
            row["case_index"],
        )
    )
    return tuple(rows)


def _review_flags_for_payload(payload: dict[str, Any], *, threshold: float) -> list[str]:
    case = payload["case"]
    decision = payload["decision"]
    strategy_results = payload.get("strategy_results", [])
    strategy_actions = {
        (row.get("decision") or {}).get("selected_action_id")
        for row in strategy_results
    }
    final_statuses = {
        (row.get("decision") or {}).get("final_status")
        for row in strategy_results
    }
    flags: list[str] = []
    if case.get("supported", True) and not decision.get("correct", False):
        flags.append("hybrid_incorrect")
    if len(strategy_actions) > 1:
        flags.append("strategy_disagreement")
    if decision.get("fallback_used") or decision.get("final_status") == "fallback_executed":
        flags.append("fallback_path")
    if decision.get("confidence") is not None and decision["confidence"] <= threshold + 0.05:
        flags.append("low_confidence")
    if case.get("supported", True) and case.get("ood", False):
        flags.append("supported_ood")
    if not case.get("supported", True):
        flags.append("unsupported_case")
    if "abstained" in final_statuses:
        flags.append("selector_abstention")
    return flags


def _review_priority(flags: list[str]) -> int:
    ordering = [
        "hybrid_incorrect",
        "strategy_disagreement",
        "fallback_path",
        "low_confidence",
        "supported_ood",
        "unsupported_case",
        "selector_abstention",
    ]
    for index, name in enumerate(ordering):
        if name in flags:
            return index
    return len(ordering)


def _draft_review_status(draft_case: dict[str, Any]) -> str:
    return str((draft_case.get("draft_meta") or {}).get("review_status") or "pending")


def _draft_is_promotable(
    target: str,
    review_status: str,
    readiness: dict[str, Any],
) -> bool:
    if review_status.startswith("promoted_"):
        return False
    if target == "review":
        return review_status == "reviewed" and readiness.get("recommended_target") in {"train", "eval"}
    if target == "train":
        return bool(readiness.get("train_ready"))
    if target == "eval":
        return bool(readiness.get("eval_ready"))
    raise ValueError(f"unsupported draft target: {target}")


def _draft_matches_filter(
    draft_filter: str,
    review_status: str,
    readiness: dict[str, Any],
    promotable: bool,
) -> bool:
    if draft_filter == "all":
        return True
    if draft_filter == "pending":
        return review_status != "reviewed" and not review_status.startswith("promoted_")
    if draft_filter == "reviewed":
        return review_status == "reviewed"
    if draft_filter == "promotable":
        return promotable
    if draft_filter == "blocked":
        return (
            not review_status.startswith("promoted_")
            and not readiness.get("train_ready")
            and not readiness.get("eval_ready")
        )
    if draft_filter == "promoted":
        return review_status.startswith("promoted_")
    raise ValueError(f"unsupported draft filter: {draft_filter}")


def _draft_queue_sort_key(entry: dict[str, Any], draft_sort: str) -> tuple[Any, ...]:
    draft_index = int(entry.get("draft_index", 0))
    review_status = str(entry.get("review_status") or "pending")
    readiness = entry.get("readiness") or {}
    primary_diagnostic = entry.get("primary_diagnostic") or {}
    diagnostic_code = str(primary_diagnostic.get("code") or "ready_or_unclassified")
    recommended_target = str(readiness.get("recommended_target") or "unassigned")
    promotable_rank = 0 if entry.get("promotable") else 1

    if draft_sort == "queue":
        return (draft_index,)
    if draft_sort == "diagnostic":
        return (
            0 if primary_diagnostic else 1,
            diagnostic_code,
            _draft_review_status_rank(review_status),
            _draft_recommended_target_rank(recommended_target),
            draft_index,
        )
    if draft_sort == "status":
        return (
            _draft_review_status_rank(review_status),
            promotable_rank,
            _draft_recommended_target_rank(recommended_target),
            diagnostic_code,
            draft_index,
        )
    if draft_sort == "target":
        return (
            _draft_recommended_target_rank(recommended_target),
            _draft_review_status_rank(review_status),
            promotable_rank,
            diagnostic_code,
            draft_index,
        )
    raise ValueError(f"unsupported draft sort: {draft_sort}")


def _draft_queue_group_label(entry: dict[str, Any], draft_sort: str) -> str | None:
    if draft_sort == "diagnostic":
        primary_diagnostic = entry.get("primary_diagnostic") or {}
        return str(primary_diagnostic.get("code") or "ready_or_unclassified")
    if draft_sort == "status":
        return str(entry.get("review_status") or "pending")
    if draft_sort == "target":
        readiness = entry.get("readiness") or {}
        return str(readiness.get("recommended_target") or "unassigned")
    return None


def _draft_review_status_rank(review_status: str) -> int:
    ordering = {
        "pending": 0,
        "reviewed": 1,
        "promoted_train": 2,
        "promoted_eval": 3,
    }
    return ordering.get(review_status, len(ordering))


def _draft_recommended_target_rank(recommended_target: str) -> int:
    ordering = {
        "train": 0,
        "eval": 1,
        "unassigned": 2,
    }
    return ordering.get(recommended_target, len(ordering))


def _draft_export_dir(repo_root: str | Path, domain: str, target: str) -> Path:
    return _draft_export_root(repo_root) / domain / target


def _draft_export_root(repo_root: str | Path) -> Path:
    return Path(repo_root) / "kvrm-bench" / "results" / "draft_exports"


def _draft_export_basename(
    *,
    domain: str,
    target: str,
    draft_filter: str,
    draft_sort: str,
    group_label: str | None,
) -> str:
    scope = "slice" if group_label is None else f"group-{_sanitize_export_token(group_label)}"
    return (
        f"{_sanitize_export_token(domain)}_{_sanitize_export_token(target)}"
        f"_filter-{_sanitize_export_token(draft_filter)}"
        f"_sort-{_sanitize_export_token(draft_sort)}"
        f"_scope-{scope}"
    )


def _sanitize_export_token(value: str) -> str:
    rendered = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in rendered:
        rendered = rendered.replace("--", "-")
    rendered = rendered.strip("-")
    return rendered or "none"


def _drafts_dir(repo_root: str | Path, domain: str) -> Path:
    return Path(repo_root) / DOMAIN_CONFIG[domain]["data_dir"] / "drafts"


def _write_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
