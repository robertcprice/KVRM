"""Deep-dive analysis of support_spec overlap zones across KVRM domains.

For each domain this module:
  1. Identifies all overlap zones -- cases where 2+ actions' support_specs
     both accept the same input features.
  2. Runs the hybrid selector on overlap cases and measures disambiguation
     accuracy, confidence, and margin vs. runner-up.
  3. Compares overlap-zone accuracy vs. non-overlap accuracy so you can see
     whether overlaps are the primary source of errors.
  4. For the content-moderation domain, generates synthetic cases inside the
     reduce_visibility / flag_for_human_review overlap zone and stress-tests
     the hybrid selector.
  5. Generalised synthetic overlap generation for ANY domain -- given a
     registry and a list of overlap action pairs, computes the support_spec
     feature-value intersection and generates synthetic cases inside that
     intersection.
  6. Writes JSON + Markdown reports.
"""

from __future__ import annotations

import importlib
import itertools
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.registry import load_registry
from kvrm_core.support import evaluate_support_spec
from kvrm_core.types import DecisionInput, RegistrySpec

from .ceiling import load_cases

# ---------------------------------------------------------------------------
# Domain catalogue
# ---------------------------------------------------------------------------

DEMO_ROOT = Path(__file__).resolve().parents[3] / "kvrm-demos"

DOMAIN_CATALOGUE: dict[str, dict[str, str]] = {
    "soc": {
        "dir": "soc-playbook-router",
        "module": "soc_playbook_router",
    },
    "sre": {
        "dir": "sre-policy-router",
        "module": "sre_policy_router",
    },
    "drone": {
        "dir": "drone-mission-router",
        "module": "drone_mission_router",
    },
    "grid": {
        "dir": "grid-ops-router",
        "module": "grid_ops_router",
    },
    "finance": {
        "dir": "finance-risk-router",
        "module": "finance_risk_router",
    },
    "medical": {
        "dir": "medical-workflow-router",
        "module": "medical_workflow_router",
    },
    "iam": {
        "dir": "iam-access-router",
        "module": "iam_access_router",
    },
    "customer_support": {
        "dir": "customer-support-router",
        "module": "customer_support_router",
    },
    "content_moderation": {
        "dir": "content-moderation-router",
        "module": "content_moderation_router",
    },
}


def _domain_paths(domain_name: str) -> tuple[Path, Path, Path]:
    """Return (registry_path, cases_path, train_cases_path) for a domain."""
    info = DOMAIN_CATALOGUE[domain_name]
    base = DEMO_ROOT / info["dir"] / "data"
    return (
        base / "registry.json",
        base / "cases.jsonl",
        base / "train_cases.jsonl",
    )


def _import_build_hybrid(domain_name: str):
    """Dynamically import build_hybrid_selector for *domain_name*."""
    info = DOMAIN_CATALOGUE[domain_name]
    mod = importlib.import_module(info["module"])
    return mod.build_hybrid_selector


# ---------------------------------------------------------------------------
# Core overlap detection
# ---------------------------------------------------------------------------

def find_overlap_cases(
    registry: RegistrySpec,
    cases: list[dict[str, Any]],
    *,
    supported_only: bool = True,
) -> list[dict[str, Any]]:
    """Return cases where 2+ actions' support_specs accept the input."""
    rows: list[dict[str, Any]] = []
    for case in cases:
        if supported_only and not case.get("supported", True):
            continue
        matched: list[str] = []
        for action in registry.actions:
            ok, _ = evaluate_support_spec(action.support_spec, case["input_features"])
            if ok:
                matched.append(action.action_id)
        if len(matched) >= 2:
            rows.append({
                "case_id": case.get("case_id"),
                "expected_action_id": case.get("expected_action_id"),
                "input_features": case["input_features"],
                "matched_actions": matched,
                "overlap_degree": len(matched),
            })
    return rows


def find_non_overlap_cases(
    registry: RegistrySpec,
    cases: list[dict[str, Any]],
    *,
    supported_only: bool = True,
) -> list[dict[str, Any]]:
    """Return cases where exactly 1 action's support_spec accepts the input."""
    rows: list[dict[str, Any]] = []
    for case in cases:
        if supported_only and not case.get("supported", True):
            continue
        matched: list[str] = []
        for action in registry.actions:
            ok, _ = evaluate_support_spec(action.support_spec, case["input_features"])
            if ok:
                matched.append(action.action_id)
        if len(matched) == 1:
            rows.append({
                "case_id": case.get("case_id"),
                "expected_action_id": case.get("expected_action_id"),
                "input_features": case["input_features"],
                "matched_actions": matched,
            })
    return rows


