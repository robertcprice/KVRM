"""Adversarial near-boundary stress testing for KVRM support gates.

Generates cases that are intentionally close to support-spec boundaries:
1. N-1 of N conditions satisfied (single-condition miss)
2. Features one step away from enum boundaries
3. Cases where multiple actions have nearly identical support compliance
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.registry import load_registry
from kvrm_core.support import evaluate_support_spec
from kvrm_core.types import DecisionInput

from .demo import DOMAIN_CONFIG, STRATEGY_ORDER, _cached_runtime_for_strategy, load_cases
from .metrics import compute_metrics

DEFAULT_ADVERSARIAL_THRESHOLD = 0.60
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_REPORT_JSON = "adversarial_stress_report.json"
DEFAULT_REPORT_MD = "adversarial_stress_report.md"


# ---------------------------------------------------------------------------
# Leaf-level support_spec traversal
# ---------------------------------------------------------------------------


def _flatten_all_leaves(spec: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return all leaf conditions from a support_spec tree.

    Only traverses into ``all`` nodes (conjunctions) so that each leaf
    represents one independently flippable condition.  ``any`` and ``not``
    subtrees are returned as single opaque leaves.
    """
    if spec is None:
        return []
    if "feature" in spec:
        return [spec]
    if "all" in spec:
        leaves: list[dict[str, Any]] = []
        for child in spec["all"]:
            leaves.extend(_flatten_all_leaves(child))
        return leaves
    # any / not blocks are treated as opaque single leaves
    return [spec]


