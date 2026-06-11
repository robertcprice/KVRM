"""Run proxy and Ollama-backed baseline evaluation on the live KVRM suite."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .classifier import (
    BaselineResult,
    ConstrainedClassifier,
    DirectLabelClassifier,
    JsonActionClassifier,
)
from .data_loader import DOMAIN_ORDER, load_domain_data
from .ollama_runner import OllamaJsonBaseline


DEFAULT_DECISION_COSTS = {
    "supported_correct": 0.0,
    "supported_abstain": 0.35,
    "supported_misroute": 1.0,
    "unsupported_safe_reject": 0.0,
    "unsupported_false_accept": 1.25,
}


def compute_baseline_metrics(
    results: list[BaselineResult] | list[dict[str, Any]],
    eval_cases: list[dict] | None = None,
) -> dict[str, Any]:
    """Compute metrics aligned with the live KVRM benchmark outputs."""
    case_results = _coerce_case_results(results, eval_cases)
    total = len(case_results)
    supported_cases = [r for r in case_results if r.get("supported", True)]
    unsupported_cases = [r for r in case_results if not r.get("supported", True)]
    ood_supported_cases = [
        r for r in case_results
        if r.get("supported", True) and r.get("ood", False)
    ]

    def rate(items, predicate):
        if not items:
            return 0.0
        return sum(1 for item in items if predicate(item)) / len(items)

    latencies = [float(r.get("latency_ms", 0.0)) for r in case_results]
    return {
        "total_cases": total,
        "supported_cases": len(supported_cases),
        "unsupported_cases": len(unsupported_cases),
        "structural_validity_rate": rate(case_results, lambda r: bool(r.get("valid", False))),
        "semantic_correctness_rate": rate(supported_cases, lambda r: bool(r.get("correct", False))),
        "abstention_rate": rate(case_results, lambda r: bool(r.get("abstained", False))),
        "fallback_rate": rate(case_results, lambda r: bool(r.get("fallback_used", False))),
        "invalid_output_rate": rate(case_results, lambda r: not bool(r.get("valid", False))),
        "false_accept_rate": rate(unsupported_cases, lambda r: r.get("final_status") == "executed"),
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
        "latency_p99_ms": _percentile(latencies, 99),
        "calibration_ece": _compute_ece(case_results),
        "ood_accuracy_supported_only": rate(ood_supported_cases, lambda r: bool(r.get("correct", False))),
        "unsupported_case_rejection_rate": rate(
            unsupported_cases,
            lambda r: r.get("final_status") in {"abstained", "fallback_executed", "fail_closed"},
        ),
        "support_gate_trigger_rate": 0.0,
        "supported_support_gate_rescue_rate": 0.0,
        "unsupported_support_gate_short_circuit_rate": 0.0,
        "support_gate_exhausted_rate": 0.0,
        "mean_decision_cost": _mean_decision_cost(case_results),
        "supported_mean_decision_cost": _mean_decision_cost(supported_cases),
        "unsupported_mean_decision_cost": _mean_decision_cost(unsupported_cases),
    }


def run_single_baseline(domain: str, variant: str, output_dir: Path) -> dict[str, Any]:
    """Train and evaluate one sklearn proxy baseline variant on one domain."""
    data = load_domain_data(domain)
    train_cases = data["train"]
    eval_cases = data["eval_all"]
    train_supported = [c for c in train_cases if c.get("expected_action_id") is not None]

    if variant == "direct_label":
        classifier = DirectLabelClassifier(domain=domain)
    elif variant == "json_action":
        classifier = JsonActionClassifier(domain=domain, threshold=0.60)
    elif variant == "constrained":
        classifier = ConstrainedClassifier(domain=domain)
    else:
        raise ValueError(f"Unknown variant: {variant}")

    classifier.train(train_supported)
    proxy_results = [classifier.predict(case) for case in eval_cases]
    case_results = _coerce_case_results(proxy_results, eval_cases)
    metrics = compute_baseline_metrics(case_results)

    output_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "domain": domain,
        "variant": variant,
        "runner": "proxy",
        "train_cases": len(train_supported),
        "eval_cases": len(eval_cases),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "config.json").write_text(json.dumps(config, indent=2))
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    _write_jsonl(output_dir / "per_case_results.jsonl", case_results)

    return {
        "domain": domain,
        "variant": variant,
        "metrics": metrics,
        "per_case": case_results,
    }


def run_all_baselines(output_root: Path | None = None) -> dict[str, Any]:
    """Run the historical proxy baselines across the live domains."""
    if output_root is None:
        output_root = Path(__file__).resolve().parents[2] / "outputs" / "proxy"

    all_results: dict[str, Any] = {}
    for domain in DOMAIN_ORDER:
        domain_results = {}
        for variant in ["direct_label", "json_action", "constrained"]:
            out_dir = output_root / domain / f"qwen_{variant}"
            result = run_single_baseline(domain, variant, out_dir)
            domain_results[variant] = result["metrics"]
        all_results[domain] = domain_results
    return all_results


def run_ollama_baseline(
    *,
    domain: str,
    model: str,
    output_dir: Path,
    variant: str = "abstain_json",
    refresh: bool = False,
    max_cases: int | None = None,
    max_examples_per_action: int = 1,
) -> dict[str, Any]:
    """Run a real Ollama-backed baseline on one live canonical domain pack."""
    data = load_domain_data(domain)
    train_cases = data["train"]
    eval_cases = data["eval_all"]
    if max_cases is not None:
        eval_cases = eval_cases[:max_cases]

    output_dir.mkdir(parents=True, exist_ok=True)
    per_case_path = output_dir / "per_case_results.jsonl"
    existing_records = {} if refresh else _load_case_records(per_case_path)
    runner = OllamaJsonBaseline(
        domain=domain,
        model=model,
        train_cases=train_cases,
        variant=variant,
        max_examples_per_action=max_examples_per_action,
    )

    case_results: list[dict[str, Any]] = []
    for case in eval_cases:
        cached = existing_records.get(case["case_id"])
        if cached is not None:
            case_results.append(cached)
            continue
        result = runner.predict(case).to_dict()
        case_results.append(result)
        existing_records[case["case_id"]] = result
        _append_jsonl(per_case_path, result)

    ordered_results = [existing_records[case["case_id"]] for case in eval_cases]
    metrics = compute_baseline_metrics(ordered_results)
    config = {
        "domain": domain,
        "model": model,
        "variant": variant,
        "runner": "ollama",
        "registry_version": data["registry"]["version"],
        "train_cases": len(train_cases),
        "eval_cases": len(eval_cases),
        "max_examples_per_action": max_examples_per_action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "refresh": refresh,
    }
    (output_dir / "config.json").write_text(json.dumps(config, indent=2))
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    _write_jsonl(per_case_path, ordered_results)
    (output_dir / "summary.md").write_text(
        _build_summary_markdown(domain=domain, model=model, variant=variant, metrics=metrics)
    )

    return {
        "domain": domain,
        "model": model,
        "variant": variant,
        "metrics": metrics,
        "per_case": ordered_results,
    }


def load_ollama_artifact(
    output_dir: Path,
    *,
    require_cases: bool = False,
) -> dict[str, Any] | None:
    config_path = output_dir / "config.json"
    metrics_path = output_dir / "metrics.json"
    per_case_path = output_dir / "per_case_results.jsonl"
    if not config_path.exists() or not metrics_path.exists():
        return None
    if require_cases and not per_case_path.exists():
        return None
    config = json.loads(config_path.read_text())
    metrics = json.loads(metrics_path.read_text())
    per_case = _load_case_records(per_case_path) if per_case_path.exists() else {}
    return {
        "domain": config["domain"],
        "model": config["model"],
        "variant": config["variant"],
        "config": config,
        "metrics": metrics,
        "per_case": list(per_case.values()),
    }


def _coerce_case_results(
    results: list[BaselineResult] | list[dict[str, Any]],
    eval_cases: list[dict] | None = None,
) -> list[dict[str, Any]]:
    if results and isinstance(results[0], dict):
        return [dict(result) for result in results]
    if eval_cases is None:
        raise ValueError("eval_cases are required when converting BaselineResult objects")
    case_map = {case["case_id"]: case for case in eval_cases}
    case_results = []
    for result in results:
        case = case_map[result.case_id]
        case_results.append(
            {
                "case_id": result.case_id,
                "selected_action_id": result.predicted_action_id,
                "expected_action_id": case.get("expected_action_id"),
                "confidence": result.confidence,
                "valid": result.valid,
                "correct": result.correct,
                "abstained": result.abstained,
                "fallback_used": result.fallback_used,
                "final_status": result.final_status,
                "latency_ms": result.latency_ms,
                "supported": bool(case.get("supported", True)),
                "ood": bool(case.get("ood", False)),
                "variant": result.variant,
            }
        )
    return case_results


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _load_case_records(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    records: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            records[row["case_id"]] = row
    return records


def _build_summary_markdown(
    *,
    domain: str,
    model: str,
    variant: str,
    metrics: dict[str, Any],
) -> str:
    lines = [
        f"# {domain.upper()} - {model} ({variant})",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    keys = [
        "semantic_correctness_rate",
        "false_accept_rate",
        "unsupported_case_rejection_rate",
        "invalid_output_rate",
        "ood_accuracy_supported_only",
        "abstention_rate",
        "mean_decision_cost",
        "latency_p50_ms",
        "latency_p95_ms",
    ]
    for key in keys:
        value = metrics.get(key, 0.0)
        lines.append(f"| {key} | {value:.4f} |")
    return "\n".join(lines) + "\n"


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = max(0, min(len(values) - 1, int((q / 100.0) * len(values) + 0.999999) - 1))
    return float(values[index])


def _compute_ece(case_results: list[dict[str, Any]], n_bins: int = 10) -> float:
    confident_cases = [r for r in case_results if r.get("confidence") is not None]
    if not confident_cases:
        return 0.0
    ece = 0.0
    bin_size = 1.0 / n_bins
    total = len(confident_cases)
    for index in range(n_bins):
        lo = index * bin_size
        hi = (index + 1) * bin_size
        bin_cases = [
            r for r in confident_cases
            if lo <= float(r.get("confidence", 0.0)) < hi
        ]
        if not bin_cases:
            continue
        bin_accuracy = sum(1 for r in bin_cases if bool(r.get("correct", False))) / len(bin_cases)
        bin_confidence = sum(float(r.get("confidence", 0.0)) for r in bin_cases) / len(bin_cases)
        ece += (len(bin_cases) / total) * abs(bin_accuracy - bin_confidence)
    return ece


def _mean_decision_cost(case_results: list[dict[str, Any]]) -> float:
    if not case_results:
        return 0.0
    return sum(_decision_cost(case_result) for case_result in case_results) / len(case_results)


def _decision_cost(case_result: dict[str, Any]) -> float:
    supported = bool(case_result.get("supported", True))
    final_status = case_result.get("final_status")
    correct = bool(case_result.get("correct", False))

    if supported:
        if correct:
            return DEFAULT_DECISION_COSTS["supported_correct"]
        if final_status in {"abstained", "fallback_executed", "fail_closed"}:
            return DEFAULT_DECISION_COSTS["supported_abstain"]
        return DEFAULT_DECISION_COSTS["supported_misroute"]

    if final_status == "executed":
        return DEFAULT_DECISION_COSTS["unsupported_false_accept"]
    return DEFAULT_DECISION_COSTS["unsupported_safe_reject"]

