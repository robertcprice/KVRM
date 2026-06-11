"""Scale testing for KVRM domains.

Generates 1000+ synthetic cases per domain by systematic feature-space
enumeration and random sampling, then measures throughput and correctness.
"""
from __future__ import annotations

import itertools
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.registry import load_registry
from kvrm_core.support import evaluate_support_spec
from kvrm_core.types import DecisionInput

from .demo import DOMAIN_CONFIG, _cached_runtime_for_strategy
from .metrics import compute_metrics, percentile

DEFAULT_SCALE_THRESHOLD = 0.60
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_REPORT_JSON = "scale_benchmark_report.json"
DEFAULT_REPORT_MD = "scale_benchmark_report.md"


# ---------------------------------------------------------------------------
# Feature-space enumeration
# ---------------------------------------------------------------------------


def _enumerate_feature_values(context_schema: dict[str, dict[str, Any]]) -> dict[str, list[Any]]:
    """Build a map of feature name to all possible discrete values.

    For enum fields, all enum members are included.  For booleans, True/False.
    Numeric and other field types are skipped (not enumerable in a finite
    product).
    """
    feature_values: dict[str, list[Any]] = {}
    for feature_name, field_spec in context_schema.items():
        field_type = field_spec.get("type")
        if "enum" in field_spec:
            feature_values[feature_name] = list(field_spec["enum"])
        elif field_type == "boolean":
            feature_values[feature_name] = [True, False]
        elif field_type == "integer":
            minimum = field_spec.get("minimum")
            maximum = field_spec.get("maximum")
            if minimum is not None and maximum is not None and (maximum - minimum) <= 20:
                feature_values[feature_name] = list(range(minimum, maximum + 1))
            elif minimum is not None and maximum is not None:
                # Sample representative values for large integer ranges
                step = max(1, (maximum - minimum) // 10)
                feature_values[feature_name] = list(range(minimum, maximum + 1, step))
                if maximum not in feature_values[feature_name]:
                    feature_values[feature_name].append(maximum)
            else:
                # Cannot enumerate unbounded integers; skip
                continue
        elif field_type == "number":
            minimum = field_spec.get("minimum")
            maximum = field_spec.get("maximum")
            if minimum is not None and maximum is not None:
                span = float(maximum) - float(minimum)
                feature_values[feature_name] = [
                    round(float(minimum) + span * i / 10.0, 6) for i in range(11)
                ]
            else:
                continue
        else:
            continue
    return feature_values


def _pick_action_for_features(
    registry,
    features: dict[str, Any],
    *,
    exclude_fallback: bool = True,
) -> tuple[str | None, int]:
    """Evaluate all actions and return (best_action_id, n_satisfied).

    When multiple non-fallback actions match, picks using tag priority:
    ``stable`` > untagged > ``fallback``.  Ties broken by alphabetical
    action_id for determinism.
    """
    satisfied: list[tuple[int, str]] = []
    for action in registry.actions:
        if exclude_fallback and "fallback" in action.tags:
            continue
        ok, _ = evaluate_support_spec(action.support_spec, features)
        if ok:
            if "stable" in action.tags:
                priority = 0
            elif "fallback" in action.tags:
                priority = 2
            else:
                priority = 1
            satisfied.append((priority, action.action_id))
    satisfied.sort()
    if not satisfied:
        return (None, 0)
    return (satisfied[0][1], len(satisfied))


# ---------------------------------------------------------------------------
# Case generation
# ---------------------------------------------------------------------------


def generate_scale_test_cases(
    *,
    repo_root: str | Path,
    domain: str,
    target_count: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    """Generate synthetic evaluation cases via feature-space enumeration.

    If the full cartesian product of enumerable features is smaller than
    *target_count*, all combinations are included.  Otherwise a random
    sample of *target_count* is drawn.

    Each case is labelled with the expected action determined by evaluating
    every action's ``support_spec`` against the feature set.
    """
    repo_root = Path(repo_root)
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported scale domain: {domain}")

    data_dir = repo_root / DOMAIN_CONFIG[domain]["data_dir"]
    registry = load_registry(data_dir / "registry.json")
    feature_values = _enumerate_feature_values(registry.context_schema)

    if not feature_values:
        return {
            "domain": domain,
            "total_feature_space_size": 0,
            "generated_case_count": 0,
            "supported_case_count": 0,
            "unsupported_case_count": 0,
            "multi_action_case_count": 0,
            "cases": [],
        }

    feature_names = sorted(feature_values.keys())
    value_lists = [feature_values[name] for name in feature_names]

    # Compute total feature-space size (may be very large)
    total_space_size = 1
    for vl in value_lists:
        total_space_size *= len(vl)

    rng = random.Random(seed)

    if total_space_size <= target_count:
        # Include every combination
        combos = list(itertools.product(*value_lists))
    else:
        # Random sample without replacement via index-based sampling
        indices = rng.sample(range(total_space_size), target_count)
        combos = []
        sizes = [len(vl) for vl in value_lists]
        for idx in indices:
            combo: list[Any] = []
            remaining = idx
            for size in sizes:
                combo.append(value_lists[len(combo)][remaining % size])
                remaining //= size
            combos.append(tuple(combo))

    cases: list[dict[str, Any]] = []
    supported_count = 0
    unsupported_count = 0
    multi_action_count = 0

    for i, combo in enumerate(combos):
        features = dict(zip(feature_names, combo))
        expected_action_id, n_satisfied = _pick_action_for_features(registry, features)
        case_supported = expected_action_id is not None

        if case_supported:
            supported_count += 1
        else:
            unsupported_count += 1
        if n_satisfied >= 2:
            multi_action_count += 1

        cases.append({
            "case_id": f"scale_{domain}_{i:06d}",
            "expected_action_id": expected_action_id,
            "input_features": features,
            "supported": case_supported,
            "ood": True,
            "multi_action": n_satisfied >= 2,
            "competing_action_count": n_satisfied,
        })

    return {
        "domain": domain,
        "total_feature_space_size": total_space_size,
        "generated_case_count": len(cases),
        "supported_case_count": supported_count,
        "unsupported_case_count": unsupported_count,
        "multi_action_case_count": multi_action_count,
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def run_scale_benchmark(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    target_count: int = 1000,
    threshold: float = DEFAULT_SCALE_THRESHOLD,
    learned_model_paths: dict[str, str | Path] | None = None,
    output_dir: str | Path | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Run hybrid strategy on scale-test cases and measure throughput.

    Measures per-case latency, aggregate throughput, and correctness metrics
    for each domain.
    """
    repo_root = Path(repo_root)
    active_domains = list(domains or DOMAIN_CONFIG.keys())
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domains": {},
        "summary": {},
    }

    total_cases = 0
    total_elapsed_ms = 0.0
    all_perfect = True

    for domain in active_domains:
        if domain not in DOMAIN_CONFIG:
            raise ValueError(f"unsupported scale domain: {domain}")

        generated = generate_scale_test_cases(
            repo_root=repo_root,
            domain=domain,
            target_count=target_count,
            seed=seed,
        )
        cases = generated["cases"]
        if not cases:
            continue

        learned_model_path = _resolve_learned_model_path(repo_root, domain, learned_model_paths)
        result = _cached_runtime_for_strategy(
            str(repo_root),
            domain,
            "cases.jsonl",
            "hybrid",
            str(learned_model_path) if learned_model_path is not None else None,
            threshold,
        )
        runtime = result[0] if result else None
        if runtime is None:
            continue

        case_results: list[dict[str, Any]] = []
        per_case_latencies_ms: list[float] = []

        wall_start = time.perf_counter()
        for case in cases:
            t0 = time.perf_counter()
            decision = runtime.decide_and_execute(
                DecisionInput(
                    case_id=case["case_id"],
                    features=case["input_features"],
                    supported=case.get("supported", True),
                    ood=case.get("ood", False),
                    expected_action_id=case.get("expected_action_id"),
                )
            )
            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000.0
            per_case_latencies_ms.append(elapsed_ms)
            case_results.append(_decision_to_case_result(case, decision.model_dump(mode="json")))
        wall_end = time.perf_counter()

        domain_elapsed_ms = (wall_end - wall_start) * 1000.0
        domain_throughput = (len(cases) / domain_elapsed_ms * 1000.0) if domain_elapsed_ms > 0 else 0.0
        mean_latency = sum(per_case_latencies_ms) / len(per_case_latencies_ms) if per_case_latencies_ms else 0.0

        correctness = compute_metrics(case_results)
        if correctness.get("semantic_correctness_rate", 0.0) < 1.0:
            all_perfect = False

        payload["domains"][domain] = {
            "case_count": len(cases),
            "total_feature_space_size": generated["total_feature_space_size"],
            "supported_case_count": generated["supported_case_count"],
            "unsupported_case_count": generated["unsupported_case_count"],
            "multi_action_case_count": generated["multi_action_case_count"],
            "correctness": correctness,
            "latency": {
                "total_elapsed_ms": round(domain_elapsed_ms, 3),
                "throughput_decisions_per_sec": round(domain_throughput, 2),
                "p50_ms": round(percentile(per_case_latencies_ms, 50), 4),
                "p95_ms": round(percentile(per_case_latencies_ms, 95), 4),
                "p99_ms": round(percentile(per_case_latencies_ms, 99), 4),
                "max_ms": round(max(per_case_latencies_ms) if per_case_latencies_ms else 0.0, 4),
                "mean_ms": round(mean_latency, 4),
            },
        }
        total_cases += len(cases)
        total_elapsed_ms += domain_elapsed_ms

    overall_throughput = (total_cases / total_elapsed_ms * 1000.0) if total_elapsed_ms > 0 else 0.0
    payload["summary"] = {
        "total_cases": total_cases,
        "total_elapsed_ms": round(total_elapsed_ms, 3),
        "overall_throughput_decisions_per_sec": round(overall_throughput, 2),
        "all_domains_perfect": all_perfect,
    }

    report_paths = write_scale_benchmark_reports(payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    return payload


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_scale_benchmark_markdown(payload: dict[str, Any]) -> str:
    """Render a markdown report from scale benchmark results."""
    summary = payload["summary"]
    lines = [
        "# KVRM Scale Benchmark Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "This benchmark generates 1000+ synthetic cases per domain by enumerating the full "
            "feature space (cartesian product of enum and boolean values) and random-sampling "
            "when the space exceeds the target count.  Each case is labelled by evaluating every "
            "action's support_spec."
        ),
        "",
        f"**Total cases**: {summary['total_cases']}  ",
        f"**Total elapsed**: {summary['total_elapsed_ms']:.1f} ms  ",
        f"**Overall throughput**: {summary['overall_throughput_decisions_per_sec']:.1f} decisions/sec  ",
        f"**All domains perfect**: {summary['all_domains_perfect']}",
        "",
        "## Per-Domain Results",
        "",
        "| Domain | Cases | Feature Space | Supported | Unsupported | Multi-Action | Correctness | Throughput |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for domain, dp in payload["domains"].items():
        corr = dp["correctness"]
        lat = dp["latency"]
        lines.append(
            "| "
            f"{domain} | "
            f"{dp['case_count']} | "
            f"{dp['total_feature_space_size']} | "
            f"{dp['supported_case_count']} | "
            f"{dp['unsupported_case_count']} | "
            f"{dp['multi_action_case_count']} | "
            f"{corr.get('semantic_correctness_rate', 0.0):.4f} | "
            f"{lat['throughput_decisions_per_sec']:.1f}/s |"
        )

    lines.append("")
    lines.append("## Latency Profile")
    lines.append("")
    lines.append("| Domain | Mean | P50 | P95 | P99 | Max |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")

    for domain, dp in payload["domains"].items():
        lat = dp["latency"]
        lines.append(
            "| "
            f"{domain} | "
            f"{lat['mean_ms']:.4f} ms | "
            f"{lat['p50_ms']:.4f} ms | "
            f"{lat['p95_ms']:.4f} ms | "
            f"{lat['p99_ms']:.4f} ms | "
            f"{lat['max_ms']:.4f} ms |"
        )

    return "\n".join(lines) + "\n"


def write_scale_benchmark_reports(
    payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write JSON and markdown reports to *output_dir*."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / DEFAULT_REPORT_JSON
    report_md = output_dir / DEFAULT_REPORT_MD
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_scale_benchmark_markdown(payload), encoding="utf-8")
    return {"json": report_json, "md": report_md}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decision_to_case_result(case: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
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