def _negate_leaf(leaf: dict[str, Any], features: dict[str, Any], schema: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Return mutated *features* dict that fails a single leaf condition.

    Returns ``None`` if the leaf cannot be trivially negated (e.g. complex
    ``any``/``not`` subtrees without a ``feature`` key).
    """
    if "feature" not in leaf:
        return None

    feature_name = leaf["feature"]
    op = leaf.get("op")
    value = leaf.get("value")
    field_spec = schema.get(feature_name, {})

    negated_value = _pick_negated_value(feature_name, op, value, features.get(feature_name), field_spec)
    if negated_value is _SENTINEL:
        return None

    mutated = dict(features)
    mutated[feature_name] = negated_value
    return mutated


_SENTINEL = object()


def _pick_negated_value(
    feature_name: str,
    op: str | None,
    spec_value: Any,
    current_value: Any,
    field_spec: dict[str, Any],
) -> Any:
    """Pick a feature value that causes the given leaf to evaluate to False."""
    enum_values = field_spec.get("enum")
    field_type = field_spec.get("type")

    if op == "eq":
        if isinstance(spec_value, bool):
            return not spec_value
        if enum_values:
            for v in enum_values:
                if v != spec_value:
                    return v
        return _SENTINEL

    if op == "neq":
        return spec_value

    if op == "in" and isinstance(spec_value, list):
        if enum_values:
            for v in enum_values:
                if v not in spec_value:
                    return v
        return _SENTINEL

    if op == "not_in" and isinstance(spec_value, list):
        if spec_value:
            return spec_value[0]
        return _SENTINEL

    if op in {"gt", "gte", "lt", "lte"} and isinstance(spec_value, (int, float)):
        minimum = field_spec.get("minimum")
        maximum = field_spec.get("maximum")
        if op == "gt":
            candidate = spec_value if isinstance(spec_value, int) else spec_value
            if minimum is not None and candidate < minimum:
                return _SENTINEL
            return candidate
        if op == "gte":
            candidate = spec_value - 1 if isinstance(spec_value, int) else spec_value - 0.01
            if minimum is not None and candidate < minimum:
                return _SENTINEL
            return candidate
        if op == "lt":
            candidate = spec_value if isinstance(spec_value, int) else spec_value
            if maximum is not None and candidate > maximum:
                return _SENTINEL
            return candidate
        if op == "lte":
            candidate = spec_value + 1 if isinstance(spec_value, int) else spec_value + 0.01
            if maximum is not None and candidate > maximum:
                return _SENTINEL
            return candidate

    return _SENTINEL


# ---------------------------------------------------------------------------
# Enum boundary stepping
# ---------------------------------------------------------------------------


def _adjacent_enum_values(current_value: Any, enum_values: list[Any]) -> list[Any]:
    """Return enum values one ordinal step away from *current_value*."""
    if current_value not in enum_values:
        return []
    idx = enum_values.index(current_value)
    neighbors: list[Any] = []
    if idx > 0:
        neighbors.append(enum_values[idx - 1])
    if idx < len(enum_values) - 1:
        neighbors.append(enum_values[idx + 1])
    return neighbors


# ---------------------------------------------------------------------------
# Multi-action competition scoring
# ---------------------------------------------------------------------------


def _count_satisfied_actions(
    registry,
    features: dict[str, Any],
    *,
    exclude_fallback: bool = True,
) -> tuple[int, list[str]]:
    """Count how many non-fallback actions are support-satisfied by *features*."""
    satisfied: list[str] = []
    for action in registry.actions:
        if exclude_fallback and "fallback" in action.tags:
            continue
        ok, _ = evaluate_support_spec(action.support_spec, features)
        if ok:
            satisfied.append(action.action_id)
    return len(satisfied), satisfied


# ---------------------------------------------------------------------------
# Primary generation
# ---------------------------------------------------------------------------


def generate_adversarial_near_boundary_cases(
    *,
    repo_root: str | Path,
    domain: str,
) -> dict[str, Any]:
    """Generate adversarial near-boundary cases for a single domain.

    Mutation types:
    - ``single_condition_miss``: flip one leaf condition in the matching
      action's support_spec so the case *almost* passes.
    - ``boundary_step``: step each enum feature to adjacent ordinal value and
      check whether support status changes.
    - ``multi_action_competition``: find feature sets where 2+ actions are
      simultaneously satisfied.

    Returns a dict with metadata and a ``cases`` list.
    """
    repo_root = Path(repo_root)
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported adversarial domain: {domain}")

    data_dir = repo_root / DOMAIN_CONFIG[domain]["data_dir"]
    registry = load_registry(data_dir / "registry.json")
    base_cases = [c for c in load_cases(data_dir / "cases.jsonl") if c.get("supported", True)]
    action_map = {a.action_id: a for a in registry.actions}

    generated: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    single_miss_count = 0
    boundary_step_count = 0
    multi_action_count = 0

    for base_case in base_cases:
        base_features = base_case["input_features"]
        base_action_id = base_case.get("expected_action_id")
        action_spec = action_map.get(base_action_id) if base_action_id else None

        # --- 1. Single-condition miss ---
        if action_spec and action_spec.support_spec:
            leaves = _flatten_all_leaves(action_spec.support_spec)
            for leaf in leaves:
                feature_name = leaf.get("feature")
                if feature_name is None:
                    continue
                mutated_features = _negate_leaf(leaf, base_features, registry.context_schema)
                if mutated_features is None:
                    continue

                dedupe = json.dumps(mutated_features, sort_keys=True)
                if dedupe in seen_keys:
                    continue
                seen_keys.add(dedupe)

                supported, _ = evaluate_support_spec(action_spec.support_spec, mutated_features)
                # Find which action (if any) now matches
                expected_action_id = None
                if not supported:
                    # Check other non-fallback actions
                    for other_action in registry.actions:
                        if "fallback" in other_action.tags:
                            continue
                        ok, _ = evaluate_support_spec(other_action.support_spec, mutated_features)
                        if ok:
                            expected_action_id = other_action.action_id
                            break
                else:
                    expected_action_id = base_action_id

                n_competing, _ = _count_satisfied_actions(registry, mutated_features)
                case_supported = expected_action_id is not None

                case_id = f"adv_{base_case['case_id']}:single_condition_miss:{feature_name}"
                generated.append({
                    "case_id": case_id,
                    "base_case_id": base_case["case_id"],
                    "mutation_type": "single_condition_miss",
                    "mutated_feature": feature_name,
                    "from_value": base_features.get(feature_name),
                    "to_value": mutated_features.get(feature_name),
                    "base_action_id": base_action_id,
                    "expected_action_id": expected_action_id,
                    "supported": case_supported,
                    "ood": True,
                    "input_features": mutated_features,
                    "competing_action_count": n_competing,
                })
                single_miss_count += 1

        # --- 2. Boundary enum step ---
        for feature_name, field_spec in registry.context_schema.items():
            enum_values = field_spec.get("enum")
            if not enum_values:
                continue
            current_value = base_features.get(feature_name)
            if current_value is None:
                continue

            for neighbor_value in _adjacent_enum_values(current_value, enum_values):
                mutated_features = dict(base_features)
                mutated_features[feature_name] = neighbor_value

                dedupe = json.dumps(mutated_features, sort_keys=True)
                if dedupe in seen_keys:
                    continue
                seen_keys.add(dedupe)

                # Determine expected action
                expected_action_id = None
                for action in registry.actions:
                    if "fallback" in action.tags:
                        continue
                    ok, _ = evaluate_support_spec(action.support_spec, mutated_features)
                    if ok:
                        expected_action_id = action.action_id
                        break

                n_competing, _ = _count_satisfied_actions(registry, mutated_features)
                case_supported = expected_action_id is not None

                case_id = f"adv_{base_case['case_id']}:boundary_step:{feature_name}"
                generated.append({
                    "case_id": case_id,
                    "base_case_id": base_case["case_id"],
                    "mutation_type": "boundary_step",
                    "mutated_feature": feature_name,
                    "from_value": current_value,
                    "to_value": neighbor_value,
                    "base_action_id": base_action_id,
                    "expected_action_id": expected_action_id,
                    "supported": case_supported,
                    "ood": True,
                    "input_features": mutated_features,
                    "competing_action_count": n_competing,
                })
                boundary_step_count += 1

        # --- 3. Multi-action competition ---
        n_competing, competing_ids = _count_satisfied_actions(registry, base_features)
        if n_competing >= 2:
            dedupe = json.dumps(base_features, sort_keys=True) + ":multi_action"
            if dedupe not in seen_keys:
                seen_keys.add(dedupe)
                # Pick by tag priority: stable > fallback
                prioritized = _pick_by_tag_priority(registry, competing_ids)
                generated.append({
                    "case_id": f"adv_{base_case['case_id']}:multi_action_competition:_",
                    "base_case_id": base_case["case_id"],
                    "mutation_type": "multi_action_competition",
                    "mutated_feature": None,
                    "from_value": None,
                    "to_value": None,
                    "base_action_id": base_action_id,
                    "expected_action_id": prioritized,
                    "supported": True,
                    "ood": True,
                    "input_features": base_features,
                    "competing_action_count": n_competing,
                })
                multi_action_count += 1

    generated.sort(key=lambda c: (c["base_case_id"], c["mutation_type"], c["case_id"]))

    return {
        "domain": domain,
        "adversarial_case_count": len(generated),
        "single_condition_miss_count": single_miss_count,
        "boundary_step_count": boundary_step_count,
        "multi_action_competition_count": multi_action_count,
        "cases": generated,
    }


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def run_adversarial_stress_benchmark(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_ADVERSARIAL_THRESHOLD,
    learned_model_paths: dict[str, str | Path] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run all strategies on adversarial near-boundary cases.

    Computes per-mutation-type metrics and a hybrid-vs-best-non-hybrid
    comparison for each domain.
    """
    repo_root = Path(repo_root)
    active_domains = list(domains or DOMAIN_CONFIG.keys())
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "domains": {},
        "summary": {},
    }

    hybrid_wins = 0
    hybrid_ties = 0
    hybrid_losses = 0

    for domain in active_domains:
        if domain not in DOMAIN_CONFIG:
            raise ValueError(f"unsupported adversarial domain: {domain}")

        generated = generate_adversarial_near_boundary_cases(repo_root=repo_root, domain=domain)
        cases = generated["cases"]
        learned_model_path = _resolve_learned_model_path(repo_root, domain, learned_model_paths)
        strategy_payloads: dict[str, dict[str, Any]] = {}

        for strategy in STRATEGY_ORDER:
            result = _cached_runtime_for_strategy(
                str(repo_root),
                domain,
                "cases.jsonl",
                strategy,
                str(learned_model_path) if learned_model_path is not None else None,
                threshold,
            )
            runtime = result[0] if result else None
            if runtime is None:
                continue

            all_results: list[dict[str, Any]] = []
            single_miss_results: list[dict[str, Any]] = []
            boundary_step_results: list[dict[str, Any]] = []
            multi_action_results: list[dict[str, Any]] = []

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
                cr = _decision_to_case_result(case, decision.model_dump(mode="json"))
                all_results.append(cr)
                mutation_type = case["mutation_type"]
                if mutation_type == "single_condition_miss":
                    single_miss_results.append(cr)
                elif mutation_type == "boundary_step":
                    boundary_step_results.append(cr)
                elif mutation_type == "multi_action_competition":
                    multi_action_results.append(cr)

            strategy_payloads[strategy] = {
                "metrics": compute_metrics(all_results),
                "single_condition_miss_metrics": compute_metrics(single_miss_results) if single_miss_results else {},
                "boundary_step_metrics": compute_metrics(boundary_step_results) if boundary_step_results else {},
                "multi_action_competition_metrics": compute_metrics(multi_action_results) if multi_action_results else {},
            }

        # Hybrid-vs-best comparison
        best_non_hybrid = _best_non_hybrid_strategy(strategy_payloads)
        hybrid_metrics = strategy_payloads.get("hybrid", {}).get("metrics", {})
        baseline_metrics = strategy_payloads.get(best_non_hybrid, {}).get("metrics", {})

        hybrid_correctness = hybrid_metrics.get("semantic_correctness_rate", 0.0)
        baseline_correctness = baseline_metrics.get("semantic_correctness_rate", 0.0)

        if hybrid_correctness > baseline_correctness:
            hybrid_wins += 1
        elif hybrid_correctness < baseline_correctness:
            hybrid_losses += 1
        else:
            hybrid_ties += 1

        payload["domains"][domain] = {
            "adversarial_case_count": generated["adversarial_case_count"],
            "single_condition_miss_count": generated["single_condition_miss_count"],
            "boundary_step_count": generated["boundary_step_count"],
            "multi_action_competition_count": generated["multi_action_competition_count"],
            "strategies": strategy_payloads,
            "comparison": {
                "best_non_hybrid_strategy": best_non_hybrid,
                "hybrid_correctness_gain": hybrid_correctness - baseline_correctness,
                "hybrid_false_accept_reduction": (
                    baseline_metrics.get("false_accept_rate", 0.0)
                    - hybrid_metrics.get("false_accept_rate", 0.0)
                ),
            },
        }

    payload["summary"] = {
        "domain_count": len(active_domains),
        "hybrid_win_count": hybrid_wins,
        "hybrid_tie_count": hybrid_ties,
        "hybrid_loss_count": hybrid_losses,
    }

    report_paths = write_adversarial_stress_reports(payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    return payload


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_adversarial_stress_markdown(payload: dict[str, Any]) -> str:
    """Render a markdown report from adversarial stress benchmark results."""
    lines = [
        "# KVRM Adversarial Near-Boundary Stress Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "This benchmark generates adversarial cases designed to push KVRM to its limits. "
            "Three mutation types probe boundary behaviour: single-condition miss (flip one leaf "
            "condition), boundary enum step (one ordinal step on each enum feature), and "
            "multi-action competition (feature sets satisfying 2+ actions simultaneously)."
        ),
        "",
        (
            f"Hybrid comparison summary: wins={payload['summary']['hybrid_win_count']}, "
            f"ties={payload['summary']['hybrid_tie_count']}, "
            f"losses={payload['summary']['hybrid_loss_count']}."
        ),
        "",
        "## Per-Domain Results",
        "",
        "| Domain | Adv Cases | Single Miss | Boundary Step | Multi-Action | Hybrid Correctness | Best Non-Hybrid | Baseline Correctness | Gain |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]

    for domain, dp in payload["domains"].items():
        hybrid_metrics = dp["strategies"].get("hybrid", {}).get("metrics", {})
        baseline_name = dp["comparison"]["best_non_hybrid_strategy"]
        baseline_metrics = dp["strategies"].get(baseline_name, {}).get("metrics", {})
        lines.append(
            "| "
            f"{domain} | "
            f"{dp['adversarial_case_count']} | "
            f"{dp['single_condition_miss_count']} | "
            f"{dp['boundary_step_count']} | "
            f"{dp['multi_action_competition_count']} | "
            f"{hybrid_metrics.get('semantic_correctness_rate', 0.0):.4f} | "
            f"{baseline_name} | "
            f"{baseline_metrics.get('semantic_correctness_rate', 0.0):.4f} | "
            f"{dp['comparison']['hybrid_correctness_gain']:.4f} |"
        )

    lines.append("")
    lines.append("## Mutation-Type Breakdown (Hybrid Strategy)")
    lines.append("")
    lines.append("| Domain | Mutation Type | Cases | Correctness | False Accept | Fallback |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")

    for domain, dp in payload["domains"].items():
        hybrid = dp["strategies"].get("hybrid", {})
        for mtype, mkey in [
            ("single_condition_miss", "single_condition_miss_metrics"),
            ("boundary_step", "boundary_step_metrics"),
            ("multi_action_competition", "multi_action_competition_metrics"),
        ]:
            m = hybrid.get(mkey, {})
            if not m:
                continue
            lines.append(
                "| "
                f"{domain} | "
                f"{mtype} | "
                f"{m.get('total_cases', 0)} | "
                f"{m.get('semantic_correctness_rate', 0.0):.4f} | "
                f"{m.get('false_accept_rate', 0.0):.4f} | "
                f"{m.get('fallback_rate', 0.0):.4f} |"
            )

    return "\n".join(lines) + "\n"


def write_adversarial_stress_reports(
    payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write JSON and markdown reports to *output_dir*."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / DEFAULT_REPORT_JSON
    report_md = output_dir / DEFAULT_REPORT_MD
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_adversarial_stress_markdown(payload), encoding="utf-8")
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


def _best_non_hybrid_strategy(strategy_payloads: dict[str, dict[str, Any]]) -> str:
    non_hybrid = {
        strategy: payload
        for strategy, payload in strategy_payloads.items()
        if strategy != "hybrid"
    }
    if not non_hybrid:
        return "rule"
    return min(
        non_hybrid,
        key=lambda s: (
            -non_hybrid[s].get("metrics", {}).get("semantic_correctness_rate", 0.0),
            non_hybrid[s].get("metrics", {}).get("mean_decision_cost", float("inf")),
        ),
    )


def _pick_by_tag_priority(registry, action_ids: list[str]) -> str | None:
    """Pick the best action from competing IDs using tag priority.

    Prefers actions tagged ``stable`` over untagged, and untagged over
    ``fallback``.  Ties broken by action_id alphabetical order.
    """
    action_map = {a.action_id: a for a in registry.actions}
    scored: list[tuple[int, str]] = []
    for aid in action_ids:
        action = action_map.get(aid)
        if action is None:
            continue
        if "stable" in action.tags:
            scored.append((0, aid))
        elif "fallback" in action.tags:
            scored.append((2, aid))
        else:
            scored.append((1, aid))
    scored.sort()
    return scored[0][1] if scored else (action_ids[0] if action_ids else None)


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
