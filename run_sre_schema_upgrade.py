from __future__ import annotations

import argparse
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def load_cases(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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
    parser = argparse.ArgumentParser(description="Compare SRE v3 vs v4 schema performance.")
    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument(
        "--output",
        default="kvrm-bench/results/sre_schema_upgrade_report.json",
        help="JSON report path relative to repo root.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from kvrm_bench.ceiling import analyze_domain
    from kvrm_bench.metrics import compute_metrics_with_ci
    from kvrm_core.registry import load_registry
    from kvrm_core.validation import DeterministicValidator
    from sre_policy_router.executor import build_executor
    from sre_policy_router.selectors import build_hybrid_selector

    data_dir = BASE_DIR / "kvrm-demos" / "sre-policy-router" / "data"
    paths = {
        "v3": {
            "registry": data_dir / "registry.json",
            "train": data_dir / "train_cases.jsonl",
            "eval": data_dir / "cases_v3.jsonl",
        },
        "v4": {
            "registry": data_dir / "registry_v4.json",
            "train": data_dir / "train_cases_v4.jsonl",
            "eval": data_dir / "cases_v4.jsonl",
        },
    }

    for label, config in paths.items():
        missing = [str(path) for path in config.values() if not path.exists()]
        if missing:
            raise FileNotFoundError(f"{label} inputs missing: {', '.join(missing)}")

    executor = build_executor()
    comparison: dict[str, dict] = {}
    for label, config in paths.items():
        registry = load_registry(config["registry"])
        validator = DeterministicValidator(registry)
        selector = build_hybrid_selector(config["train"])
        cases = load_cases(config["eval"])
        results = run_selector_on_cases(
            selector=selector,
            registry=registry,
            validator=validator,
            executor=executor,
            cases=cases,
            threshold=args.threshold,
            fallback_action_id="page_human_operator",
        )
        comparison[label] = {
            "metrics": compute_metrics_with_ci(results),
            "ceiling": analyze_domain(
                domain_name="sre",
                registry_path=config["registry"],
                cases_path=config["eval"],
            ),
        }

    report = {
        "domain": "sre",
        "threshold": args.threshold,
        "v3": comparison["v3"],
        "v4": comparison["v4"],
        "delta": {
            "semantic_correctness_rate": comparison["v4"]["metrics"]["semantic_correctness_rate"]
            - comparison["v3"]["metrics"]["semantic_correctness_rate"],
            "false_accept_rate": comparison["v4"]["metrics"]["false_accept_rate"]
            - comparison["v3"]["metrics"]["false_accept_rate"],
            "exact_feature_oracle_accuracy": comparison["v4"]["ceiling"]["exact_feature_oracle_accuracy"]
            - comparison["v3"]["ceiling"]["exact_feature_oracle_accuracy"],
        },
    }

    output_path = BASE_DIR / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"saved report to {output_path}")
    print(
        f"v3 acc={comparison['v3']['metrics']['semantic_correctness_rate']:.4f} "
        f"oracle={comparison['v3']['ceiling']['exact_feature_oracle_accuracy']:.4f}"
    )
    print(
        f"v4 acc={comparison['v4']['metrics']['semantic_correctness_rate']:.4f} "
        f"oracle={comparison['v4']['ceiling']['exact_feature_oracle_accuracy']:.4f}"
    )


if __name__ == "__main__":
    main()
