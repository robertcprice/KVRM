"""Feature importance and interpretability analysis for KVRM compact selectors.

Computes RandomForest feature importances and optionally SHAP values
for each domain's trained compact selector model.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from .demo import DOMAIN_CONFIG

DEFAULT_MODEL_DIR = "kvrm-models"
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_REPORT_JSON = "interpretability_report.json"
DEFAULT_REPORT_MD = "interpretability_report.md"

# Feature-schema sentinels (must match kvrm_core.learned)
NUMERIC_SCHEMA = "numeric"
BOOLEAN_SCHEMA = "boolean"


# ---------------------------------------------------------------------------
# Feature name expansion
# ---------------------------------------------------------------------------


def _expand_feature_names(
    feature_schema: dict[str, str | list[str]],
    feature_order: list[str],
) -> list[str]:
    """Expand the compact feature schema into one human-readable name per
    column in the encoded feature vector.

    For numeric and boolean features the name is unchanged.  For categorical
    (one-hot) features, one name per category plus an ``<unknown>`` sentinel
    is emitted.
    """
    names: list[str] = []
    for feature_name in feature_order:
        spec = feature_schema.get(feature_name)
        if spec == NUMERIC_SCHEMA:
            names.append(feature_name)
        elif spec == BOOLEAN_SCHEMA:
            names.append(feature_name)
        elif isinstance(spec, list):
            for category in spec:
                names.append(f"{feature_name}={category}")
            names.append(f"{feature_name}=<unknown>")
        else:
            # Fallback for unexpected schema type
            names.append(feature_name)
    return names


def _collapse_importances_to_features(
    expanded_names: list[str],
    importances: np.ndarray,
    feature_order: list[str],
) -> list[tuple[str, float]]:
    """Sum per-column importances back to the original feature granularity.

    All one-hot columns belonging to the same categorical feature are summed
    so that the result is one importance value per original feature.
    """
    feature_totals: dict[str, float] = {f: 0.0 for f in feature_order}
    for name, imp in zip(expanded_names, importances):
        base = name.split("=")[0]
        if base in feature_totals:
            feature_totals[base] += float(imp)
        else:
            feature_totals[name] = float(imp)

    result = [(fname, feature_totals[fname]) for fname in feature_order if fname in feature_totals]
    # Include any orphaned expanded names not in feature_order
    for fname, total in feature_totals.items():
        if fname not in feature_order:
            result.append((fname, total))
    return result


# ---------------------------------------------------------------------------
# Per-class importance (mean decrease in impurity per class)
# ---------------------------------------------------------------------------


def _per_class_importances(
    model: Any,
    expanded_names: list[str],
    feature_order: list[str],
) -> dict[str, list[dict[str, Any]]] | None:
    """Compute per-class feature importances when possible.

    Uses the per-tree weighted impurity decrease disaggregated by class label.
    Falls back to ``None`` if the model does not expose the necessary
    internals.
    """
    try:
        classes = list(model.classes_)
    except AttributeError:
        return None

    n_features = len(expanded_names)
    n_classes = len(classes)

    # Accumulate per-class importances across trees
    per_class_imp = np.zeros((n_classes, n_features), dtype=np.float64)
    tree_count = 0

    for estimator in model.estimators_:
        tree = estimator.tree_
        n_nodes = tree.node_count
        left = tree.children_left
        right = tree.children_right
        feature_idx = tree.feature
        impurity = tree.impurity
        n_samples = tree.n_node_samples
        value = tree.value  # shape (n_nodes, 1, n_classes) for classification

        for node_id in range(n_nodes):
            if left[node_id] == right[node_id]:
                # Leaf node
                continue

            feat = feature_idx[node_id]
            if feat < 0 or feat >= n_features:
                continue

            # Weighted impurity decrease
            n_t = n_samples[node_id]
            n_l = n_samples[left[node_id]]
            n_r = n_samples[right[node_id]]
            imp_decrease = (
                n_t * impurity[node_id]
                - n_l * impurity[left[node_id]]
                - n_r * impurity[right[node_id]]
            )
            if imp_decrease <= 0:
                continue

            # Distribute to classes proportionally by node class distribution
            class_dist = value[node_id].ravel()
            class_total = class_dist.sum()
            if class_total > 0:
                class_fractions = class_dist / class_total
                per_class_imp[:, feat] += imp_decrease * class_fractions

        tree_count += 1

    if tree_count == 0:
        return None

    # Normalize per class
    for c in range(n_classes):
        total = per_class_imp[c].sum()
        if total > 0:
            per_class_imp[c] /= total

    # Collapse to original feature granularity and build output
    result: dict[str, list[dict[str, Any]]] = {}
    for c_idx, class_label in enumerate(classes):
        collapsed = _collapse_importances_to_features(
            expanded_names, per_class_imp[c_idx], feature_order
        )
        collapsed.sort(key=lambda x: x[1], reverse=True)
        result[str(class_label)] = [
            {"feature": fname, "importance": round(imp, 6)}
            for fname, imp in collapsed
        ]
    return result


# ---------------------------------------------------------------------------
# Primary analysis
# ---------------------------------------------------------------------------


def analyze_selector_interpretability(
    *,
    repo_root: str | Path,
    domain: str,
    model_path: str | Path,
) -> dict[str, Any]:
    """Analyze feature importances for a single domain's compact selector.

    Loads the joblib artifact, extracts the RandomForest model, computes
    global and per-class feature importances, and returns a structured dict.
    """
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"model artifact not found: {model_path}")

    artifact = joblib.load(model_path)

    model = artifact["model"]
    feature_schema: dict[str, str | list[str]] = artifact["feature_schema"]
    feature_order: list[str] = artifact["feature_order"]
    metadata = artifact.get("metadata", {})
    label_list = artifact.get("label_list", [])

    expanded_names = _expand_feature_names(feature_schema, feature_order)
    raw_importances = model.feature_importances_

    # Collapse one-hot importances to feature-level
    collapsed = _collapse_importances_to_features(expanded_names, raw_importances, feature_order)
    collapsed.sort(key=lambda x: x[1], reverse=True)

    global_importances = [
        {"feature": fname, "importance": round(imp, 6), "rank": rank + 1}
        for rank, (fname, imp) in enumerate(collapsed)
    ]

    # Per-class importances
    per_action = _per_class_importances(model, expanded_names, feature_order)

    # Count actions
    try:
        action_count = len(model.classes_)
    except AttributeError:
        action_count = len(label_list)

    return {
        "domain": domain,
        "model_path": str(model_path),
        "feature_count": len(feature_order),
        "action_count": action_count,
        "global_feature_importances": global_importances,
        "per_action_importances": per_action,
        "metadata": {
            "n_estimators": int(metadata.get("n_estimators", getattr(model, "n_estimators", 0))),
            "train_case_count": int(metadata.get("train_case_count", 0)),
            "train_accuracy": float(metadata.get("train_accuracy", 0.0)),
        },
    }


# ---------------------------------------------------------------------------
# Multi-domain runner
# ---------------------------------------------------------------------------


def run_interpretability_analysis(
    *,
    repo_root: str | Path,
    model_dir: str = DEFAULT_MODEL_DIR,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run interpretability analysis for all domains with trained models.

    Scans *model_dir* for ``{domain}_compact_selector_v1.joblib`` artifacts
    matching known domains in ``DOMAIN_CONFIG``.
    """
    repo_root = Path(repo_root)
    models_root = repo_root / model_dir
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_dir": str(models_root),
        "domains": {},
        "summary": {},
    }

    analyzed_count = 0
    skipped_count = 0

    for domain in sorted(DOMAIN_CONFIG.keys()):
        model_path = models_root / f"{domain}_compact_selector_v1.joblib"
        if not model_path.exists():
            skipped_count += 1
            continue

        try:
            result = analyze_selector_interpretability(
                repo_root=repo_root,
                domain=domain,
                model_path=model_path,
            )
            payload["domains"][domain] = result
            analyzed_count += 1
        except Exception as exc:
            payload["domains"][domain] = {
                "domain": domain,
                "error": str(exc),
            }
            skipped_count += 1

    payload["summary"] = {
        "analyzed_domain_count": analyzed_count,
        "skipped_domain_count": skipped_count,
        "total_domain_count": len(DOMAIN_CONFIG),
    }

    report_paths = write_interpretability_reports(payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    return payload


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_interpretability_markdown(payload: dict[str, Any]) -> str:
    """Render a markdown report from interpretability analysis results."""
    summary = payload["summary"]
    lines = [
        "# KVRM Feature Interpretability Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "This report shows RandomForest feature importances (mean decrease in impurity) "
            "for each domain's compact learned selector.  Features are ranked by their "
            "contribution to decision-making.  Per-action importances show which features "
            "matter most for routing to each specific action."
        ),
        "",
        f"**Analyzed domains**: {summary['analyzed_domain_count']} / {summary['total_domain_count']}  ",
        f"**Skipped**: {summary['skipped_domain_count']}",
        "",
    ]

    for domain, dp in payload["domains"].items():
        if "error" in dp:
            lines.append(f"## {domain} (ERROR)")
            lines.append("")
            lines.append(f"Error: {dp['error']}")
            lines.append("")
            continue

        meta = dp.get("metadata", {})
        lines.append(f"## {domain}")
        lines.append("")
        lines.append(
            f"**Features**: {dp['feature_count']} | "
            f"**Actions**: {dp['action_count']} | "
            f"**Estimators**: {meta.get('n_estimators', 'N/A')} | "
            f"**Train cases**: {meta.get('train_case_count', 'N/A')} | "
            f"**Train accuracy**: {meta.get('train_accuracy', 0.0):.4f}"
        )
        lines.append("")

        # Global importance table
        lines.append("### Global Feature Importances")
        lines.append("")
        lines.append("| Rank | Feature | Importance |")
        lines.append("| ---: | --- | ---: |")
        for entry in dp.get("global_feature_importances", []):
            lines.append(
                f"| {entry['rank']} | {entry['feature']} | {entry['importance']:.4f} |"
            )
        lines.append("")

        # Per-action importances (top 5 per action)
        per_action = dp.get("per_action_importances")
        if per_action:
            lines.append("### Per-Action Top Features")
            lines.append("")
            lines.append("| Action | Top Features |")
            lines.append("| --- | --- |")
            for action_id, features in sorted(per_action.items()):
                top_features = features[:5]
                feature_strs = ", ".join(
                    f"{f['feature']} ({f['importance']:.3f})" for f in top_features
                )
                lines.append(f"| {action_id} | {feature_strs} |")
            lines.append("")

    return "\n".join(lines) + "\n"


def write_interpretability_reports(
    payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write JSON and markdown reports to *output_dir*."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / DEFAULT_REPORT_JSON
    report_md = output_dir / DEFAULT_REPORT_MD
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_interpretability_markdown(payload), encoding="utf-8")
    return {"json": report_json, "md": report_md}
