#!/usr/bin/env python3
"""Generate publication-quality figures for the KVRM paper.

Reads benchmark results from kvrm-bench-results/ and produces
matplotlib figures in docs/figures/ at 300 DPI in both PNG and PDF.

Usage:
    .venv/bin/python kvrm-bench/scripts/generate_publication_figures.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.patches import FancyBboxPatch

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "kvrm-bench-results"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
# Use a clean academic style; fall back gracefully if unavailable.
_STYLE_PREFS = [
    "seaborn-v0_8-whitegrid",
    "seaborn-whitegrid",
    "ggplot",
]
for _s in _STYLE_PREFS:
    try:
        plt.style.use(_s)
        break
    except OSError:
        continue

plt.rcParams.update(
    {
        "font.size": 12,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.15,
        "font.family": "sans-serif",
    }
)

# Colorblind-friendly palette (Okabe-Ito inspired)
CB_PALETTE = [
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # green
    "#CC79A7",  # pink
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#F0E442",  # yellow
    "#000000",  # black
]

# Domain display names (short -> human-readable)
DOMAIN_LABELS: dict[str, str] = {
    "soc": "SOC",
    "sre": "SRE",
    "drone": "Drone",
    "grid": "Grid",
    "finance": "Finance",
    "medical": "Medical",
    "iam": "IAM",
    "customer_support": "Cust. Support",
    "content_moderation": "Content Mod.",
}

# Domain category mapping for scatter plot shapes
DOMAIN_CATEGORIES: dict[str, str] = {
    "soc": "infrastructure",
    "sre": "infrastructure",
    "drone": "infrastructure",
    "grid": "infrastructure",
    "finance": "enterprise",
    "medical": "enterprise",
    "iam": "enterprise",
    "customer_support": "trust-safety",
    "content_moderation": "trust-safety",
}

CATEGORY_MARKERS: dict[str, str] = {
    "infrastructure": "o",
    "enterprise": "s",
    "trust-safety": "D",
}

# Canonical domain ordering
DOMAIN_ORDER = [
    "soc", "sre", "drone", "grid",
    "finance", "medical", "iam",
    "customer_support", "content_moderation",
]

STRATEGY_ORDER = [
    "rule", "retrieval", "semantic",
    "prototype", "learned", "hybrid",
]

STRATEGY_COLORS: dict[str, str] = {
    s: CB_PALETTE[i] for i, s in enumerate(STRATEGY_ORDER)
}


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


def load_calibration() -> dict[str, Any]:
    return load_json(RESULTS_DIR / "calibration" / "calibration_report.json")


def load_generalization() -> dict[str, Any]:
    return load_json(RESULTS_DIR / "generalization" / "generalization_results.json")


def load_overlap() -> dict[str, Any]:
    return load_json(RESULTS_DIR / "overlap_analysis" / "overlap_analysis.json")


def build_calibration_matrices(
    cal_data: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (ece_matrix, brier_matrix, mean_conf_matrix, overconf_matrix)
    each of shape (n_domains, n_strategies), plus domain/strategy label lists."""
    results = cal_data["per_strategy_domain_results"]

    ece_mat = np.full((len(DOMAIN_ORDER), len(STRATEGY_ORDER)), np.nan)
    brier_mat = np.full_like(ece_mat, np.nan)
    conf_mat = np.full_like(ece_mat, np.nan)
    overconf_mat = np.full_like(ece_mat, np.nan)

    for r in results:
        if r.get("error"):
            continue
        di = DOMAIN_ORDER.index(r["domain"])
        si = STRATEGY_ORDER.index(r["strategy"])
        ece_mat[di, si] = r["ece"]
        brier_mat[di, si] = r["brier"]
        overconf_mat[di, si] = r["overconfidence_ratio"]

        # Compute weighted mean confidence from bins
        bins = r.get("bins", [])
        total = sum(b["count"] for b in bins)
        if total > 0:
            conf_mat[di, si] = (
                sum(b["count"] * b["mean_confidence"] for b in bins if b["count"] > 0)
                / total
            )

    return ece_mat, brier_mat, conf_mat, overconf_mat


