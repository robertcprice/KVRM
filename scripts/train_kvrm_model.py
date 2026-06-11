from __future__ import annotations

import argparse
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent  # repo root (this script lives in scripts/)


def load_cases(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def default_modules_for_domain(domain: str) -> tuple[str, str, str]:
    mapping = {
        "soc": (
            "soc_playbook_router.selectors",
            "soc_playbook_router.executor",
            "request_human_triage",
        ),
        "sre": (
            "sre_policy_router.selectors",
            "sre_policy_router.executor",
            "page_human_operator",
        ),
        "drone": (
            "drone_mission_router.selectors",
            "drone_mission_router.executor",
            "manual_handoff",
        ),
        "grid": (
            "grid_ops_router.selectors",
            "grid_ops_router.executor",
            "escalate_grid_supervisor",
        ),
        "finance": (
            "finance_risk_router.selectors",
            "finance_risk_router.executor",
            "manual_review",
        ),
        "medical": (
            "medical_workflow_router.selectors",
            "medical_workflow_router.executor",
            "escalate_supervisor_review",
        ),
        "iam": (
            "iam_access_router.selectors",
            "iam_access_router.executor",
            "escalate_identity_admin",
        ),
    }
    if domain not in mapping:
        raise ValueError(f"unsupported domain {domain!r}")
    return mapping[domain]


def run_selector_on_cases(
    *,
    selector,
    registry,
    validator,
    executor,
    cases: list[dict],
    threshold: float,
    fallback_action_id: str | None,
) -> list[dict]:
    from kvrm_core.runtime import KVRMRuntime
    from kvrm_core.types import DecisionInput

    runtime = KVRMRuntime(
        registry=registry,
        selector=selector,
        validator=validator,
        executor=executor,
        threshold=threshold,
        fallback_action_id=fallback_action_id,
    )
    results: list[dict] = []
    for case in cases:
        decision = runtime.decide_and_execute(
            DecisionInput(
                case_id=case["case_id"],
                features=case["input_features"],
                supported=case.get("supported", True),
                ood=case.get("ood", False),
                expected_action_id=case.get("expected_action_id"),
            )
        )
        results.append(
            {
                "case_id": decision.case_id,
                "selected_action_id": decision.selected_action_id,
                "expected_action_id": case.get("expected_action_id"),
                "confidence": decision.confidence,
                "valid": decision.valid,
                "correct": decision.correct,
                "abstained": decision.abstained,
                "fallback_used": decision.fallback_used,
                "final_status": decision.final_status.value,
                "latency_ms": decision.latency_ms,
                "supported": case.get("supported", True),
                "ood": case.get("ood", False),
            }
        )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a compact KVRM selector and evaluate it.")
    parser.add_argument("--domain", required=True, choices=["soc", "sre", "drone", "grid", "finance", "medical", "iam"])
    parser.add_argument("--registry", required=True)
    parser.add_argument("--train-cases", required=True)
    parser.add_argument("--eval-cases", required=True)
    parser.add_argument("--output-model", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--n-estimators", type=int, default=256)
    parser.add_argument("--selectors-module")
    parser.add_argument("--executor-module")
    parser.add_argument("--fallback-action-id")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from kvrm_core.learned import CompactLearnedSelector, save_compact_model_artifact, train_compact_model
    from kvrm_core.context_schema import build_registry_unsupported_predicate
    from kvrm_core.registry import load_registry
    from kvrm_core.validation import DeterministicValidator
    from kvrm_bench.metrics import compute_metrics_with_ci

    import importlib

    selectors_module_name, executor_module_name, default_fallback = default_modules_for_domain(args.domain)
    selectors_module_name = args.selectors_module or selectors_module_name
    executor_module_name = args.executor_module or executor_module_name
    fallback_action_id = args.fallback_action_id or default_fallback

    registry_path = Path(args.registry)
    train_cases_path = Path(args.train_cases)
    eval_cases_path = Path(args.eval_cases)
    output_model_path = Path(args.output_model)
    output_report_path = Path(args.output_report)

    registry = load_registry(registry_path)
    train_cases = load_cases(train_cases_path)
    eval_cases = load_cases(eval_cases_path)

    artifact = train_compact_model(
        train_cases=train_cases,
        registry=registry,
        random_state=args.random_state,
        n_estimators=args.n_estimators,
    )
    save_compact_model_artifact(output_model_path, artifact)

    selectors_module = importlib.import_module(selectors_module_name)
    executor_module = importlib.import_module(executor_module_name)
    executor = executor_module.build_executor()
    validator = DeterministicValidator(registry)
    unsupported_predicate = getattr(selectors_module, "_looks_unsupported", None)
    if unsupported_predicate is None:
        unsupported_predicate = build_registry_unsupported_predicate(registry)

    learned_selector = CompactLearnedSelector.from_artifact(
        artifact_path=output_model_path,
        registry=registry,
        unsupported_predicate=unsupported_predicate,
        min_confidence=0.42,
        candidate_floor=0.18,
        top_k=3,
        name=f"{args.domain}_trained_selector",
    )
    learned_results = run_selector_on_cases(
        selector=learned_selector,
        registry=registry,
        validator=validator,
        executor=executor,
        cases=eval_cases,
        threshold=args.threshold,
        fallback_action_id=fallback_action_id,
    )
    learned_metrics = compute_metrics_with_ci(learned_results)

    hybrid_selector = selectors_module.build_hybrid_selector(
        train_cases_path,
        learned_model_path=output_model_path,
    )
    hybrid_results = run_selector_on_cases(
        selector=hybrid_selector,
        registry=registry,
        validator=validator,
        executor=executor,
        cases=eval_cases,
        threshold=args.threshold,
        fallback_action_id=fallback_action_id,
    )
    hybrid_metrics = compute_metrics_with_ci(hybrid_results)

    report = {
        "domain": args.domain,
        "registry": str(registry_path),
        "train_cases": str(train_cases_path),
        "eval_cases": str(eval_cases_path),
        "output_model": str(output_model_path),
        "metadata": artifact["metadata"],
        "selector_only": learned_metrics,
        "hybrid_augmented": hybrid_metrics,
    }

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    output_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"saved model to {output_model_path}")
    print(f"saved report to {output_report_path}")
    print(
        "selector_only "
        f"acc={learned_metrics['semantic_correctness_rate']:.4f} "
        f"fa={learned_metrics['false_accept_rate']:.4f} "
        f"rej={learned_metrics['unsupported_case_rejection_rate']:.4f}"
    )
    print(
        "hybrid_augmented "
        f"acc={hybrid_metrics['semantic_correctness_rate']:.4f} "
        f"fa={hybrid_metrics['false_accept_rate']:.4f} "
        f"rej={hybrid_metrics['unsupported_case_rejection_rate']:.4f}"
    )


if __name__ == "__main__":
    main()
