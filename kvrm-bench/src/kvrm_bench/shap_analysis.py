"""SHAP-based directional feature importance analysis for KVRM compact selectors.

Unlike standard feature importances (mean decrease in impurity), SHAP values
show the *direction* of each feature's influence: does higher toxicity push
toward remove_content or away from it?  This is critical for auditability.
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
DEFAULT_REPORT_JSON = "shap_analysis_report.json"
DEFAULT_REPORT_MD = "shap_analysis_report.md"


def _load_training_data(
    repo_root: Path,
    domain: str,
) -> tuple[list[dict[str, Any]], Path]:
    """Load supported training cases for a domain."""
    cfg = DOMAIN_CONFIG[domain]
    train_path = repo_root / cfg["data_dir"] / "train_cases.jsonl"
    cases = []
    with train_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            case = json.loads(line)
            if case.get("expected_action_id") is not None and case.get("supported", True):
                cases.append(case)
    return cases, train_path


def analyze_shap_importances(
    *,
    repo_root: str | Path,
    domain: str,
    model_path: str | Path,
    max_background: int = 50,
) -> dict[str, Any]:
    """Compute SHAP values for a domain's compact selector.

    Uses TreeExplainer for RandomForest models (exact, fast).
    Returns per-feature mean absolute SHAP values (global importance)
    and per-class directional SHAP summaries.
    """
    import shap

    repo_root = Path(repo_root)
    model_path = Path(model_path)
    artifact = joblib.load(model_path)

    model = artifact["model"]
    feature_schema = artifact["feature_schema"]
    feature_order = artifact["feature_order"]
    metadata = artifact.get("metadata", {})

    # Load training data and encode it
    from kvrm_core.learned import encode_batch, infer_feature_schema

    train_cases, _ = _load_training_data(repo_root, domain)
    if not train_cases:
        return {"domain": domain, "error": "no supported training cases"}

    # Re-infer schema from training data (must match artifact schema)
    schema, f_order = infer_feature_schema(train_cases)

    # Encode training matrix
    matrix = encode_batch(train_cases, schema, f_order)
    labels = np.array([c["expected_action_id"] for c in train_cases], dtype=object)

    # Build expanded feature names (matching interpretability.py logic)
    expanded_names: list[str] = []
    for fname in f_order:
        spec = schema.get(fname)
        if spec in ("numeric", "boolean"):
            expanded_names.append(fname)
        elif isinstance(spec, list):
            for cat in spec:
                expanded_names.append(f"{fname}={cat}")
            expanded_names.append(f"{fname}=<unknown>")
        else:
            expanded_names.append(fname)

    # SHAP TreeExplainer (exact for tree ensembles)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(matrix)

    # shap_values shape varies by SHAP version:
    # - list of (n_samples, n_features) arrays, one per class
    # - (n_samples, n_features, n_classes) array
    # - (n_classes, n_samples, n_features) array
    # Normalize to (n_classes, n_samples, n_features)
    if isinstance(shap_values, list):
        shap_array = np.array(shap_values)  # (n_classes, n_samples, n_features)
    else:
        shap_array = np.array(shap_values)
        if shap_array.ndim == 2:
            # Binary case: single array (n_samples, n_features)
            shap_array = np.stack([shap_array, -shap_array])
        elif shap_array.ndim == 3 and shap_array.shape[2] == len(model.classes_):
            # Shape is (n_samples, n_features, n_classes) -> transpose
            shap_array = shap_array.transpose(2, 0, 1)

    classes = list(model.classes_)
    n_classes = len(classes)

    # --- Global importance: mean |SHAP| across all classes and samples ---
    global_mean_abs = np.mean(np.abs(shap_array), axis=(0, 1))  # (n_features,)

    # Collapse one-hot columns to feature-level
    feature_shap: dict[str, float] = {f: 0.0 for f in f_order}
    for idx, name in enumerate(expanded_names):
        base = name.split("=")[0]
        if base in feature_shap:
            feature_shap[base] += float(global_mean_abs[idx])
        else:
            feature_shap[name] = float(global_mean_abs[idx])

    # Normalize to sum to 1
    total = sum(feature_shap.values())
    if total > 0:
        feature_shap = {k: v / total for k, v in feature_shap.items()}

    global_importances = sorted(feature_shap.items(), key=lambda x: x[1], reverse=True)
    global_importances_list = [
        {"feature": fname, "shap_importance": round(imp, 6), "rank": rank + 1}
        for rank, (fname, imp) in enumerate(global_importances)
    ]

    # --- Per-class directional analysis ---
    per_action_directions: dict[str, list[dict[str, Any]]] = {}
    for c_idx, class_label in enumerate(classes):
        class_shap = shap_array[c_idx]  # (n_samples, n_features)

        # For each original feature, compute:
        # - mean_shap: average direction (positive = pushes toward this class)
        # - mean_abs_shap: average magnitude
        feature_directions: dict[str, dict[str, float]] = {}
        for fname in f_order:
            feature_directions[fname] = {"sum_shap": 0.0, "sum_abs": 0.0, "count": 0}

        for idx, name in enumerate(expanded_names):
            base = name.split("=")[0]
            if base in feature_directions:
                col_vals = class_shap[:, idx]
                feature_directions[base]["sum_shap"] += float(np.mean(col_vals))
                feature_directions[base]["sum_abs"] += float(np.mean(np.abs(col_vals)))
                feature_directions[base]["count"] += 1

        directions_list = []
        for fname in f_order:
            d = feature_directions[fname]
            n = max(d["count"], 1)
            mean_shap = d["sum_shap"]
            mean_abs = d["sum_abs"]
            direction = "pushes_toward" if mean_shap > 0.001 else ("pushes_away" if mean_shap < -0.001 else "neutral")
            directions_list.append({
                "feature": fname,
                "mean_shap": round(mean_shap, 6),
                "mean_abs_shap": round(mean_abs, 6),
                "direction": direction,
            })

        directions_list.sort(key=lambda x: x["mean_abs_shap"], reverse=True)
        per_action_directions[str(class_label)] = directions_list

    return {
        "domain": domain,
        "model_path": str(model_path),
        "feature_count": len(f_order),
        "action_count": n_classes,
        "sample_count": len(train_cases),
        "global_shap_importances": global_importances_list,
        "per_action_directions": per_action_directions,
        "metadata": {
            "n_estimators": int(metadata.get("n_estimators", 0)),
            "train_case_count": int(metadata.get("train_case_count", 0)),
            "train_accuracy": float(metadata.get("train_accuracy", 0.0)),
            "shap_method": "TreeExplainer",
        },
    }


def run_shap_analysis(
    *,
    repo_root: str | Path,
    model_dir: str = DEFAULT_MODEL_DIR,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run SHAP analysis for all domains with trained models."""
    repo_root = Path(repo_root)
    models_root = repo_root / model_dir
    results_dir = Path(output_dir) if output_dir else repo_root / "kvrm-bench-results" / "shap"

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_dir": str(models_root),
        "domains": {},
        "summary": {},
    }

    analyzed = 0
    skipped = 0

    for domain in sorted(DOMAIN_CONFIG.keys()):
        model_path = models_root / f"{domain}_compact_selector_v1.joblib"
        if not model_path.exists():
            skipped += 1
            continue
        try:
            result = analyze_shap_importances(
                repo_root=repo_root,
                domain=domain,
                model_path=model_path,
            )
            payload["domains"][domain] = result
            analyzed += 1
        except Exception as exc:
            payload["domains"][domain] = {"domain": domain, "error": str(exc)}
            skipped += 1

    payload["summary"] = {
        "analyzed_domain_count": analyzed,
        "skipped_domain_count": skipped,
        "total_domain_count": len(DOMAIN_CONFIG),
    }

    report_paths = write_shap_reports(payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    return payload


def render_shap_markdown(payload: dict[str, Any]) -> str:
    """Render markdown report with directional SHAP analysis."""
    lines = [
        "# KVRM SHAP Directional Feature Analysis",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "This report shows SHAP (SHapley Additive exPlanations) values for each domain's "
        "compact learned selector. Unlike standard feature importances, SHAP values reveal "
        "the **direction** of each feature's influence: does a feature push toward or away "
        "from a particular action?",
        "",
        f"**Analyzed domains**: {payload['summary']['analyzed_domain_count']} / "
        f"{payload['summary']['total_domain_count']}  ",
        f"**Skipped**: {payload['summary']['skipped_domain_count']}",
        "",
    ]

    for domain, dp in payload["domains"].items():
        if "error" in dp:
            lines.extend([f"## {domain} (ERROR)", "", f"Error: {dp['error']}", ""])
            continue

        meta = dp.get("metadata", {})
        lines.extend([
            f"## {domain}",
            "",
            f"**Features**: {dp['feature_count']} | "
            f"**Actions**: {dp['action_count']} | "
            f"**Samples**: {dp['sample_count']} | "
            f"**Method**: {meta.get('shap_method', 'N/A')}",
            "",
        ])

        # Global SHAP importance table
        lines.extend([
            "### Global SHAP Importances (mean |SHAP|)",
            "",
            "| Rank | Feature | SHAP Importance |",
            "| ---: | --- | ---: |",
        ])
        for entry in dp.get("global_shap_importances", []):
            lines.append(f"| {entry['rank']} | {entry['feature']} | {entry['shap_importance']:.4f} |")
        lines.append("")

        # Per-action directional table
        per_action = dp.get("per_action_directions", {})
        if per_action:
            lines.extend([
                "### Per-Action Feature Directions",
                "",
                "Shows which features push toward (+) or away from (-) each action.",
                "",
            ])
            for action_id in sorted(per_action.keys()):
                features = per_action[action_id]
                top = [f for f in features if f["mean_abs_shap"] > 0.001][:5]
                if not top:
                    continue
                lines.append(f"**{action_id}**:")
                for f in top:
                    arrow = "+" if f["direction"] == "pushes_toward" else ("-" if f["direction"] == "pushes_away" else "~")
                    lines.append(f"  - {arrow} {f['feature']} (SHAP: {f['mean_shap']:+.4f})")
                lines.append("")

    return "\n".join(lines) + "\n"


def write_shap_reports(
    payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write JSON and markdown SHAP reports."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / DEFAULT_REPORT_JSON
    md_path = output_dir / DEFAULT_REPORT_MD
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_shap_markdown(payload), encoding="utf-8")
    return {"json": json_path, "md": md_path}