def _save(fig: plt.Figure, name: str) -> list[Path]:
    """Save figure as PNG and PDF, close it, return paths."""
    paths = []
    for ext in ("png", "pdf"):
        p = OUTPUT_DIR / f"{name}.{ext}"
        fig.savefig(p, format=ext)
        paths.append(p)
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------
# Figure 1: ECE Heatmap
# ---------------------------------------------------------------------------

def fig_ece_heatmap(ece_mat: np.ndarray) -> list[Path]:
    fig, ax = plt.subplots(figsize=(12, 8))

    domain_labels = [DOMAIN_LABELS[d] for d in DOMAIN_ORDER]
    strategy_labels = [s.capitalize() for s in STRATEGY_ORDER]

    # Mask NaN for display
    masked = np.ma.masked_invalid(ece_mat)

    im = ax.imshow(masked, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=0.35)

    # Annotate cells and highlight best per domain
    best_per_domain = np.nanargmin(ece_mat, axis=1)
    for i in range(ece_mat.shape[0]):
        for j in range(ece_mat.shape[1]):
            val = ece_mat[i, j]
            if np.isnan(val):
                ax.text(j, i, "N/A", ha="center", va="center", fontsize=9, color="gray")
                continue
            # Pick text color for contrast
            color = "white" if val > 0.15 else "black"
            weight = "bold" if j == best_per_domain[i] else "normal"
            ax.text(
                j, i, f"{val:.3f}",
                ha="center", va="center", fontsize=9,
                color=color, fontweight=weight,
            )
            # Draw border around best cell
            if j == best_per_domain[i]:
                rect = FancyBboxPatch(
                    (j - 0.48, i - 0.48), 0.96, 0.96,
                    boxstyle="round,pad=0.02",
                    linewidth=2.5, edgecolor="black", facecolor="none",
                )
                ax.add_patch(rect)

    ax.set_xticks(range(len(strategy_labels)))
    ax.set_xticklabels(strategy_labels, rotation=30, ha="right")
    ax.set_yticks(range(len(domain_labels)))
    ax.set_yticklabels(domain_labels)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, label="ECE (lower is better)")
    ax.set_title("Expected Calibration Error by Domain and Strategy", pad=12)
    ax.set_xlabel("Strategy")
    ax.set_ylabel("Domain")

    fig.tight_layout()
    return _save(fig, "fig_ece_heatmap")


# ---------------------------------------------------------------------------
# Figure 2: Brier Heatmap
# ---------------------------------------------------------------------------

def fig_brier_heatmap(brier_mat: np.ndarray) -> list[Path]:
    fig, ax = plt.subplots(figsize=(12, 8))

    domain_labels = [DOMAIN_LABELS[d] for d in DOMAIN_ORDER]
    strategy_labels = [s.capitalize() for s in STRATEGY_ORDER]

    masked = np.ma.masked_invalid(brier_mat)

    # Lower Brier = better, so use RdYlGn (green for low)
    im = ax.imshow(masked, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=1.0)

    best_per_domain = np.nanargmin(brier_mat, axis=1)
    for i in range(brier_mat.shape[0]):
        for j in range(brier_mat.shape[1]):
            val = brier_mat[i, j]
            if np.isnan(val):
                ax.text(j, i, "N/A", ha="center", va="center", fontsize=9, color="gray")
                continue
            color = "white" if val > 0.5 else "black"
            weight = "bold" if j == best_per_domain[i] else "normal"
            ax.text(
                j, i, f"{val:.3f}",
                ha="center", va="center", fontsize=9,
                color=color, fontweight=weight,
            )
            if j == best_per_domain[i]:
                rect = FancyBboxPatch(
                    (j - 0.48, i - 0.48), 0.96, 0.96,
                    boxstyle="round,pad=0.02",
                    linewidth=2.5, edgecolor="black", facecolor="none",
                )
                ax.add_patch(rect)

    ax.set_xticks(range(len(strategy_labels)))
    ax.set_xticklabels(strategy_labels, rotation=30, ha="right")
    ax.set_yticks(range(len(domain_labels)))
    ax.set_yticklabels(domain_labels)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, label="Brier Score (lower is better)")
    ax.set_title("Brier Score by Domain and Strategy", pad=12)
    ax.set_xlabel("Strategy")
    ax.set_ylabel("Domain")

    fig.tight_layout()
    return _save(fig, "fig_brier_heatmap")


