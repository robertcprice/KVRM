from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .demo import (
    DOMAIN_CONFIG,
    STRATEGY_ORDER,
    build_case_review_queue,
    load_cases,
    run_demo_case_matrix,
)
from .metrics import compute_metrics, compute_regret_metrics

DEFAULT_AMBIGUITY_THRESHOLD = 0.60
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_REPORT_JSON = "ambiguity_regret_report.json"
DEFAULT_REPORT_MD = "ambiguity_regret_report.md"
DEFAULT_SELECTED_FLAGS = (
    "strategy_disagreement",
    "fallback_path",
    "low_confidence",
    "supported_ood",
    "unsupported_case",
    "selector_abstention",
    "hybrid_incorrect",
)


def run_ambiguity_regret_benchmark(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_AMBIGUITY_THRESHOLD,
    learned_model_paths: dict[str, str | Path] | None = None,
    selected_flags: list[str] | tuple[str, ...] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    active_domains = list(domains or DOMAIN_CONFIG.keys())
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)
    active_flags = tuple(selected_flags or DEFAULT_SELECTED_FLAGS)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "selected_flags": list(active_flags),
        "domains": {},
    }

    for domain in active_domains:
        if domain not in DOMAIN_CONFIG:
            raise ValueError(f"unsupported ambiguity domain: {domain}")
        data_dir = repo_root / DOMAIN_CONFIG[domain]["data_dir"]
        all_cases = load_cases(data_dir / "cases.jsonl")
        review_queue = build_case_review_queue(
            repo_root=repo_root,
            domain=domain,
            eval_filename="cases.jsonl",
            threshold=threshold,
            learned_model_path=str(_resolve_learned_model_path(repo_root, domain, learned_model_paths)),
        )
        frontier_rows = [
            row for row in review_queue
            if set(row.get("review_flags", [])).intersection(active_flags)
        ]

        strategies: dict[str, list[dict[str, Any]]] = {strategy: [] for strategy in STRATEGY_ORDER}
        flag_counts: Counter[str] = Counter()
        supported_frontier_count = 0
        unsupported_frontier_count = 0
        ood_supported_frontier_count = 0

        for row in frontier_rows:
            payload_row = run_demo_case_matrix(
                repo_root=repo_root,
                domain=domain,
                eval_filename="cases.jsonl",
                case_index=row["case_index"],
                threshold=threshold,
                learned_model_path=str(_resolve_learned_model_path(repo_root, domain, learned_model_paths)),
            )
            case = payload_row["case"]
            if case.get("supported", True):
                supported_frontier_count += 1
                if case.get("ood", False):
                    ood_supported_frontier_count += 1
            else:
                unsupported_frontier_count += 1
            flag_counts.update(row.get("review_flags", []))
            for strategy_row in payload_row.get("strategy_results", []):
                strategy = strategy_row.get("strategy")
                if strategy not in strategies:
                    continue
                strategies[strategy].append(
                    _decision_payload_to_case_result(case, strategy_row.get("decision") or {})
                )

        strategy_payloads = {
            strategy: {
                "case_count": len(case_results),
                "metrics": compute_metrics(case_results),
                "regret": compute_regret_metrics(case_results),
            }
            for strategy, case_results in strategies.items()
            if case_results
        }
        best_non_hybrid_strategy = _best_non_hybrid_strategy(strategy_payloads)
        hybrid_payload = strategy_payloads["hybrid"]
        baseline_payload = strategy_payloads[best_non_hybrid_strategy]
        payload["domains"][domain] = {
            "total_case_count": len(all_cases),
            "frontier_case_count": len(frontier_rows),
            "frontier_case_rate": (len(frontier_rows) / len(all_cases)) if all_cases else 0.0,
            "supported_frontier_case_count": supported_frontier_count,
            "unsupported_frontier_case_count": unsupported_frontier_count,
            "ood_supported_frontier_case_count": ood_supported_frontier_count,
            "flag_counts": dict(sorted(flag_counts.items())),
            "strategies": strategy_payloads,
            "comparison": {
                "best_non_hybrid_strategy": best_non_hybrid_strategy,
                "hybrid_regret_gain": baseline_payload["regret"]["mean_decision_regret"] - hybrid_payload["regret"]["mean_decision_regret"],
                "hybrid_cost_reduction": baseline_payload["metrics"]["mean_decision_cost"] - hybrid_payload["metrics"]["mean_decision_cost"],
                "hybrid_severe_regret_reduction": baseline_payload["regret"]["severe_regret_rate"] - hybrid_payload["regret"]["severe_regret_rate"],
                "hybrid_supported_abstention_reduction": baseline_payload["regret"]["supported_abstention_regret_rate"] - hybrid_payload["regret"]["supported_abstention_regret_rate"],
            },
        }

    report_paths = write_ambiguity_regret_reports(payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    return payload


def render_ambiguity_regret_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Ambiguity-Regret Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "The ambiguity frontier is derived from the live review-queue heuristic used by the TUI. "
            "Cases enter the slice when they exhibit one or more of the selected high-signal flags: "
            + ", ".join(f"`{flag}`" for flag in payload["selected_flags"])
            + "."
        ),
        "",
        (
            "This benchmark is case-slice-oriented rather than stress-injection-oriented: it measures "
            "how KVRM and its component strategies behave on the real hard cases already present in the "
            "canonical packs, with explicit regret and decision-cost accounting."
        ),
        "",
        "| Domain | Frontier Cases | Rate | Hybrid Regret | Best Non-Hybrid | Baseline Regret | Gain | Hybrid Cost | Baseline Cost | Hybrid Severe | Baseline Severe |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for domain, domain_payload in payload["domains"].items():
        hybrid = domain_payload["strategies"]["hybrid"]
        baseline_name = domain_payload["comparison"]["best_non_hybrid_strategy"]
        baseline = domain_payload["strategies"][baseline_name]
        lines.append(
            "| "
            f"{domain} | "
            f"{domain_payload['frontier_case_count']} | "
            f"{domain_payload['frontier_case_rate']:.4f} | "
            f"{hybrid['regret']['mean_decision_regret']:.4f} | "
            f"{baseline_name} | "
            f"{baseline['regret']['mean_decision_regret']:.4f} | "
            f"{domain_payload['comparison']['hybrid_regret_gain']:.4f} | "
            f"{hybrid['metrics']['mean_decision_cost']:.4f} | "
            f"{baseline['metrics']['mean_decision_cost']:.4f} | "
            f"{hybrid['regret']['severe_regret_rate']:.4f} | "
            f"{baseline['regret']['severe_regret_rate']:.4f} |"
        )
        lines.append(
            f"Flags `{domain}`: "
            + ", ".join(f"{name}={count}" for name, count in domain_payload["flag_counts"].items())
        )
        lines.append(
            f"Slice `{domain}`: supported={domain_payload['supported_frontier_case_count']}, "
            f"unsupported={domain_payload['unsupported_frontier_case_count']}, "
            f"ood_supported={domain_payload['ood_supported_frontier_case_count']}"
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_ambiguity_regret_reports(
    payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / DEFAULT_REPORT_JSON
    report_md = output_dir / DEFAULT_REPORT_MD
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_ambiguity_regret_markdown(payload), encoding="utf-8")
    return {"json": report_json, "md": report_md}


def _decision_payload_to_case_result(case: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case.get("case_id"),
        "expected_action_id": case.get("expected_action_id"),
        "supported": case.get("supported", True),
        "ood": case.get("ood", False),
        "selected_action_id": decision.get("selected_action_id"),
        "confidence": decision.get("confidence"),
        "valid": bool(decision.get("valid", False)),
        "correct": bool(decision.get("correct", False)),
        "abstained": bool(decision.get("abstained", False)),
        "fallback_used": bool(decision.get("fallback_used", False)),
        "latency_ms": float(decision.get("latency_ms", 0.0) or 0.0),
        "final_status": decision.get("final_status"),
        "validation_reason": decision.get("validation_reason"),
    }


def _best_non_hybrid_strategy(strategy_payloads: dict[str, dict[str, Any]]) -> str:
    non_hybrid = {
        strategy: payload
        for strategy, payload in strategy_payloads.items()
        if strategy != "hybrid"
    }
    if not non_hybrid:
        raise ValueError("ambiguity benchmark requires at least one non-hybrid strategy")
    return min(
        non_hybrid,
        key=lambda strategy: (
            non_hybrid[strategy]["regret"]["mean_decision_regret"],
            non_hybrid[strategy]["metrics"]["mean_decision_cost"],
            -non_hybrid[strategy]["metrics"]["semantic_correctness_rate"],
        ),
    )


def _resolve_learned_model_path(
    repo_root: Path,
    domain: str,
    learned_model_paths: dict[str, str | Path] | None,
) -> Path | None:
    if learned_model_paths and domain in learned_model_paths:
        path = Path(learned_model_paths[domain])
        return path if path.exists() else None
    default_path = repo_root / "kvrm-models" / f"{domain}_compact_selector_v1.joblib"
    return default_path if default_path.exists() else None