def overlap_action_pairs(overlap_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Count co-occurring action pairs across overlap cases."""
    counts: Counter[tuple[str, str]] = Counter()
    for row in overlap_rows:
        actions = sorted(row["matched_actions"])
        for a, b in itertools.combinations(actions, 2):
            counts[(a, b)] += 1
    return [{"pair": list(p), "count": c} for p, c in counts.most_common()]


# ---------------------------------------------------------------------------
# Hybrid selector disambiguation
# ---------------------------------------------------------------------------

def _run_hybrid_on_case(
    hybrid_selector,
    case: dict[str, Any],
) -> dict[str, Any]:
    """Run hybrid selector on one case, return detailed result."""
    di = DecisionInput(
        case_id=case.get("case_id", "unknown"),
        features=case["input_features"],
        expected_action_id=case.get("expected_action_id"),
    )
    candidates = hybrid_selector.select(di)
    if not candidates:
        return {
            "case_id": di.case_id,
            "expected": case.get("expected_action_id"),
            "predicted": None,
            "confidence": 0.0,
            "correct": False,
            "margin": None,
            "runner_up": None,
            "runner_up_confidence": None,
            "num_candidates": 0,
        }

    # Sort by confidence descending
    ranked = sorted(candidates, key=lambda c: c.confidence, reverse=True)
    best = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None

    predicted = best.action_id
    expected = case.get("expected_action_id")
    correct = predicted == expected

    margin = None
    if runner_up is not None:
        margin = best.confidence - runner_up.confidence

    return {
        "case_id": di.case_id,
        "expected": expected,
        "predicted": predicted,
        "confidence": round(best.confidence, 4),
        "correct": correct,
        "margin": round(margin, 4) if margin is not None else None,
        "runner_up": runner_up.action_id if runner_up else None,
        "runner_up_confidence": round(runner_up.confidence, 4) if runner_up else None,
        "num_candidates": len(ranked),
    }


def evaluate_disambiguation(
    hybrid_selector,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run hybrid on a list of cases and compute disambiguation stats."""
    results = [_run_hybrid_on_case(hybrid_selector, c) for c in cases]
    total = len(results)
    if total == 0:
        return {
            "total": 0,
            "correct": 0,
            "accuracy": 0.0,
            "mean_confidence": 0.0,
            "mean_margin": None,
            "results": [],
        }
    correct_count = sum(1 for r in results if r["correct"])
    margins = [r["margin"] for r in results if r["margin"] is not None]
    confidences = [r["confidence"] for r in results]

    return {
        "total": total,
        "correct": correct_count,
        "accuracy": round(correct_count / total, 4) if total else 0.0,
        "mean_confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        "mean_margin": round(sum(margins) / len(margins), 4) if margins else None,
        "results": results,
    }


# ---------------------------------------------------------------------------
# Content-moderation synthetic overlap generation
# ---------------------------------------------------------------------------

_CM_OVERLAP_REPORTER_CREDIBILITY = ["established", "trusted"]
_CM_OVERLAP_CONTEXT_SENSITIVITY = ["general", "workplace"]
_CM_OVERLAP_CONTENT_TYPES = ["text", "image"]
_CM_OVERLAP_USER_TRUST = ["low", "medium"]
_CM_OVERLAP_RECIDIVISM = ["first_offense", "repeat_minor"]
_CM_OVERLAP_AUDIENCE_REACH = ["community", "viral"]
_CM_OVERLAP_AGE = ["fresh", "recent"]


def generate_cm_overlap_synthetic_cases(
    n: int = 25,
) -> list[dict[str, Any]]:
    """Generate synthetic cases in the reduce_visibility / flag_for_human_review overlap.

    Both actions accept toxicity_level=moderate.  We vary reporter_credibility,
    context_sensitivity, content_type, user_trust_score, recidivism_risk,
    audience_reach, and content_age_hours across values that both support_specs
    accept.

    Convention: cases where reporter_credibility is "established" or "trusted"
    and content_type allows flag_for_human_review AND reduce_visibility jointly.

    The *expected* label follows the domain's design intent:
      - reporter_credibility in {"trusted", "internal_tool"} -> flag_for_human_review
        (high-credibility reporters warrant human eyes)
      - reporter_credibility in {"new_reporter", "established"} with
        user_trust_score=low -> reduce_visibility
        (reduce distribution while reporter credibility is ambiguous)
    """
    # Build all combos then sort so reporter_credibility alternates (ensures
    # both expected labels appear even for small n).
    combos = list(itertools.product(
        _CM_OVERLAP_CONTEXT_SENSITIVITY,     # general, workplace
        _CM_OVERLAP_CONTENT_TYPES,           # text, image
        _CM_OVERLAP_USER_TRUST,              # low, medium
        _CM_OVERLAP_RECIDIVISM,              # first_offense, repeat_minor
        _CM_OVERLAP_AUDIENCE_REACH,          # community, viral
        _CM_OVERLAP_AGE,                     # fresh, recent
        _CM_OVERLAP_REPORTER_CREDIBILITY,    # established, trusted (LAST so it toggles fastest)
    ))

    cases: list[dict[str, Any]] = []
    for idx, (ctx_sens, ctype, trust, recid, reach, age, reporter) in enumerate(combos):
        if idx >= n:
            break
        features = {
            "toxicity_level": "moderate",
            "content_type": ctype,
            "reporter_credibility": reporter,
            "user_trust_score": trust,
            "context_sensitivity": ctx_sens,
            "audience_reach": reach,
            "recidivism_risk": recid,
            "content_age_hours": age,
        }

        # Domain design intent for disambiguation:
        # trusted reporters -> flag_for_human_review (want human verification)
        # established reporters with low trust -> reduce_visibility
        # established reporters with medium trust -> reduce_visibility (less aggressive)
        if reporter == "trusted":
            expected = "flag_for_human_review"
        else:
            expected = "reduce_visibility"

        cases.append({
            "case_id": f"cm_synth_overlap_{idx + 1:03d}",
            "expected_action_id": expected,
            "input_features": features,
            "supported": True,
            "ood": False,
        })

    return cases


# ---------------------------------------------------------------------------
# Generalised synthetic overlap generation
# ---------------------------------------------------------------------------

def _extract_leaf_constraints(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Walk a support_spec and return all leaf-level constraints.

    For ``all`` nodes every child is required (conjunction).
    For ``any`` nodes each child is an alternative disjunct -- we collect
    leaves from *all* children so the caller can intersect appropriately.
    Leaf nodes have ``feature``, ``op``, ``value``.
    """
    leaves: list[dict[str, Any]] = []
    if "feature" in spec:
        leaves.append(spec)
    elif "all" in spec:
        for child in spec["all"]:
            leaves.extend(_extract_leaf_constraints(child))
    elif "any" in spec:
        for child in spec["any"]:
            leaves.extend(_extract_leaf_constraints(child))
    elif "not" in spec:
        # ``not`` inverts the logic -- we skip it for intersection purposes
        # because negation makes it hard to enumerate accepted values.
        pass
    return leaves


def _accepted_values_from_leaves(
    leaves: list[dict[str, Any]],
    context_schema: dict[str, dict[str, Any]],
) -> dict[str, set[Any]]:
    """From a list of leaf constraints, derive accepted values per feature.

    For ``eq`` ops the accepted set is {value}.
    For ``in`` ops the accepted set is set(value).
    For features not mentioned in the constraints we fall back to the full
    enum from the context_schema, meaning the spec places no restriction.
    """
    accepted: dict[str, set[Any]] = {}

    for leaf in leaves:
        feat = leaf["feature"]
        op = leaf["op"]
        val = leaf.get("value")

        if op == "eq":
            accepted.setdefault(feat, set()).add(val)
        elif op == "in":
            accepted.setdefault(feat, set()).update(val)
        # neq / not_in: hard to enumerate positively -- skip, the caller
        # will verify generated cases against both specs anyway.

    return accepted


def extract_spec_accepted_values(
    spec: dict[str, Any],
    context_schema: dict[str, dict[str, Any]],
) -> dict[str, list[Any]]:
    """Return a dict mapping each feature to its accepted values under *spec*.

    Features not explicitly constrained by *spec* inherit the full enum
    from *context_schema*.  Boolean features default to ``[True, False]``.
    """
    leaves = _extract_leaf_constraints(spec)
    raw = _accepted_values_from_leaves(leaves, context_schema)

    result: dict[str, list[Any]] = {}
    for feat, schema_info in context_schema.items():
        if feat in raw:
            result[feat] = sorted(raw[feat], key=str)
        else:
            # No constraint from spec -- use full enum
            enum = schema_info.get("enum")
            if enum is not None:
                result[feat] = list(enum)
            elif schema_info.get("type") == "boolean":
                result[feat] = [True, False]
            else:
                result[feat] = []
    return result


def compute_overlap_intersection(
    registry: RegistrySpec,
    action_id_a: str,
    action_id_b: str,
) -> dict[str, list[Any]]:
    """Compute the feature-value intersection of two actions' support_specs.

    Returns a dict mapping each feature to the list of values accepted by
    *both* actions.  An empty list for a feature means no common values
    (the specs are disjoint on that dimension).
    """
    schema = registry.context_schema
    action_a = next(a for a in registry.actions if a.action_id == action_id_a)
    action_b = next(a for a in registry.actions if a.action_id == action_id_b)

    accepted_a = extract_spec_accepted_values(action_a.support_spec, schema)
    accepted_b = extract_spec_accepted_values(action_b.support_spec, schema)

    intersection: dict[str, list[Any]] = {}
    for feat in schema:
        vals_a = set(accepted_a.get(feat, []))
        vals_b = set(accepted_b.get(feat, []))
        common = vals_a & vals_b
        intersection[feat] = sorted(common, key=str)
    return intersection


def generate_overlap_synthetic_cases(
    registry: RegistrySpec,
    overlap_pairs: list[tuple[str, str]],
    *,
    n: int = 25,
    domain_label: str = "generic",
    expected_action_fn: Any | None = None,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Generate synthetic cases in overlap zones for arbitrary action pairs.

    Parameters
    ----------
    registry:
        The loaded RegistrySpec for the domain.
    overlap_pairs:
        List of (action_id_a, action_id_b) pairs to generate cases for.
    n:
        Number of synthetic cases to generate per pair.
    domain_label:
        Short prefix for case_ids (e.g. "cs", "cm").
    expected_action_fn:
        Optional callable ``(action_id_a, action_id_b, features, idx) -> str``
        that returns the expected action_id for a given synthetic case.
        When ``None``, the expected label alternates between the two actions.
    seed:
        Random seed for reproducibility.

    Returns
    -------
    All generated cases across all pairs, each with a unique case_id.
    Cases that fail to satisfy both actions' support_specs are silently
    dropped (the intersection heuristic is conservative for ``any`` specs).
    """
    from kvrm_core.support import evaluate_support_spec as _eval_spec

    rng = random.Random(seed)
    all_cases: list[dict[str, Any]] = []
    global_idx = 0

    for action_a, action_b in overlap_pairs:
        pair_label = f"{action_a}_vs_{action_b}"
        intersection = compute_overlap_intersection(registry, action_a, action_b)

        # Skip pairs with empty intersection on any feature
        empty_feats = [f for f, vals in intersection.items() if not vals]
        if empty_feats:
            continue

        # Generate candidate feature combos from the intersection
        features_list = list(intersection.keys())
        values_lists = [intersection[f] for f in features_list]

        # If the product space is large, sample; otherwise enumerate
        product_size = 1
        for vl in values_lists:
            product_size *= max(1, len(vl))

        if product_size <= n * 2:
            # Enumerate all and sample
            combos = list(itertools.product(*values_lists))
            rng.shuffle(combos)
        else:
            # Random sampling from the product space
            combos = []
            seen: set[tuple] = set()
            attempts = 0
            while len(combos) < n * 2 and attempts < n * 20:
                combo = tuple(rng.choice(vl) for vl in values_lists)
                if combo not in seen:
                    seen.add(combo)
                    combos.append(combo)
                attempts += 1

        pair_cases: list[dict[str, Any]] = []
        for combo in combos:
            if len(pair_cases) >= n:
                break

            features = dict(zip(features_list, combo))

            # Verify the case actually falls in both specs
            spec_a = next(a for a in registry.actions if a.action_id == action_a).support_spec
            spec_b = next(a for a in registry.actions if a.action_id == action_b).support_spec
            ok_a, _ = _eval_spec(spec_a, features)
            ok_b, _ = _eval_spec(spec_b, features)
            if not (ok_a and ok_b):
                continue

            idx_in_pair = len(pair_cases)

            if expected_action_fn is not None:
                expected = expected_action_fn(action_a, action_b, features, idx_in_pair)
            else:
                # Default: alternate between the two actions
                expected = action_a if idx_in_pair % 2 == 0 else action_b

            pair_cases.append({
                "case_id": f"{domain_label}_synth_{pair_label}_{global_idx + 1:03d}",
                "expected_action_id": expected,
                "input_features": features,
                "supported": True,
                "ood": False,
                "overlap_pair": [action_a, action_b],
            })
            global_idx += 1

        all_cases.extend(pair_cases)

    return all_cases


# ---------------------------------------------------------------------------
# Customer-support synthetic overlap generation
# ---------------------------------------------------------------------------

# Top-3 customer support overlap pairs (by case count from prior analysis):
#   1. escalate_to_manager vs request_human_review (8 cases)
#   2. assign_specialist vs request_human_review (7 cases)
#   3. request_human_review vs send_knowledge_article (6 cases)

CS_TOP_OVERLAP_PAIRS: list[tuple[str, str]] = [
    ("escalate_to_manager", "request_human_review"),
    ("assign_specialist", "request_human_review"),
    ("request_human_review", "send_knowledge_article"),
]


def _cs_expected_action(
    action_a: str,
    action_b: str,
    features: dict[str, Any],
    idx: int,
) -> str:
    """Domain design-intent disambiguation for customer support overlap pairs.

    The logic encodes the domain's intended routing:
      - escalate_to_manager vs request_human_review:
          multi_escalated or angry+excessive or requires_engineering -> escalate_to_manager
          otherwise -> request_human_review
      - assign_specialist vs request_human_review:
          moderate/complex + technical/account/product_defect + standard+ tier -> assign_specialist
          otherwise -> request_human_review
      - send_knowledge_article vs request_human_review:
          simple + positive/neutral + no prior contacts -> send_knowledge_article
          otherwise -> request_human_review
    """
    pair = frozenset([action_a, action_b])

    if pair == frozenset(["escalate_to_manager", "request_human_review"]):
        # Escalation triggers: multi_escalated, angry+excessive, requires_engineering,
        # angry+enterprise
        if features.get("escalation_history") == "multi_escalated":
            return "escalate_to_manager"
        if (features.get("sentiment") == "angry"
                and features.get("prior_contacts") == "excessive"):
            return "escalate_to_manager"
        if features.get("resolution_complexity") == "requires_engineering":
            return "escalate_to_manager"
        if (features.get("customer_tier") == "enterprise"
                and features.get("sentiment") == "angry"):
            return "escalate_to_manager"
        return "request_human_review"

    if pair == frozenset(["assign_specialist", "request_human_review"]):
        # Specialist triggers: technical/account/product_defect category,
        # moderate+/complex complexity, paying tier
        cat = features.get("issue_category")
        complexity = features.get("resolution_complexity")
        tier = features.get("customer_tier")
        if (cat in ("technical", "account", "product_defect")
                and complexity in ("moderate", "complex")
                and tier in ("standard", "premium", "enterprise")):
            return "assign_specialist"
        return "request_human_review"

    if pair == frozenset(["request_human_review", "send_knowledge_article"]):
        # KB article triggers: simple + positive/neutral + no contacts + no escalation
        if (features.get("resolution_complexity") == "simple"
                and features.get("sentiment") in ("positive", "neutral")
                and features.get("prior_contacts") == "none"
                and not features.get("has_open_ticket")
                and features.get("escalation_history") == "none"):
            return "send_knowledge_article"
        return "request_human_review"

    # Fallback: alternate
    return action_a if idx % 2 == 0 else action_b


def generate_cs_overlap_synthetic_cases(
    registry: RegistrySpec,
    *,
    n_per_pair: int = 25,
    pairs: list[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Generate synthetic overlap cases for customer support domain.

    Uses domain-specific expected-action logic to assign ground-truth labels
    that match the domain's design intent.
    """
    if pairs is None:
        pairs = CS_TOP_OVERLAP_PAIRS
    return generate_overlap_synthetic_cases(
        registry=registry,
        overlap_pairs=pairs,
        n=n_per_pair,
        domain_label="cs",
        expected_action_fn=_cs_expected_action,
        seed=42,
    )


# ---------------------------------------------------------------------------
# Expanded overlap analysis (multi-domain synthetic)
# ---------------------------------------------------------------------------

def run_expanded_overlap_analysis(
    output_dir: str | Path | None = None,
    *,
    cm_synthetic_count: int = 25,
    cs_synthetic_per_pair: int = 25,
) -> dict[str, Any]:
    """Run synthetic overlap analysis for CM and customer support, write results.

    This is a focused analysis that generates synthetic overlap cases for
    domains with known high-overlap pairs (content moderation and customer
    support) and measures the hybrid selector's disambiguation accuracy.
    """
    results: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domains": {},
        "hard_pairs": [],
        "easy_pairs": [],
    }

    # --- Content moderation ---
    cm_synth = generate_cm_overlap_synthetic_cases(n=cm_synthetic_count)
    cm_report = analyze_domain_overlaps(
        "content_moderation",
        extra_synthetic_cases=cm_synth,
    )
    results["domains"]["content_moderation"] = cm_report

    # --- Customer support ---
    cs_registry_path, cs_cases_path, cs_train_path = _domain_paths("customer_support")
    cs_registry = load_registry(cs_registry_path)
    cs_synth = generate_cs_overlap_synthetic_cases(
        cs_registry,
        n_per_pair=cs_synthetic_per_pair,
    )
    cs_report = analyze_domain_overlaps(
        "customer_support",
        extra_synthetic_cases=cs_synth,
    )
    results["domains"]["customer_support"] = cs_report

    # --- Classify pairs as hard (<80% accuracy) vs easy (>=80%) ---
    for domain_name, dom in results["domains"].items():
        for pd_entry in dom.get("pair_disambiguation", []):
            entry = {
                "domain": domain_name,
                "pair": pd_entry["pair"],
                "case_count": pd_entry["case_count"],
                "accuracy": pd_entry["accuracy"],
                "mean_confidence": pd_entry["mean_confidence"],
                "mean_margin": pd_entry["mean_margin"],
            }
            if pd_entry["accuracy"] < 0.80:
                results["hard_pairs"].append(entry)
            else:
                results["easy_pairs"].append(entry)

    # Sort hard pairs by accuracy ascending (hardest first)
    results["hard_pairs"].sort(key=lambda x: x["accuracy"])
    results["easy_pairs"].sort(key=lambda x: x["accuracy"])

    # --- CS synthetic per-pair breakdown ---
    if cs_synth:
        build_hybrid = _import_build_hybrid("customer_support")
        hybrid = build_hybrid(cs_train_path)
        cs_synth_eval = evaluate_disambiguation(hybrid, cs_synth)

        # Per-pair breakdown for synthetic cases
        cs_pair_synth: list[dict[str, Any]] = []
        for pair_tuple in CS_TOP_OVERLAP_PAIRS:
            pair_set = set(pair_tuple)
            pair_cases = [
                c for c in cs_synth
                if set(c.get("overlap_pair", [])) == pair_set
            ]
            if pair_cases:
                pair_eval = evaluate_disambiguation(hybrid, pair_cases)
                cs_pair_synth.append({
                    "pair": list(pair_tuple),
                    "generated": len(pair_cases),
                    "accuracy": pair_eval["accuracy"],
                    "mean_confidence": pair_eval["mean_confidence"],
                    "mean_margin": pair_eval["mean_margin"],
                    "correct": pair_eval["correct"],
                    "total": pair_eval["total"],
                })

        results["domains"]["customer_support"]["synthetic_overlap_eval"] = {
            "accuracy": cs_synth_eval["accuracy"],
            "mean_confidence": cs_synth_eval["mean_confidence"],
            "mean_margin": cs_synth_eval["mean_margin"],
            "correct": cs_synth_eval["correct"],
            "total": cs_synth_eval["total"],
            "results": cs_synth_eval["results"],
            "per_pair": cs_pair_synth,
        }

    if output_dir is not None:
        _write_expanded_reports(results, Path(output_dir))

    return results


def _write_expanded_reports(results: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "expanded_overlap_report.json"
    json_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    md_path = output_dir / "expanded_overlap_report.md"
    md_path.write_text(_render_expanded_markdown(results), encoding="utf-8")


def _render_expanded_markdown(results: dict[str, Any]) -> str:
    lines = [
        "# KVRM Expanded Overlap Stress-Test Report",
        "",
        f"Generated: {results['generated_at']}",
        "",
        "## Overview",
        "",
        "This report analyses synthetic overlap cases generated for domains with",
        "known high-overlap action pairs.  The goal is to identify which overlaps",
        "are genuinely hard to disambiguate (accuracy < 80%) versus easily handled",
        "by the hybrid selector.",
        "",
    ]

    # --- Hard pairs ---
    lines.extend([
        "## Hard Pairs (Accuracy < 80%)",
        "",
    ])
    if results["hard_pairs"]:
        lines.append("| Domain | Pair | Cases | Accuracy | Mean Conf | Mean Margin |")
        lines.append("|--------|------|------:|---------:|----------:|------------:|")
        for hp in results["hard_pairs"]:
            margin_str = f"{hp['mean_margin']:.4f}" if hp["mean_margin"] is not None else "n/a"
            lines.append(
                f"| {hp['domain']} | {hp['pair'][0]} vs {hp['pair'][1]} "
                f"| {hp['case_count']} | {hp['accuracy']:.2%} "
                f"| {hp['mean_confidence']:.4f} | {margin_str} |"
            )
    else:
        lines.append("No pairs with accuracy below 80% -- the hybrid selector handles all overlaps well.")
    lines.append("")

    # --- Easy pairs ---
    lines.extend([
        "## Easy Pairs (Accuracy >= 80%)",
        "",
    ])
    if results["easy_pairs"]:
        lines.append("| Domain | Pair | Cases | Accuracy | Mean Conf | Mean Margin |")
        lines.append("|--------|------|------:|---------:|----------:|------------:|")
        for ep in results["easy_pairs"]:
            margin_str = f"{ep['mean_margin']:.4f}" if ep["mean_margin"] is not None else "n/a"
            lines.append(
                f"| {ep['domain']} | {ep['pair'][0]} vs {ep['pair'][1]} "
                f"| {ep['case_count']} | {ep['accuracy']:.2%} "
                f"| {ep['mean_confidence']:.4f} | {margin_str} |"
            )
    else:
        lines.append("No easy pairs detected.")
    lines.append("")

    # --- Per-domain detail ---
    for domain_name, dom in results["domains"].items():
        lines.extend([
            f"## {domain_name.upper().replace('_', ' ')} Detail",
            "",
            f"- Actions: {dom['action_count']}",
            f"- Supported cases: {dom['supported_case_count']}",
            f"- Overlap cases: {dom['overlap_case_count']} ({dom['overlap_case_fraction']:.2%})",
            "",
        ])

        # Overlap pairs
        if dom["overlap_zone_action_pairs"]:
            lines.append("### Overlap Action Pairs")
            lines.append("")
            for entry in dom["overlap_zone_action_pairs"]:
                lines.append(f"- `{entry['pair'][0]}` vs `{entry['pair'][1]}`: {entry['count']} cases")
            lines.append("")

        # Per-pair disambiguation
        if dom["pair_disambiguation"]:
            lines.append("### Per-Pair Disambiguation (Real Cases)")
            lines.append("")
            lines.append("| Pair | Cases | Accuracy | Mean Conf | Mean Margin |")
            lines.append("|------|------:|---------:|----------:|------------:|")
            for pd_entry in dom["pair_disambiguation"]:
                margin_str = f"{pd_entry['mean_margin']:.4f}" if pd_entry["mean_margin"] is not None else "n/a"
                lines.append(
                    f"| {pd_entry['pair'][0]} vs {pd_entry['pair'][1]} "
                    f"| {pd_entry['case_count']} | {pd_entry['accuracy']:.2%} "
                    f"| {pd_entry['mean_confidence']:.4f} | {margin_str} |"
                )
            lines.append("")

        # Synthetic eval
        se = dom.get("synthetic_overlap_eval")
        if se:
            lines.extend([
                "### Synthetic Overlap Stress-Test",
                "",
                f"- **Total synthetic cases**: {se['total']}",
                f"- **Accuracy**: {se['correct']}/{se['total']} = {se['accuracy']:.2%}",
                f"- **Mean confidence**: {se['mean_confidence']:.4f}",
                f"- **Mean margin**: {se['mean_margin'] if se['mean_margin'] is not None else 'n/a'}",
                "",
            ])

            # Per-pair synthetic breakdown (CS only)
            per_pair = se.get("per_pair", [])
            if per_pair:
                lines.append("#### Per-Pair Synthetic Breakdown")
                lines.append("")
                lines.append("| Pair | Generated | Accuracy | Mean Conf | Mean Margin |")
                lines.append("|------|----------:|---------:|----------:|------------:|")
                for pp in per_pair:
                    margin_str = f"{pp['mean_margin']:.4f}" if pp["mean_margin"] is not None else "n/a"
                    lines.append(
                        f"| {pp['pair'][0]} vs {pp['pair'][1]} "
                        f"| {pp['generated']} | {pp['accuracy']:.2%} "
                        f"| {pp['mean_confidence']:.4f} | {margin_str} |"
                    )
                lines.append("")

            # Breakdown by expected action
            by_expected: dict[str, list[dict]] = defaultdict(list)
            for r in se["results"]:
                by_expected[r["expected"] or "unknown"].append(r)
            for exp, items in sorted(by_expected.items()):
                correct_items = sum(1 for i in items if i["correct"])
                lines.append(f"- Expected `{exp}`: {correct_items}/{len(items)} correct")
            lines.append("")

            # Misclassifications
            misses = [r for r in se["results"] if not r["correct"]]
            if misses:
                lines.append("#### Misclassified Synthetic Cases")
                lines.append("")
                lines.append("| Case ID | Expected | Predicted | Confidence | Margin |")
                lines.append("|---------|----------|-----------|----------:|-------:|")
                for m in misses[:20]:
                    margin_str = f"{m['margin']:.4f}" if m["margin"] is not None else "n/a"
                    lines.append(
                        f"| {m['case_id']} | {m['expected']} | {m['predicted']} "
                        f"| {m['confidence']:.4f} | {margin_str} |"
                    )
                lines.append("")

    # --- Interpretation ---
    lines.extend([
        "## Key Insight: Hard vs Easy Disambiguation",
        "",
        "**Hard pairs** (accuracy < 80%) represent overlap zones where the hybrid",
        "selector's evidence signals (retrieval bank, rules, prototypes, semantic",
        "matching) are insufficient to reliably distinguish the two actions.  These",
        "pairs are candidates for:",
        "",
        "  1. Additional discriminating features in the support_spec",
        "  2. More training cases in the retrieval bank for these specific overlaps",
        "  3. Targeted rules that capture the domain design intent",
        "",
        "**Easy pairs** (accuracy >= 80%) show the hybrid selector successfully",
        "disambiguates despite the support_spec overlap -- the non-spec evidence",
        "(retrieval exemplars, rule lookups, prototype distance) provides enough",
        "signal.",
        "",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-domain analysis
# ---------------------------------------------------------------------------

def analyze_domain_overlaps(
    domain_name: str,
    *,
    extra_synthetic_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Full overlap analysis for one domain."""
    registry_path, cases_path, train_cases_path = _domain_paths(domain_name)

    registry = load_registry(registry_path)
    cases = load_cases(cases_path)
    supported_cases = [c for c in cases if c.get("supported", True)]

    # --- overlap detection ---
    overlap_rows = find_overlap_cases(registry, cases, supported_only=True)
    non_overlap_rows = find_non_overlap_cases(registry, cases, supported_only=True)
    pair_counts = overlap_action_pairs(overlap_rows)

    overlap_case_count = len(overlap_rows)
    supported_count = len(supported_cases)
    overlap_fraction = (overlap_case_count / supported_count) if supported_count else 0.0

    # --- build hybrid selector ---
    build_hybrid = _import_build_hybrid(domain_name)
    hybrid = build_hybrid(train_cases_path)

    # --- disambiguation on overlap cases ---
    overlap_eval = evaluate_disambiguation(hybrid, overlap_rows)

    # --- accuracy on non-overlap cases ---
    non_overlap_eval = evaluate_disambiguation(hybrid, non_overlap_rows)

    # --- accuracy on ALL supported cases ---
    all_eval = evaluate_disambiguation(hybrid, supported_cases)

    # --- extra synthetic cases (content moderation) ---
    synthetic_eval = None
    if extra_synthetic_cases:
        synthetic_eval = evaluate_disambiguation(hybrid, extra_synthetic_cases)

    # --- per-pair disambiguation breakdown ---
    pair_disambiguation: list[dict[str, Any]] = []
    for pair_entry in pair_counts:
        pair_set = set(pair_entry["pair"])
        pair_cases = [r for r in overlap_rows if pair_set <= set(r["matched_actions"])]
        if pair_cases:
            pair_result = evaluate_disambiguation(hybrid, pair_cases)
            pair_disambiguation.append({
                "pair": pair_entry["pair"],
                "case_count": pair_entry["count"],
                "accuracy": pair_result["accuracy"],
                "mean_confidence": pair_result["mean_confidence"],
                "mean_margin": pair_result["mean_margin"],
            })

    return {
        "domain": domain_name,
        "registry_name": registry.registry_name,
        "action_count": len(registry.actions),
        "supported_case_count": supported_count,
        "overlap_case_count": overlap_case_count,
        "overlap_case_fraction": round(overlap_fraction, 4),
        "non_overlap_case_count": len(non_overlap_rows),
        "overlap_zone_action_pairs": pair_counts,
        "pair_disambiguation": pair_disambiguation,
        "overlap_disambiguation": {
            "accuracy": overlap_eval["accuracy"],
            "mean_confidence": overlap_eval["mean_confidence"],
            "mean_margin": overlap_eval["mean_margin"],
            "correct": overlap_eval["correct"],
            "total": overlap_eval["total"],
        },
        "non_overlap_accuracy": {
            "accuracy": non_overlap_eval["accuracy"],
            "mean_confidence": non_overlap_eval["mean_confidence"],
            "correct": non_overlap_eval["correct"],
            "total": non_overlap_eval["total"],
        },
        "all_supported_accuracy": {
            "accuracy": all_eval["accuracy"],
            "mean_confidence": all_eval["mean_confidence"],
            "correct": all_eval["correct"],
            "total": all_eval["total"],
        },
        "synthetic_overlap_eval": (
            {
                "accuracy": synthetic_eval["accuracy"],
                "mean_confidence": synthetic_eval["mean_confidence"],
                "mean_margin": synthetic_eval["mean_margin"],
                "correct": synthetic_eval["correct"],
                "total": synthetic_eval["total"],
                "results": synthetic_eval["results"],
            }
            if synthetic_eval
            else None
        ),
        "overlap_detail": overlap_eval["results"],
    }


# ---------------------------------------------------------------------------
# Full cross-domain run
# ---------------------------------------------------------------------------

def run_all_domains(
    output_dir: str | Path | None = None,
    *,
    cm_synthetic_count: int = 25,
    cs_synthetic_per_pair: int = 25,
) -> dict[str, Any]:
    """Analyse overlap zones for every domain and write reports.

    Generates synthetic overlap stress-test cases for all domains with
    known high-overlap pairs:
      - content_moderation: reduce_visibility vs flag_for_human_review
      - customer_support: escalate_to_manager vs request_human_review,
        assign_specialist vs request_human_review,
        send_knowledge_article vs request_human_review
    """
    results: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domains": {},
        "summary": {},
    }

    for domain_name in DOMAIN_CATALOGUE:
        extra = None
        if domain_name == "content_moderation":
            extra = generate_cm_overlap_synthetic_cases(n=cm_synthetic_count)
        elif domain_name == "customer_support":
            cs_registry_path = _domain_paths("customer_support")[0]
            cs_registry = load_registry(cs_registry_path)
            extra = generate_cs_overlap_synthetic_cases(
                cs_registry,
                n_per_pair=cs_synthetic_per_pair,
            )
        report = analyze_domain_overlaps(domain_name, extra_synthetic_cases=extra)
        results["domains"][domain_name] = report

    # --- cross-domain summary ---
    summary_rows: list[dict[str, Any]] = []
    for name, dom in results["domains"].items():
        summary_rows.append({
            "domain": name,
            "supported_cases": dom["supported_case_count"],
            "overlap_cases": dom["overlap_case_count"],
            "overlap_fraction": dom["overlap_case_fraction"],
            "overlap_accuracy": dom["overlap_disambiguation"]["accuracy"],
            "non_overlap_accuracy": dom["non_overlap_accuracy"]["accuracy"],
            "all_accuracy": dom["all_supported_accuracy"]["accuracy"],
            "accuracy_gap_pp": round(
                100.0 * (dom["non_overlap_accuracy"]["accuracy"] - dom["overlap_disambiguation"]["accuracy"]),
                2,
            ) if dom["overlap_disambiguation"]["total"] > 0 else None,
            "top_pair": dom["overlap_zone_action_pairs"][0]["pair"] if dom["overlap_zone_action_pairs"] else None,
        })
    results["summary"] = summary_rows

    if output_dir is not None:
        _write_reports(results, Path(output_dir))

    return results


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------

def _write_reports(results: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "overlap_analysis.json"
    json_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    md_path = output_dir / "overlap_analysis.md"
    md_path.write_text(render_markdown(results), encoding="utf-8")


def render_markdown(results: dict[str, Any]) -> str:
    lines = [
        "# KVRM Support-Spec Overlap Analysis",
        "",
        f"Generated: {results['generated_at']}",
        "",
        "## Cross-Domain Summary",
        "",
        "| Domain | Supported Cases | Overlap Cases | Overlap % | Overlap Acc | Non-Overlap Acc | All Acc | Gap (pp) |",
        "|--------|----------------:|-------------:|----------:|------------:|----------------:|--------:|---------:|",
    ]
    for row in results["summary"]:
        gap = f"{row['accuracy_gap_pp']:.1f}" if row["accuracy_gap_pp"] is not None else "n/a"
        lines.append(
            f"| {row['domain']} | {row['supported_cases']} | {row['overlap_cases']} "
            f"| {row['overlap_fraction']:.2%} | {row['overlap_accuracy']:.2%} "
            f"| {row['non_overlap_accuracy']:.2%} | {row['all_accuracy']:.2%} | {gap} |"
        )
    lines.append("")

    for domain_name, dom in results["domains"].items():
        lines.extend([
            f"## {domain_name.upper().replace('_', ' ')}",
            "",
            f"- Actions: {dom['action_count']}",
            f"- Supported eval cases: {dom['supported_case_count']}",
            f"- Overlap cases: {dom['overlap_case_count']} ({dom['overlap_case_fraction']:.2%})",
            f"- Non-overlap cases: {dom['non_overlap_case_count']}",
            "",
        ])

        if dom["overlap_zone_action_pairs"]:
            lines.append("### Overlap Action Pairs")
            lines.append("")
            for entry in dom["overlap_zone_action_pairs"]:
                lines.append(f"- `{entry['pair'][0]}` vs `{entry['pair'][1]}`: {entry['count']} cases")
            lines.append("")

        if dom["pair_disambiguation"]:
            lines.append("### Per-Pair Disambiguation")
            lines.append("")
            lines.append("| Pair | Cases | Accuracy | Mean Conf | Mean Margin |")
            lines.append("|------|------:|---------:|----------:|------------:|")
            for pd in dom["pair_disambiguation"]:
                margin_str = f"{pd['mean_margin']:.4f}" if pd["mean_margin"] is not None else "n/a"
                lines.append(
                    f"| {pd['pair'][0]} vs {pd['pair'][1]} "
                    f"| {pd['case_count']} | {pd['accuracy']:.2%} "
                    f"| {pd['mean_confidence']:.4f} | {margin_str} |"
                )
            lines.append("")

        lines.extend([
            "### Disambiguation Accuracy",
            "",
            f"- **Overlap zone**: {dom['overlap_disambiguation']['correct']}/{dom['overlap_disambiguation']['total']}"
            f" = {dom['overlap_disambiguation']['accuracy']:.2%}"
            f" (mean conf {dom['overlap_disambiguation']['mean_confidence']:.4f},"
            f" mean margin {dom['overlap_disambiguation']['mean_margin'] or 'n/a'})",
            f"- **Non-overlap zone**: {dom['non_overlap_accuracy']['correct']}/{dom['non_overlap_accuracy']['total']}"
            f" = {dom['non_overlap_accuracy']['accuracy']:.2%}"
            f" (mean conf {dom['non_overlap_accuracy']['mean_confidence']:.4f})",
            f"- **All supported**: {dom['all_supported_accuracy']['correct']}/{dom['all_supported_accuracy']['total']}"
            f" = {dom['all_supported_accuracy']['accuracy']:.2%}",
            "",
        ])

        if dom.get("synthetic_overlap_eval"):
            se = dom["synthetic_overlap_eval"]
            lines.extend([
                f"### {domain_name.upper().replace('_', ' ')} Synthetic Overlap Zone",
                "",
                f"Generated {se['total']} synthetic stress-test cases in overlap zones.",
                "",
                f"- **Accuracy**: {se['correct']}/{se['total']} = {se['accuracy']:.2%}",
                f"- **Mean confidence**: {se['mean_confidence']:.4f}",
                f"- **Mean margin**: {se['mean_margin'] if se['mean_margin'] is not None else 'n/a'}",
                "",
            ])

            # Breakdown by expected action
            by_expected: dict[str, list[dict]] = defaultdict(list)
            for r in se["results"]:
                by_expected[r["expected"] or "unknown"].append(r)
            for exp, items in sorted(by_expected.items()):
                correct_items = sum(1 for i in items if i["correct"])
                lines.append(f"- Expected `{exp}`: {correct_items}/{len(items)} correct")
            lines.append("")

            # Show misclassifications
            misses = [r for r in se["results"] if not r["correct"]]
            if misses:
                lines.append("#### Misclassified Synthetic Cases")
                lines.append("")
                lines.append("| Case ID | Expected | Predicted | Confidence | Margin |")
                lines.append("|---------|----------|-----------|----------:|-------:|")
                for m in misses[:15]:
                    margin_str = f"{m['margin']:.4f}" if m["margin"] is not None else "n/a"
                    lines.append(
                        f"| {m['case_id']} | {m['expected']} | {m['predicted']} "
                        f"| {m['confidence']:.4f} | {margin_str} |"
                    )
                lines.append("")

        # Show a few overlap detail misses
        overlap_misses = [r for r in dom["overlap_detail"] if not r["correct"]]
        if overlap_misses:
            lines.append("### Overlap Zone Misclassifications")
            lines.append("")
            lines.append("| Case ID | Expected | Predicted | Confidence | Margin |")
            lines.append("|---------|----------|-----------|----------:|-------:|")
            for m in overlap_misses[:10]:
                margin_str = f"{m['margin']:.4f}" if m["margin"] is not None else "n/a"
                lines.append(
                    f"| {m['case_id']} | {m['expected']} | {m['predicted']} "
                    f"| {m['confidence']:.4f} | {margin_str} |"
                )
            lines.append("")

    lines.extend([
        "## Interpretation",
        "",
        "- **Overlap fraction** = proportion of supported cases where 2+ actions' support_specs both match.",
        "- **Accuracy gap** = non-overlap accuracy minus overlap accuracy (in percentage points).",
        "  A positive gap means overlaps are harder to disambiguate than non-overlapping cases.",
        "- When the gap is large, the hybrid selector relies on evidence beyond support_spec matching",
        "  (retrieval bank, rules, prototypes) to choose the right action.",
        "- The content-moderation synthetic analysis stress-tests the intentional overlap between",
        "  `reduce_visibility` and `flag_for_human_review` at `toxicity_level=moderate`.",
        "",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import sys

    output_dir = Path(__file__).resolve().parents[3] / "kvrm-bench-results" / "overlap_analysis"
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])

    print(f"Running overlap analysis across {len(DOMAIN_CATALOGUE)} domains ...")
    results = run_all_domains(
        output_dir,
        cm_synthetic_count=25,
        cs_synthetic_per_pair=25,
    )

    # Print summary
    print()
    print("=" * 80)
    print("KVRM SUPPORT-SPEC OVERLAP ANALYSIS RESULTS")
    print("=" * 80)
    print()
    header = f"{'Domain':<22} {'Cases':>6} {'Overlap':>8} {'Ovlp%':>7} {'OvlpAcc':>8} {'NonOvAcc':>9} {'AllAcc':>8} {'Gap pp':>8}"
    print(header)
    print("-" * len(header))
    for row in results["summary"]:
        gap = f"{row['accuracy_gap_pp']:.1f}" if row["accuracy_gap_pp"] is not None else "n/a"
        print(
            f"{row['domain']:<22} {row['supported_cases']:>6} {row['overlap_cases']:>8} "
            f"{row['overlap_fraction']:>7.2%} {row['overlap_accuracy']:>8.2%} "
            f"{row['non_overlap_accuracy']:>9.2%} {row['all_accuracy']:>8.2%} {gap:>8}"
        )
    print()

    # Synthetic detail for domains with overlap stress tests
    for domain_label, domain_key in [
        ("CONTENT MODERATION", "content_moderation"),
        ("CUSTOMER SUPPORT", "customer_support"),
    ]:
        dom = results["domains"].get(domain_key, {})
        se = dom.get("synthetic_overlap_eval")
        if se:
            print(f"{domain_label} SYNTHETIC OVERLAP ZONE:")
            print(f"  Cases: {se['total']}, Correct: {se['correct']}, Accuracy: {se['accuracy']:.2%}")
            print(f"  Mean confidence: {se['mean_confidence']:.4f}")
            print(f"  Mean margin: {se['mean_margin']}")
            misses = [r for r in se["results"] if not r["correct"]]
            if misses:
                print(f"  Misclassifications ({len(misses)}):")
                for m in misses[:10]:
                    print(f"    {m['case_id']}: expected={m['expected']}, got={m['predicted']} "
                          f"(conf={m['confidence']:.4f}, margin={m['margin']})")
            print()

    # Per-domain overlap pairs
    for dname, dom in results["domains"].items():
        if dom["overlap_zone_action_pairs"]:
            print(f"{dname} overlap pairs:")
            for entry in dom["overlap_zone_action_pairs"][:5]:
                print(f"  {entry['pair'][0]} vs {entry['pair'][1]}: {entry['count']} cases")
            if dom["pair_disambiguation"]:
                for pd in dom["pair_disambiguation"][:5]:
                    margin_str = f"{pd['mean_margin']:.4f}" if pd["mean_margin"] is not None else "n/a"
                    print(f"    -> acc={pd['accuracy']:.2%}, conf={pd['mean_confidence']:.4f}, margin={margin_str}")
            print()

    print(f"Reports saved to: {output_dir}")
    print(f"  - {output_dir / 'overlap_analysis.json'}")
    print(f"  - {output_dir / 'overlap_analysis.md'}")


if __name__ == "__main__":
    main()