# ---------------------------------------------------------------------------
# Figure 3: LOOCV Bar Chart
# ---------------------------------------------------------------------------

def fig_loocv_bar(gen_data: dict[str, Any]) -> list[Path]:
    fig, ax = plt.subplots(figsize=(10, 6))

    domains = [d for d in DOMAIN_ORDER if d in gen_data]
    accuracies = [gen_data[d]["loocv"]["accuracy"] for d in domains]
    n_classes = [gen_data[d]["n_classes"] for d in domains]
    labels = [DOMAIN_LABELS[d] for d in domains]

    # Color bars by accuracy tier
    colors = []
    for acc in accuracies:
        if acc > 0.80:
            colors.append("#2ca02c")   # green
        elif acc >= 0.40:
            colors.append("#ff7f0e")   # amber/yellow
        else:
            colors.append("#d62728")   # red

    x = np.arange(len(domains))
    bars = ax.bar(x, accuracies, color=colors, edgecolor="black", linewidth=0.5, width=0.65)

    # Add chance level lines per domain
    for i, (nc, acc) in enumerate(zip(n_classes, accuracies)):
        chance = 1.0 / nc
        ax.hlines(
            chance, i - 0.35, i + 0.35,
            colors="black", linestyles="dashed", linewidth=1.2, alpha=0.7,
        )
        # Label chance level on right side
        if i == len(domains) - 1 or i == 0:
            ax.text(
                i + 0.38, chance, f"1/{nc}",
                va="center", ha="left", fontsize=8, color="gray",
            )

    # Value labels on bars
    for bar, acc in zip(bars, accuracies):
        y_pos = bar.get_height() + 0.02
        if y_pos > 0.95:
            y_pos = bar.get_height() - 0.06
        ax.text(
            bar.get_x() + bar.get_width() / 2, y_pos,
            f"{acc:.1%}",
            ha="center", va="bottom", fontsize=9, fontweight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("LOOCV Accuracy")
    ax.set_title("Compact Selector LOOCV Generalization Accuracy", pad=12)
    ax.set_ylim(0, 1.12)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))

    # Legend for color tiers
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2ca02c", edgecolor="black", label="> 80% (strong)"),
        Patch(facecolor="#ff7f0e", edgecolor="black", label="40-80% (moderate)"),
        Patch(facecolor="#d62728", edgecolor="black", label="< 40% (weak)"),
        plt.Line2D([0], [0], color="black", linestyle="dashed", linewidth=1.2, label="Chance level"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", framealpha=0.9)

    fig.tight_layout()
    return _save(fig, "fig_loocv_bar")


# ---------------------------------------------------------------------------
# Figure 4: Overlap Zones Stacked Bar
# ---------------------------------------------------------------------------

def fig_overlap_zones(overlap_data: dict[str, Any]) -> list[Path]:
    fig, ax = plt.subplots(figsize=(10, 6))

    domains_data = overlap_data["domains"]
    domains = [d for d in DOMAIN_ORDER if d in domains_data]
    labels = [DOMAIN_LABELS[d] for d in domains]

    overlap_counts = [domains_data[d]["overlap_case_count"] for d in domains]
    non_overlap_counts = [domains_data[d]["non_overlap_case_count"] for d in domains]

    x = np.arange(len(domains))
    width = 0.6

    bars_non = ax.bar(
        x, non_overlap_counts, width,
        label="Non-overlap cases", color="#0072B2", edgecolor="black", linewidth=0.5,
    )
    bars_olap = ax.bar(
        x, overlap_counts, width,
        bottom=non_overlap_counts,
        label="Overlap cases", color="#D55E00", edgecolor="black", linewidth=0.5,
    )

    # Annotate overlap fractions where non-zero
    for i, (oc, noc) in enumerate(zip(overlap_counts, non_overlap_counts)):
        total = oc + noc
        if oc > 0:
            frac = oc / total
            ax.text(
                i, total + 1.5,
                f"{frac:.0%}\noverlap",
                ha="center", va="bottom", fontsize=9, fontweight="bold",
                color="#D55E00",
            )
        # Total label
        ax.text(
            i, total + 0.5 if oc == 0 else total + max(total * 0.12, 8),
            str(total),
            ha="center", va="bottom", fontsize=8, color="gray",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("Number of Cases")
    ax.set_title("Support-Spec Overlap Prevalence by Domain", pad=12)
    ax.legend(loc="upper right", framealpha=0.9)

    # Add some headroom
    max_total = max(oc + noc for oc, noc in zip(overlap_counts, non_overlap_counts))
    ax.set_ylim(0, max_total * 1.3)

    fig.tight_layout()
    return _save(fig, "fig_overlap_zones")


# ---------------------------------------------------------------------------
# Figure 5: Calibration-Accuracy Trade-off Scatter
# ---------------------------------------------------------------------------

def fig_calibration_tradeoff(
    ece_mat: np.ndarray, brier_mat: np.ndarray,
) -> list[Path]:
    fig, ax = plt.subplots(figsize=(10, 7))

    for si, strategy in enumerate(STRATEGY_ORDER):
        for di, domain in enumerate(DOMAIN_ORDER):
            ece_val = ece_mat[di, si]
            brier_val = brier_mat[di, si]
            if np.isnan(ece_val) or np.isnan(brier_val):
                continue

            cat = DOMAIN_CATEGORIES[domain]
            marker = CATEGORY_MARKERS[cat]
            color = STRATEGY_COLORS[strategy]

            ax.scatter(
                ece_val, brier_val,
                c=color, marker=marker, s=80,
                edgecolors="black", linewidth=0.5, alpha=0.85,
                zorder=3,
            )

    # Build legends
    # Strategy legend (color)
    strategy_handles = [
        plt.Line2D(
            [0], [0], marker="o", color="w",
            markerfacecolor=STRATEGY_COLORS[s], markersize=9,
            markeredgecolor="black", markeredgewidth=0.5,
            label=s.capitalize(),
        )
        for s in STRATEGY_ORDER
    ]
    # Category legend (shape)
    category_handles = [
        plt.Line2D(
            [0], [0], marker=CATEGORY_MARKERS[c], color="w",
            markerfacecolor="gray", markersize=9,
            markeredgecolor="black", markeredgewidth=0.5,
            label=c.replace("-", " ").title(),
        )
        for c in ["infrastructure", "enterprise", "trust-safety"]
    ]

    leg1 = ax.legend(
        handles=strategy_handles, title="Strategy",
        loc="upper left", framealpha=0.9,
    )
    ax.add_artist(leg1)
    ax.legend(
        handles=category_handles, title="Domain Category",
        loc="lower right", framealpha=0.9,
    )

    # Quadrant lines at medians
    ece_median = np.nanmedian(ece_mat)
    brier_median = np.nanmedian(brier_mat)
    ax.axvline(ece_median, color="gray", linestyle=":", alpha=0.5, linewidth=1)
    ax.axhline(brier_median, color="gray", linestyle=":", alpha=0.5, linewidth=1)

    # Quadrant labels
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    label_props = dict(fontsize=8, alpha=0.4, ha="center", va="center", style="italic")
    ax.text(ece_median / 2, brier_median / 2, "Best\n(low ECE, low Brier)", **label_props)
    ax.text((ece_median + x_max) / 2, brier_median / 2, "Accurate but\npoorly calibrated", **label_props)
    ax.text(ece_median / 2, (brier_median + y_max) / 2, "Well-calibrated\nbut inaccurate", **label_props)
    ax.text((ece_median + x_max) / 2, (brier_median + y_max) / 2, "Worst\n(high ECE, high Brier)", **label_props)

    ax.set_xlabel("Expected Calibration Error (ECE)")
    ax.set_ylabel("Brier Score")
    ax.set_title("Calibration-Accuracy Trade-off", pad=12)

    fig.tight_layout()
    return _save(fig, "fig_calibration_tradeoff")


# ---------------------------------------------------------------------------
# Figure 6: Strategy Radar Chart
# ---------------------------------------------------------------------------

def fig_strategy_radar(
    ece_mat: np.ndarray,
    brier_mat: np.ndarray,
    conf_mat: np.ndarray,
    overconf_mat: np.ndarray,
) -> list[Path]:
    """Radar chart comparing strategies across 4 metrics (averaged over domains)."""

    # Compute per-strategy averages
    metrics: dict[str, list[float]] = {}
    metric_names = [
        "Calibration\n(1 - ECE)",
        "Accuracy\n(1 - Brier)",
        "Mean\nConfidence",
        "Low\nOverconfidence",
    ]

    for si, strategy in enumerate(STRATEGY_ORDER):
        ece_vals = ece_mat[:, si]
        brier_vals = brier_mat[:, si]
        conf_vals = conf_mat[:, si]
        overconf_vals = overconf_mat[:, si]

        metrics[strategy] = [
            1.0 - np.nanmean(ece_vals),           # higher = better calibration
            1.0 - np.nanmean(brier_vals),          # higher = better accuracy
            np.nanmean(conf_vals),                  # mean confidence (0-1)
            1.0 - np.nanmean(overconf_vals),        # lower overconf = better
        ]

    n_metrics = len(metric_names)
    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    for si, strategy in enumerate(STRATEGY_ORDER):
        values = metrics[strategy] + metrics[strategy][:1]
        ax.plot(
            angles, values,
            color=STRATEGY_COLORS[strategy],
            linewidth=2, label=strategy.capitalize(),
        )
        ax.fill(angles, values, color=STRATEGY_COLORS[strategy], alpha=0.08)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metric_names, fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=8, color="gray")

    ax.legend(
        loc="upper right", bbox_to_anchor=(1.3, 1.1),
        framealpha=0.9, fontsize=10,
    )
    ax.set_title("Strategy Comparison Across Metrics", pad=20, fontsize=14)

    fig.tight_layout()
    return _save(fig, "fig_strategy_radar")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading benchmark data...")
    cal_data = load_calibration()
    gen_data = load_generalization()
    overlap_data = load_overlap()

    ece_mat, brier_mat, conf_mat, overconf_mat = build_calibration_matrices(cal_data)

    all_paths: list[Path] = []

    print("\n[1/6] ECE Heatmap...")
    all_paths.extend(fig_ece_heatmap(ece_mat))

    print("[2/6] Brier Heatmap...")
    all_paths.extend(fig_brier_heatmap(brier_mat))

    print("[3/6] LOOCV Bar Chart...")
    all_paths.extend(fig_loocv_bar(gen_data))

    print("[4/6] Overlap Zones...")
    all_paths.extend(fig_overlap_zones(overlap_data))

    print("[5/6] Calibration-Accuracy Trade-off...")
    all_paths.extend(fig_calibration_tradeoff(ece_mat, brier_mat))

    print("[6/6] Strategy Radar Chart...")
    all_paths.extend(fig_strategy_radar(ece_mat, brier_mat, conf_mat, overconf_mat))

    print(f"\n{'='*60}")
    print(f"Generated {len(all_paths)} files in {OUTPUT_DIR}/")
    print(f"{'='*60}")

    for p in sorted(all_paths):
        size_kb = p.stat().st_size / 1024
        print(f"  {p.name:40s} {size_kb:8.1f} KB")

    print(f"\nDone. All figures saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
