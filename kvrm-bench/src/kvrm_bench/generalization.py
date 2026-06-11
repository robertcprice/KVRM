"""LOOCV and stratified K-fold generalization analysis for KVRM compact selectors.

Measures actual holdout accuracy of RandomForest compact selectors trained on
small labelled datasets (12-31 cases).  100 % train accuracy with 256 estimators
and min_samples_leaf=1 is expected but tells us nothing about how well the model
will generalise to unseen inputs.  This module answers that question.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import LeaveOneOut, StratifiedKFold

from kvrm_core.learned import encode_batch, infer_feature_schema

# ── domain map ──────────────────────────────────────────────────────────────────
DOMAIN_ROUTER_MAP: dict[str, str] = {
    "soc": "soc-playbook-router",
    "sre": "sre-policy-router",
    "drone": "drone-mission-router",
    "grid": "grid-ops-router",
    "finance": "finance-risk-router",
    "medical": "medical-workflow-router",
    "iam": "iam-access-router",
    "customer_support": "customer-support-router",
    "content_moderation": "content-moderation-router",
}


# ── helpers ─────────────────────────────────────────────────────────────────────

def _load_supported_cases(train_path: Path) -> list[dict[str, Any]]:
    """Load train_cases.jsonl and filter to supported rows with labels."""
    cases: list[dict[str, Any]] = []
    with train_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("expected_action_id") is not None and row.get("supported", True):
                cases.append(row)
    return cases


def _build_model(
    cases: list[dict[str, Any]],
    schema: dict[str, str | list[str]],
    feature_order: list[str],
    random_state: int = 42,
    n_estimators: int = 256,
) -> RandomForestClassifier:
    """Train a RandomForest on the given cases using a pre-computed schema."""
    X = encode_batch(cases, schema, feature_order)
    y = np.array([c["expected_action_id"] for c in cases], dtype=object)
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        class_weight="balanced_subsample",
        min_samples_leaf=1,
    )
    clf.fit(X, y)
    return clf


# ── core CV routines ────────────────────────────────────────────────────────────

def run_loocv(
    cases: list[dict[str, Any]],
    *,
    random_state: int = 42,
    n_estimators: int = 256,
) -> dict[str, Any]:
    """Leave-one-out cross-validation on supported training cases.

    Returns a dict with:
      accuracy       – overall fraction correct
      misclassified  – list of {index, case_id, true, predicted}
      y_true         – full list of true labels
      y_pred         – full list of predicted labels
    """
    schema, feature_order = infer_feature_schema(cases)
    n = len(cases)
    y_true_all: list[str] = []
    y_pred_all: list[str] = []
    misclassified: list[dict[str, Any]] = []

    loo = LeaveOneOut()
    indices = list(range(n))

    for train_idx, test_idx in loo.split(indices):
        train_fold = [cases[i] for i in train_idx]
        test_case = cases[test_idx[0]]

        # Need at least 2 classes to train; if the held-out case removes the
        # only representative of a class and leaves <2 classes, skip gracefully.
        train_labels = {c["expected_action_id"] for c in train_fold}
        if len(train_labels) < 2:
            # Cannot train with a single class — mark as miss
            true_label = test_case["expected_action_id"]
            y_true_all.append(true_label)
            y_pred_all.append("__untrained__")
            misclassified.append({
                "index": test_idx[0],
                "case_id": test_case.get("case_id", f"row_{test_idx[0]}"),
                "true": true_label,
                "predicted": "__untrained__",
                "reason": "single-class fold",
            })
            continue

        clf = _build_model(train_fold, schema, feature_order, random_state, n_estimators)
        X_test = encode_batch([test_case], schema, feature_order)
        pred = clf.predict(X_test)[0]
        true_label = test_case["expected_action_id"]

        y_true_all.append(true_label)
        y_pred_all.append(str(pred))

        if str(pred) != true_label:
            misclassified.append({
                "index": test_idx[0],
                "case_id": test_case.get("case_id", f"row_{test_idx[0]}"),
                "true": true_label,
                "predicted": str(pred),
            })

    correct = sum(1 for t, p in zip(y_true_all, y_pred_all) if t == p)
    accuracy = correct / n if n else 0.0

    return {
        "accuracy": accuracy,
        "n_cases": n,
        "n_correct": correct,
        "n_misclassified": len(misclassified),
        "misclassified": misclassified,
        "y_true": y_true_all,
        "y_pred": y_pred_all,
    }


def run_stratified_kfold(
    cases: list[dict[str, Any]],
    *,
    random_state: int = 42,
    n_estimators: int = 256,
    k: int | None = None,
) -> dict[str, Any]:
    """Stratified K-fold CV.  k defaults to min(5, smallest_class_count)."""
    schema, feature_order = infer_feature_schema(cases)
    labels = [c["expected_action_id"] for c in cases]
    label_counts = Counter(labels)
    min_class_size = min(label_counts.values())

    if k is None:
        k = min(5, min_class_size)
    k = max(2, k)  # floor at 2-fold

    y = np.array(labels, dtype=object)
    X = encode_batch(cases, schema, feature_order)

    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=random_state)

    fold_accuracies: list[float] = []
    y_true_all: list[str] = []
    y_pred_all: list[str] = []

    for train_idx, test_idx in skf.split(X, y):
        train_fold = [cases[i] for i in train_idx]
        test_fold = [cases[i] for i in test_idx]

        clf = _build_model(train_fold, schema, feature_order, random_state, n_estimators)
        X_test = encode_batch(test_fold, schema, feature_order)
        preds = clf.predict(X_test)

        true_labels = [cases[i]["expected_action_id"] for i in test_idx]
        fold_correct = sum(1 for t, p in zip(true_labels, preds) if t == str(p))
        fold_accuracies.append(fold_correct / len(test_idx))

        y_true_all.extend(true_labels)
        y_pred_all.extend(str(p) for p in preds)

    correct = sum(1 for t, p in zip(y_true_all, y_pred_all) if t == p)

    return {
        "k": k,
        "overall_accuracy": correct / len(y_true_all) if y_true_all else 0.0,
        "fold_accuracies": fold_accuracies,
        "mean_fold_accuracy": float(np.mean(fold_accuracies)),
        "std_fold_accuracy": float(np.std(fold_accuracies)),
        "n_cases": len(cases),
        "y_true": y_true_all,
        "y_pred": y_pred_all,
    }


# ── per-class and confusion analysis ────────────────────────────────────────────

def per_class_accuracy(y_true: list[str], y_pred: list[str]) -> dict[str, dict[str, Any]]:
    """Compute accuracy, support, and error destinations per class."""
    class_stats: dict[str, dict[str, Any]] = {}
    by_class: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for t, p in zip(y_true, y_pred):
        by_class[t].append((t, p))

    for cls, pairs in sorted(by_class.items()):
        correct = sum(1 for t, p in pairs if t == p)
        errors = Counter(p for t, p in pairs if t != p)
        class_stats[cls] = {
            "support": len(pairs),
            "correct": correct,
            "accuracy": correct / len(pairs) if pairs else 0.0,
            "errors": dict(errors),
        }
    return class_stats


def confusion_summary(
    y_true: list[str],
    y_pred: list[str],
) -> dict[str, Any]:
    """Build a confusion matrix summary."""
    all_labels = sorted(set(y_true) | set(y_pred))
    # Filter out synthetic labels like __untrained__
    real_labels = [l for l in all_labels if not l.startswith("__")]
    cm = confusion_matrix(y_true, y_pred, labels=real_labels)
    return {
        "labels": real_labels,
        "matrix": cm.tolist(),
    }


# ── single-domain orchestration ─────────────────────────────────────────────────

def analyse_domain(
    domain: str,
    repo_root: str | Path,
    *,
    random_state: int = 42,
    n_estimators: int = 256,
) -> dict[str, Any]:
    """Run full generalization analysis for one domain."""
    repo_root = Path(repo_root)
    router_name = DOMAIN_ROUTER_MAP[domain]
    data_dir = repo_root / "kvrm-demos" / router_name / "data"

    cases = _load_supported_cases(data_dir / "train_cases.jsonl")
    label_dist = dict(Counter(c["expected_action_id"] for c in cases).most_common())
    n_classes = len(label_dist)

    # LOOCV
    loocv = run_loocv(cases, random_state=random_state, n_estimators=n_estimators)

    # Stratified K-fold
    kfold = run_stratified_kfold(cases, random_state=random_state, n_estimators=n_estimators)

    # Per-class breakdown from LOOCV
    pca = per_class_accuracy(loocv["y_true"], loocv["y_pred"])

    # Confusion matrix from LOOCV
    cm = confusion_summary(loocv["y_true"], loocv["y_pred"])

    # Train accuracy (full set)
    schema, feature_order = infer_feature_schema(cases)
    full_model = _build_model(cases, schema, feature_order, random_state, n_estimators)
    X_full = encode_batch(cases, schema, feature_order)
    train_preds = full_model.predict(X_full)
    train_acc = float((train_preds == np.array([c["expected_action_id"] for c in cases], dtype=object)).mean())

    return {
        "domain": domain,
        "n_cases": len(cases),
        "n_classes": n_classes,
        "label_distribution": label_dist,
        "train_accuracy": train_acc,
        "loocv": {
            "accuracy": loocv["accuracy"],
            "n_correct": loocv["n_correct"],
            "n_misclassified": loocv["n_misclassified"],
            "misclassified": loocv["misclassified"],
        },
        "stratified_kfold": {
            "k": kfold["k"],
            "overall_accuracy": kfold["overall_accuracy"],
            "mean_fold_accuracy": kfold["mean_fold_accuracy"],
            "std_fold_accuracy": kfold["std_fold_accuracy"],
            "fold_accuracies": kfold["fold_accuracies"],
        },
        "per_class_accuracy": pca,
        "confusion_matrix": cm,
    }


# ── full sweep ──────────────────────────────────────────────────────────────────

def run_all_domains(
    repo_root: str | Path,
    *,
    random_state: int = 42,
    n_estimators: int = 256,
) -> dict[str, Any]:
    """Run generalization analysis across all 9 domains."""
    repo_root = Path(repo_root)
    results: dict[str, Any] = {}
    for domain in sorted(DOMAIN_ROUTER_MAP):
        print(f"  [{domain}] analysing...")
        results[domain] = analyse_domain(
            domain, repo_root, random_state=random_state, n_estimators=n_estimators,
        )
        acc = results[domain]["loocv"]["accuracy"]
        n = results[domain]["n_cases"]
        print(f"  [{domain}] LOOCV {acc:.1%}  ({n} cases)")
    return results


# ── reporting ───────────────────────────────────────────────────────────────────

def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def generate_markdown_report(results: dict[str, Any]) -> str:
    """Build a detailed Markdown report from run_all_domains output."""
    lines: list[str] = []
    lines.append("# KVRM Compact Selector — Generalization Analysis")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")

    # ── summary table ──
    lines.append("## Summary")
    lines.append("")
    lines.append("| Domain | Cases | Classes | Train Acc | LOOCV Acc | K-Fold Acc (mean +/- std) | k | Drop |")
    lines.append("|--------|------:|--------:|----------:|----------:|--------------------------:|--:|-----:|")

    for domain in sorted(results):
        r = results[domain]
        drop = r["train_accuracy"] - r["loocv"]["accuracy"]
        kf = r["stratified_kfold"]
        kfold_str = f"{_fmt_pct(kf['mean_fold_accuracy'])} +/- {_fmt_pct(kf['std_fold_accuracy'])}"
        flag = " **" if drop > 0.15 else ""
        lines.append(
            f"| {domain} | {r['n_cases']} | {r['n_classes']} | "
            f"{_fmt_pct(r['train_accuracy'])} | {_fmt_pct(r['loocv']['accuracy'])}{flag} | "
            f"{kfold_str} | {kf['k']} | {_fmt_pct(drop)} |"
        )

    # ── per-domain detail ──
    for domain in sorted(results):
        r = results[domain]
        lines.append("")
        lines.append(f"## {domain}")
        lines.append("")
        lines.append(f"- **Cases**: {r['n_cases']}  |  **Classes**: {r['n_classes']}")
        lines.append(f"- **Train accuracy**: {_fmt_pct(r['train_accuracy'])}")
        lines.append(f"- **LOOCV accuracy**: {_fmt_pct(r['loocv']['accuracy'])} "
                      f"({r['loocv']['n_correct']}/{r['n_cases']})")
        kf = r["stratified_kfold"]
        lines.append(f"- **{kf['k']}-fold CV**: {_fmt_pct(kf['mean_fold_accuracy'])} "
                      f"+/- {_fmt_pct(kf['std_fold_accuracy'])} "
                      f"(folds: {', '.join(_fmt_pct(a) for a in kf['fold_accuracies'])})")

        # label distribution
        lines.append("")
        lines.append("### Label Distribution")
        lines.append("")
        lines.append("| Action | Count |")
        lines.append("|--------|------:|")
        for action_id, count in sorted(r["label_distribution"].items(), key=lambda x: -x[1]):
            lines.append(f"| {action_id} | {count} |")

        # per-class accuracy
        lines.append("")
        lines.append("### Per-Class LOOCV Accuracy")
        lines.append("")
        lines.append("| Action | Support | Correct | Accuracy | Errors |")
        lines.append("|--------|--------:|--------:|---------:|--------|")
        for action_id, stats in sorted(r["per_class_accuracy"].items()):
            err_str = ", ".join(f"{k}({v})" for k, v in stats["errors"].items()) if stats["errors"] else "-"
            lines.append(
                f"| {action_id} | {stats['support']} | {stats['correct']} | "
                f"{_fmt_pct(stats['accuracy'])} | {err_str} |"
            )

        # misclassified cases
        if r["loocv"]["misclassified"]:
            lines.append("")
            lines.append("### Misclassified Cases (LOOCV)")
            lines.append("")
            lines.append("| Case ID | True Label | Predicted |")
            lines.append("|---------|------------|-----------|")
            for mc in r["loocv"]["misclassified"]:
                lines.append(f"| {mc['case_id']} | {mc['true']} | {mc['predicted']} |")

        # confusion matrix
        cm = r["confusion_matrix"]
        if cm["labels"]:
            lines.append("")
            lines.append("### Confusion Matrix")
            lines.append("")
            header = "| |" + "|".join(f" {l} " for l in cm["labels"]) + "|"
            lines.append(header)
            lines.append("|" + "|".join(["---"] * (len(cm["labels"]) + 1)) + "|")
            for i, label in enumerate(cm["labels"]):
                row_vals = "|".join(f" {v} " for v in cm["matrix"][i])
                lines.append(f"| **{label}** |{row_vals}|")

    # ── overall conclusion ──
    lines.append("")
    lines.append("## Key Findings")
    lines.append("")

    perfect = [d for d in results if results[d]["loocv"]["accuracy"] == 1.0]
    imperfect = [(d, results[d]["loocv"]["accuracy"]) for d in results if results[d]["loocv"]["accuracy"] < 1.0]
    imperfect.sort(key=lambda x: x[1])

    if perfect:
        lines.append(f"- **Perfect LOOCV**: {', '.join(sorted(perfect))} "
                      f"({len(perfect)}/{len(results)} domains)")

    if imperfect:
        lines.append(f"- **Below 100% LOOCV**: {len(imperfect)} domains")
        for domain, acc in imperfect:
            r = results[domain]
            n_miss = r["loocv"]["n_misclassified"]
            lines.append(f"  - **{domain}**: {_fmt_pct(acc)} ({n_miss} misclassified)")

    overall_accs = [results[d]["loocv"]["accuracy"] for d in results]
    lines.append(f"- **Mean LOOCV across domains**: {_fmt_pct(np.mean(overall_accs))}")
    lines.append(f"- **Min LOOCV**: {_fmt_pct(min(overall_accs))}")

    lines.append("")
    return "\n".join(lines)


def save_results(
    results: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write JSON + Markdown reports to output_dir."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON — serialise numpy/non-JSON types
    json_path = output_dir / "generalization_results.json"
    serialisable = json.loads(json.dumps(results, default=str))
    json_path.write_text(json.dumps(serialisable, indent=2))

    # Markdown
    md_path = output_dir / "generalization_report.md"
    md_path.write_text(generate_markdown_report(results))

    return {"json": json_path, "markdown": md_path}


# ── CLI entry-point ─────────────────────────────────────────────────────────────

def main() -> None:
    """Run the full generalization sweep from the command line."""
    # Determine repo root — walk up from this file
    this_file = Path(__file__).resolve()
    # kvrm-bench/src/kvrm_bench/generalization.py  →  repo root is 4 levels up
    repo_root = this_file.parents[3]

    output_dir = repo_root / "kvrm-bench-results" / "generalization"
    print("=" * 72)
    print("KVRM Compact Selector — Generalization Analysis (LOOCV + K-Fold CV)")
    print("=" * 72)
    print(f"Repo root : {repo_root}")
    print(f"Output dir: {output_dir}")
    print()

    results = run_all_domains(repo_root)
    paths = save_results(results, output_dir)

    print()
    print("=" * 72)
    print("RESULTS SUMMARY")
    print("=" * 72)
    print()
    print(f"{'Domain':<22} {'Cases':>5} {'Classes':>7}  {'Train':>7} {'LOOCV':>7} {'K-Fold':>7}  {'Drop':>6}")
    print("-" * 72)
    for domain in sorted(results):
        r = results[domain]
        drop = r["train_accuracy"] - r["loocv"]["accuracy"]
        kf = r["stratified_kfold"]
        marker = " <<<" if drop > 0.15 else ""
        print(
            f"{domain:<22} {r['n_cases']:>5} {r['n_classes']:>7}  "
            f"{_fmt_pct(r['train_accuracy']):>7} {_fmt_pct(r['loocv']['accuracy']):>7} "
            f"{_fmt_pct(kf['mean_fold_accuracy']):>7}  {_fmt_pct(drop):>6}{marker}"
        )

    print()

    # Highlight trouble spots
    imperfect = [(d, results[d]) for d in results if results[d]["loocv"]["accuracy"] < 1.0]
    if imperfect:
        print("DOMAINS WITH LOOCV < 100%:")
        for domain, r in sorted(imperfect, key=lambda x: x[1]["loocv"]["accuracy"]):
            print(f"\n  {domain} — LOOCV {_fmt_pct(r['loocv']['accuracy'])} "
                  f"({r['loocv']['n_misclassified']} misclassified of {r['n_cases']})")
            for mc in r["loocv"]["misclassified"]:
                print(f"    {mc['case_id']}: {mc['true']} -> {mc['predicted']}")
    else:
        print("ALL 9 DOMAINS ACHIEVE 100% LOOCV — models generalise perfectly on these sets.")

    overall = [results[d]["loocv"]["accuracy"] for d in results]
    print(f"\nMean LOOCV accuracy: {_fmt_pct(np.mean(overall))}")
    print(f"Min  LOOCV accuracy: {_fmt_pct(min(overall))}")
    print()
    print(f"Reports written to:")
    print(f"  JSON:     {paths['json']}")
    print(f"  Markdown: {paths['markdown']}")


if __name__ == "__main__":
    main()
