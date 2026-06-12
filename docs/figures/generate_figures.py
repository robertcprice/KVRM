#!/usr/bin/env python3
"""Generate KVRM paper figures as SVG files.

Usage:
    python generate_figures.py

Outputs:
    docs/figures/fig1_architecture.svg
    docs/figures/fig2_registry_lifecycle.svg
    docs/figures/fig3_supported_vs_unsupported.svg
    docs/figures/fig4_per_domain_accuracy.svg
    docs/figures/fig5_false_accept_rate.svg
    docs/figures/fig6_registry_evolution.svg
    docs/figures/fig7_architecture_comparison.svg
    docs/figures/fig4_canonical_suite.svg
    docs/figures/fig5_support_gate_stress.svg
    docs/figures/fig6_fallback_feasibility.svg
    docs/figures/fig7_robustness_families.svg
"""
from __future__ import annotations

import json
import pathlib

OUT = pathlib.Path(__file__).parent
ROOT = OUT.parent.parent

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _header(w: int, h: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'

FOOTER = "</svg>"

FONT = "font-family='Inter, Helvetica, Arial, sans-serif'"

def _esc(content):
    return str(content).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _text(x, y, size, content, anchor="start", bold=False, fill="#1a1a2e"):
    weight = "font-weight='700'" if bold else "font-weight='400'"
    return f"<text x='{x}' y='{y}' {FONT} font-size='{size}' {weight} text-anchor='{anchor}' fill='{fill}'>{_esc(content)}</text>"

def _rect(x, y, w, h, fill, rx=4, stroke="none", sw=0):
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='{rx}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>"

def _bar(x, y, w, h, fill, label="", value=""):
    parts = [_rect(x, y, w, h, fill)]
    if label:
        parts.append(_text(x - 4, y + h/2 + 4, 10, label, anchor="end", fill="#333"))
    if value:
        parts.append(_text(x + w + 4, y + h/2 + 4, 9, value, fill="#555"))
    return "\n".join(parts)


def _load_json(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def _fmt_rate(value: float) -> str:
    return f"{value:.4f}"


def _line(x1, y1, x2, y2, stroke="#d0d0d0", sw=1, dash=""):
    dash_attr = f" stroke-dasharray='{dash}'" if dash else ""
    return f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{stroke}' stroke-width='{sw}'{dash_attr}/>"


# ---------------------------------------------------------------------------
# Figure 1: Architecture diagram
# ---------------------------------------------------------------------------
def fig1_architecture():
    w, h = 700, 300
    boxes = [
        (40, 100, 110, 50, "Input\nContext", "#e8f0fe"),
        (190, 100, 110, 50, "Selector\n(Rule/Retrieval)", "#fce8e8"),
        (340, 100, 110, 50, "Calibrator\n(Threshold)", "#fef7e0"),
        (490, 100, 110, 50, "Validator\n(Registry)", "#e8f5e9"),
        (490, 200, 110, 50, "Executor\n(Deterministic)", "#f3e5f5"),
        (340, 200, 110, 50, "Audit Log\n(Artifacts)", "#f5f5f5"),
    ]
    arrows = [
        (150, 125, 190, 125),
        (300, 125, 340, 125),
        (450, 125, 490, 125),
        (545, 150, 545, 200),
        (490, 225, 450, 225),
    ]
    parts = [_header(w, h)]
    parts.append(_text(350, 30, 16, "Figure 1: KVRM Core Runtime Architecture", anchor="middle", bold=True))
    parts.append(_text(350, 55, 11, "Deterministic pipeline: prediction is never directly executed", anchor="middle", fill="#666"))
    # Registry reference
    parts.append(_rect(620, 80, 60, 100, "#fff3e0", rx=6, stroke="#ff9800", sw=1.5))
    parts.append(_text(650, 120, 9, "Registry", anchor="middle", bold=True, fill="#e65100"))
    parts.append(_text(650, 135, 8, "(versioned", anchor="middle", fill="#bf360c"))
    parts.append(_text(650, 148, 8, "hashed", anchor="middle", fill="#bf360c"))
    parts.append(_text(650, 161, 8, "finite)", anchor="middle", fill="#bf360c"))
    for bx, by, bw, bh, fill, label in boxes:
        parts.append(_rect(bx, by, bw, bh, fill, rx=6, stroke="#ccc", sw=1))
        lines = label.split("\n")
        for i, line in enumerate(lines):
            parts.append(_text(bx + bw/2, by + 18 + i*14, 10, line, anchor="middle", fill="#333"))
    for x1, y1, x2, y2 in arrows:
        parts.append(f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#555' stroke-width='1.5' marker-end='url(#arrowhead)'/>")
    # Arrow marker
    parts.append("<defs><marker id='arrowhead' markerWidth='8' markerHeight='6' refX='8' refY='3' orient='auto'><polygon points='0 0, 8 3, 0 6' fill='#555'/></marker></defs>")
    # Abstain path
    parts.append(f"<line x1='400' y1='150' x2='400' y2='200' stroke='#e53935' stroke-width='1.5' stroke-dasharray='4,3'/>")
    parts.append(_text(415, 180, 8, "abstain", fill="#e53935"))
    parts.append(FOOTER)
    (OUT / "fig1_architecture.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 4: Per-domain accuracy comparison
# ---------------------------------------------------------------------------
def fig4_per_domain_accuracy():
    w, h = 600, 320
    domains = ["SRE", "SOC", "Drone"]
    kvrm =   [1.000, 0.917, 0.917]
    rf_dir = [1.000, 0.750, 0.833]
    gbm_js= [1.000, 0.667, 0.833]
    rf_con= [1.000, 0.750, 0.833]

    bar_w = 22
    gap = 8
    group_w = 4 * bar_w + 3 * gap
    left_margin = 60
    top_margin = 80
    chart_h = 180
    max_val = 1.0
    group_gap = 100

    parts = [_header(w, h)]
    parts.append(_text(300, 30, 14, "Figure 4: Supported-Case Accuracy by Domain", anchor="middle", bold=True))
    # Y axis
    for val in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = top_margin + chart_h - int(val / max_val * chart_h)
        parts.append(f"<line x1='{left_margin}' y1='{y}' x2='{w-20}' y2='{y}' stroke='#e0e0e0' stroke-width='0.5'/>")
        parts.append(_text(left_margin - 5, y + 3, 9, f"{val:.2f}", anchor="end", fill="#888"))

    colors = ["#1565c0", "#e53935", "#fb8c00", "#43a047"]
    labels = ["KVRM", "RF Direct", "GBM JSON", "RF Constrained"]

    for di, domain in enumerate(domains):
        gx = left_margin + di * (group_w + group_gap) + 20
        values = [kvrm[di], rf_dir[di], gbm_js[di], rf_con[di]]
        for bi, (val, color) in enumerate(zip(values, colors)):
            bx = gx + bi * (bar_w + gap)
            bh = max(1, int(val / max_val * chart_h))
            by = top_margin + chart_h - bh
            parts.append(_rect(bx, by, bar_w, bh, color, rx=2))
            parts.append(_text(bx + bar_w/2, by - 4, 7, f"{val:.3f}", anchor="middle", fill="#333"))
        parts.append(_text(gx + group_w/2, top_margin + chart_h + 18, 11, domain, anchor="middle", bold=True))

    # Legend
    for li, (label, color) in enumerate(zip(labels, colors)):
        lx = 140 + li * 120
        parts.append(_rect(lx, h - 30, 10, 10, color))
        parts.append(_text(lx + 14, h - 21, 9, label, fill="#333"))
    parts.append(FOOTER)
    (OUT / "fig4_per_domain_accuracy.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 5: False-accept rate comparison (the headline chart)
# ---------------------------------------------------------------------------
def fig5_false_accept_rate():
    w, h = 600, 320
    domains = ["SRE", "SOC", "Drone"]
    kvrm =   [0.000, 0.000, 0.000]
    rf_dir = [1.000, 1.000, 1.000]
    gbm_js= [1.000, 0.750, 0.250]
    rf_con= [1.000, 1.000, 1.000]

    bar_w = 22
    gap = 8
    group_w = 4 * bar_w + 3 * gap
    left_margin = 60
    top_margin = 80
    chart_h = 180
    max_val = 1.0
    group_gap = 100

    parts = [_header(w, h)]
    parts.append(_text(300, 30, 14, "Figure 5: False-Accept Rate on Unsupported Cases", anchor="middle", bold=True))
    parts.append(_text(300, 50, 10, "Lower is better. KVRM = 0% across all domains.", anchor="middle", fill="#e53935"))

    for val in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = top_margin + chart_h - int(val / max_val * chart_h)
        parts.append(f"<line x1='{left_margin}' y1='{y}' x2='{w-20}' y2='{y}' stroke='#e0e0e0' stroke-width='0.5'/>")
        parts.append(_text(left_margin - 5, y + 3, 9, f"{val:.0%}", anchor="end", fill="#888"))

    colors = ["#1565c0", "#e53935", "#fb8c00", "#43a047"]
    labels = ["KVRM", "RF Direct", "GBM JSON", "RF Constrained"]

    for di, domain in enumerate(domains):
        gx = left_margin + di * (group_w + group_gap) + 20
        values = [kvrm[di], rf_dir[di], gbm_js[di], rf_con[di]]
        for bi, (val, color) in enumerate(zip(values, colors)):
            bx = gx + bi * (bar_w + gap)
            bh = max(1, int(val / max_val * chart_h)) if val > 0 else 1
            by = top_margin + chart_h - bh if val > 0 else top_margin + chart_h - 1
            parts.append(_rect(bx, by, bar_w, bh, color, rx=2))
            parts.append(_text(bx + bar_w/2, by - 4, 7, f"{val:.0%}", anchor="middle", fill="#333"))
        parts.append(_text(gx + group_w/2, top_margin + chart_h + 18, 11, domain, anchor="middle", bold=True))

    for li, (label, color) in enumerate(zip(labels, colors)):
        lx = 140 + li * 120
        parts.append(_rect(lx, h - 30, 10, 10, color))
        parts.append(_text(lx + 14, h - 21, 9, label, fill="#333"))
    parts.append(FOOTER)
    (OUT / "fig5_false_accept_rate.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 6: Registry evolution stale-label comparison
# ---------------------------------------------------------------------------
def fig6_registry_evolution():
    w, h = 600, 280
    domains = ["SRE", "SOC", "Drone"]
    # Stale label rates under incompatible mutation
    rf_dir = [0.375, 0.313, 0.188]
    gbm_js= [0.438, 0.313, 0.188]
    rf_con= [0.375, 0.313, 0.188]
    kvrm =  [0.000, 0.000, 0.000]

    bar_w = 28
    gap = 10
    group_w = 4 * bar_w + 3 * gap
    left_margin = 60
    top_margin = 70
    chart_h = 150
    max_val = 0.5
    group_gap = 90

    parts = [_header(w, h)]
    parts.append(_text(300, 25, 14, "Figure 6: Stale-Label Rate Under Incompatible Registry Mutation", anchor="middle", bold=True))
    parts.append(_text(300, 45, 10, "Lower is better. KVRM = 0% by construction.", anchor="middle", fill="#e53935"))

    for val in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]:
        y = top_margin + chart_h - int(val / max_val * chart_h)
        parts.append(f"<line x1='{left_margin}' y1='{y}' x2='{w-20}' y2='{y}' stroke='#e0e0e0' stroke-width='0.5'/>")
        parts.append(_text(left_margin - 5, y + 3, 9, f"{val:.0%}", anchor="end", fill="#888"))

    colors = ["#1565c0", "#e53935", "#fb8c00", "#43a047"]
    labels_list = ["KVRM", "RF Direct", "GBM JSON", "RF Constrained"]

    for di, domain in enumerate(domains):
        gx = left_margin + di * (group_w + group_gap) + 10
        values = [kvrm[di], rf_dir[di], gbm_js[di], rf_con[di]]
        for bi, (val, color) in enumerate(zip(values, colors)):
            bx = gx + bi * (bar_w + gap)
            bh = max(1, int(val / max_val * chart_h)) if val > 0 else 1
            by = top_margin + chart_h - bh if val > 0 else top_margin + chart_h - 1
            parts.append(_rect(bx, by, bar_w, bh, color, rx=2))
            parts.append(_text(bx + bar_w/2, by - 4, 8, f"{val:.1%}", anchor="middle", fill="#333"))
        parts.append(_text(gx + group_w/2, top_margin + chart_h + 18, 11, domain, anchor="middle", bold=True))

    for li, (label, color) in enumerate(zip(labels_list, colors)):
        lx = 140 + li * 120
        parts.append(_rect(lx, h - 25, 10, 10, color))
        parts.append(_text(lx + 14, h - 16, 9, label, fill="#333"))
    parts.append(FOOTER)
    (OUT / "fig6_registry_evolution.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 7: Architecture comparison — classifier pipeline vs KVRM stack
# ---------------------------------------------------------------------------
def fig7_architecture_comparison():
    w, h = 700, 280
    parts = [_header(w, h)]
    parts.append(_text(350, 25, 14, "Figure 7: Classifier Pipeline vs KVRM Systems Architecture", anchor="middle", bold=True))

    # Left side: classifier-only
    parts.append(_text(175, 55, 12, "Classifier-Only Pipeline", anchor="middle", bold=True, fill="#e53935"))
    clf_boxes = [
        (100, 75, 150, 35, "Input Features"),
        (100, 125, 150, 35, "Classifier Model"),
        (100, 175, 150, 35, "Direct Execution"),
    ]
    for bx, by, bw, bh, label in clf_boxes:
        parts.append(_rect(bx, by, bw, bh, "#ffebee", rx=4, stroke="#e53935", sw=1))
        parts.append(_text(bx + bw/2, by + bh/2 + 4, 10, label, anchor="middle", fill="#333"))
    # Arrows
    for (y1, y2) in [(110, 125), (160, 175)]:
        parts.append(f"<line x1='175' y1='{y1}' x2='175' y2='{y2}' stroke='#e53935' stroke-width='1.5' marker-end='url(#arrow2)'/>")
    # X marks (no protection)
    parts.append(_text(265, 135, 14, "No validation", fill="#e53935"))
    parts.append(_text(265, 155, 14, "No abstention", fill="#e53935"))
    parts.append(_text(265, 185, 14, "No audit trail", fill="#e53935"))

    # Right side: KVRM
    parts.append(_text(525, 55, 12, "KVRM Architecture", anchor="middle", bold=True, fill="#1565c0"))
    kvrm_boxes = [
        (450, 75, 150, 30, "Input Context"),
        (450, 118, 150, 30, "Selector (Rule/Retrieval)"),
        (450, 161, 30, 30, "Cal."),
        (487, 161, 113, 30, "Validator (Registry)"),
        (450, 204, 150, 30, "Executor / Safe Handoff"),
    ]
    for bx, by, bw, bh, label in kvrm_boxes:
        parts.append(_rect(bx, by, bw, bh, "#e3f2fd", rx=4, stroke="#1565c0", sw=1))
        parts.append(_text(bx + bw/2, by + bh/2 + 4, 9, label, anchor="middle", fill="#333"))
    for (y1, y2) in [(105, 118), (148, 161), (191, 204)]:
        parts.append(f"<line x1='525' y1='{y1}' x2='525' y2='{y2}' stroke='#1565c0' stroke-width='1.5' marker-end='url(#arrow2)'/>")
    # Checkmarks
    parts.append(_text(615, 128, 14, "Validated", fill="#2e7d32"))
    parts.append(_text(615, 148, 14, "Abstention-capable", fill="#2e7d32"))
    parts.append(_text(615, 171, 14, "Registry-checked", fill="#2e7d32"))
    parts.append(_text(615, 214, 14, "Audited", fill="#2e7d32"))
    # Registry reference
    parts.append(_rect(615, 70, 60, 40, "#fff3e0", rx=4, stroke="#ff9800", sw=1))
    parts.append(_text(645, 90, 9, "Action", anchor="middle", fill="#e65100"))
    parts.append(_text(645, 102, 9, "Registry", anchor="middle", fill="#e65100"))

    parts.append("<defs><marker id='arrow2' markerWidth='8' markerHeight='6' refX='8' refY='3' orient='auto'><polygon points='0 0, 8 3, 0 6' fill='#555'/></marker></defs>")
    parts.append(FOOTER)
    (OUT / "fig7_architecture_comparison.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 4 (current): canonical seven-domain suite summary
# ---------------------------------------------------------------------------
def fig4_canonical_suite():
    demos = _load_json("kvrm-demos/reports/demo_comparison.json")["demos"]
    order = [
        ("soc_hybrid", "SOC"),
        ("sre_hybrid", "SRE"),
        ("drone_hybrid", "Drone"),
        ("grid_hybrid", "Grid"),
        ("finance_hybrid", "Finance"),
        ("medical_hybrid", "Medical"),
        ("iam_hybrid", "IAM"),
        ("customer_support_hybrid", "Cust. Support"),
        ("content_moderation_hybrid", "Content Mod."),
        ("legal_hybrid", "Legal"),
        ("cicd_hybrid", "CI/CD"),
        ("insurance_hybrid", "Insurance"),
    ]
    w, h = 920, 78 + 34 * (len(order) + 1) + 60
    headers = [
        ("Domain", 80),
        ("Pack", 80),
        ("Supp.", 70),
        ("Unsupp.", 80),
        ("Semantic", 90),
        ("False Acc.", 90),
        ("Reject", 80),
        ("Invalid", 80),
        ("Cost", 70),
    ]
    left = 35
    top = 78
    row_h = 34
    table_w = sum(width for _, width in headers)

    parts = [_header(w, h)]
    parts.append(_text(w / 2, 28, 16, "Figure 4: Canonical Twelve-Domain Benchmark Suite", anchor="middle", bold=True))
    parts.append(
        _text(
            w / 2,
            50,
            11,
            "Hybrid KVRM is perfect on the live canonical packs across all twelve domains.",
            anchor="middle",
            fill="#666",
        )
    )
    parts.append(_rect(left, top, table_w, row_h, "#12304a", rx=6))
    x = left
    for label, width in headers:
        parts.append(_text(x + width / 2, top + 22, 10, label, anchor="middle", bold=True, fill="#ffffff"))
        x += width
    for index, (key, label) in enumerate(order):
        row = demos[key]
        y = top + row_h * (index + 1)
        fill = "#f7fafc" if index % 2 == 0 else "#edf3f8"
        parts.append(_rect(left, y, table_w, row_h, fill, rx=0))
        values = [
            label,
            str(row["total_cases"]),
            str(row["supported_cases"]),
            str(row["unsupported_cases"]),
            _fmt_rate(row["semantic_correctness_rate"]),
            _fmt_rate(row["false_accept_rate"]),
            _fmt_rate(row["unsupported_case_rejection_rate"]),
            _fmt_rate(row["invalid_output_rate"]),
            _fmt_rate(row["mean_decision_cost"]),
        ]
        x = left
        for col_index, ((_, width), value) in enumerate(zip(headers, values)):
            color = "#0b6e4f" if col_index >= 4 and value in {"1.0000", "0.0000"} else "#1a1a2e"
            parts.append(_text(x + width / 2, y + 22, 10, value, anchor="middle", fill=color))
            x += width
        parts.append(_line(left, y + row_h, left + table_w, y + row_h, stroke="#d7e0e8", sw=1))
    parts.append(_rect(left, top, table_w, row_h * (len(order) + 1), "none", rx=6, stroke="#b8c7d6", sw=1))
    parts.append(
        _text(
            w / 2,
            h - 18,
            10,
            "Source: kvrm-demos/reports/demo_comparison.json",
            anchor="middle",
            fill="#777",
        )
    )
    parts.append(FOOTER)
    (OUT / "fig4_canonical_suite.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 5 (current): support-gate stress
# ---------------------------------------------------------------------------
def fig5_support_gate_stress():
    w, h = 920, 360
    report = _load_json("kvrm-bench/results/support_gate_stress_report.json")["domains"]
    order = ["soc", "sre", "drone", "grid", "finance", "medical"]
    left_margin = 70
    top_margin = 80
    chart_h = 180
    bar_w = 24
    gap = 8
    group_gap = 36

    parts = [_header(w, h)]
    parts.append(_text(w / 2, 28, 16, "Figure 5: Support-Gate Stress", anchor="middle", bold=True))
    parts.append(
        _text(
            w / 2,
            50,
            11,
            "Injected support-incompatible 0.999 candidates into rule and retrieval stages.",
            anchor="middle",
            fill="#666",
        )
    )
    for val in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = top_margin + chart_h - int(val * chart_h)
        parts.append(_line(left_margin, y, w - 40, y, stroke="#e4e8ec", sw=1))
        parts.append(_text(left_margin - 8, y + 4, 9, f"{val:.2f}", anchor="end", fill="#888"))
    parts.append(_line(left_margin, top_margin, left_margin, top_margin + chart_h, stroke="#9aa7b3", sw=1))
    colors = {"gated": "#1565c0", "ungated": "#e53935"}
    legend_x = 250
    for index, (label, color) in enumerate([("Gated", colors["gated"]), ("Ungated", colors["ungated"])]):
        lx = legend_x + index * 140
        parts.append(_rect(lx, h - 34, 12, 12, color))
        parts.append(_text(lx + 18, h - 24, 10, label, fill="#333"))

    x = left_margin + 20
    for domain in order:
        gated = report[domain]["gated"]["metrics"]["semantic_correctness_rate"]
        ungated = report[domain]["ungated"]["metrics"]["semantic_correctness_rate"]
        cost_reduction = report[domain]["comparison"]["mean_decision_cost_reduction"]
        for bar_index, (value, variant) in enumerate([(gated, "gated"), (ungated, "ungated")]):
            bx = x + bar_index * (bar_w + gap)
            bh = max(2, int(value * chart_h))
            by = top_margin + chart_h - bh
            parts.append(_rect(bx, by, bar_w, bh, colors[variant], rx=3))
            parts.append(_text(bx + bar_w / 2, by - 5, 8, f"{value:.3f}", anchor="middle", fill="#333"))
        parts.append(_text(x + bar_w + gap / 2, top_margin + chart_h + 18, 10, domain.upper(), anchor="middle", bold=True))
        parts.append(
            _text(
                x + bar_w + gap / 2,
                top_margin + chart_h + 32,
                8,
                f"dCost={cost_reduction:.3f}",
                anchor="middle",
                fill="#666",
            )
        )
        x += 2 * bar_w + gap + group_gap
    parts.append(
        _text(
            w / 2,
            330,
            10,
            "Source: kvrm-bench/results/support_gate_stress_report.json",
            anchor="middle",
            fill="#777",
        )
    )
    parts.append(FOOTER)
    (OUT / "fig5_support_gate_stress.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 6 (current): fallback feasibility
# ---------------------------------------------------------------------------
def fig6_fallback_feasibility():
    w, h = 760, 320
    report = _load_json("kvrm-bench/results/fallback_feasibility_report.json")["domains"]
    order = [("sre", "SRE"), ("drone", "Drone")]
    left_margin = 90
    top_margin = 78
    chart_h = 160
    bar_w = 54
    gap = 22
    group_gap = 120
    colors = {"strict": "#1565c0", "legacy": "#e53935"}

    parts = [_header(w, h)]
    parts.append(_text(w / 2, 28, 16, "Figure 6: Fallback-Feasibility Runtime Check", anchor="middle", bold=True))
    parts.append(
        _text(
            w / 2,
            50,
            11,
            "Unsupported unsafe execution stays at zero only when fallback-tagged actions are validated at runtime.",
            anchor="middle",
            fill="#666",
        )
    )
    for val in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = top_margin + chart_h - int(val * chart_h)
        parts.append(_line(left_margin, y, w - 40, y, stroke="#e4e8ec", sw=1))
        parts.append(_text(left_margin - 8, y + 4, 9, f"{val:.2f}", anchor="end", fill="#888"))
    parts.append(_line(left_margin, top_margin, left_margin, top_margin + chart_h, stroke="#9aa7b3", sw=1))

    legend_x = 250
    for index, (label, color) in enumerate([("Strict runtime", colors["strict"]), ("Legacy bypass", colors["legacy"])]):
        lx = legend_x + index * 160
        parts.append(_rect(lx, h - 34, 12, 12, color))
        parts.append(_text(lx + 18, h - 24, 10, label, fill="#333"))

    x = left_margin + 70
    for domain_key, label in order:
        strict = report[domain_key]["variants"]["strict"]["feasibility_metrics"]["unsupported_unsafe_execution_rate"]
        legacy = report[domain_key]["variants"]["legacy_bypass"]["feasibility_metrics"]["unsupported_unsafe_execution_rate"]
        strict_cost = report[domain_key]["variants"]["strict"]["feasibility_metrics"]["mean_feasibility_cost"]
        legacy_cost = report[domain_key]["variants"]["legacy_bypass"]["feasibility_metrics"]["mean_feasibility_cost"]
        cases = report[domain_key]["generated_case_count"]
        for bar_index, (value, variant) in enumerate([(strict, "strict"), (legacy, "legacy")]):
            bx = x + bar_index * (bar_w + gap)
            bh = max(2, int(value * chart_h))
            by = top_margin + chart_h - bh
            parts.append(_rect(bx, by, bar_w, bh, colors[variant], rx=4))
            parts.append(_text(bx + bar_w / 2, by - 6, 9, f"{value:.3f}", anchor="middle", fill="#333"))
        cx = x + bar_w + gap / 2
        parts.append(_text(cx, top_margin + chart_h + 18, 11, label, anchor="middle", bold=True))
        parts.append(_text(cx, top_margin + chart_h + 32, 8, f"cases={cases}", anchor="middle", fill="#666"))
        parts.append(_text(cx, top_margin + chart_h + 44, 8, f"cost {strict_cost:.3f} vs {legacy_cost:.3f}", anchor="middle", fill="#666"))
        x += 2 * bar_w + gap + group_gap

    parts.append(
        _text(
            w / 2,
            295,
            10,
            "Source: kvrm-bench/results/fallback_feasibility_report.json",
            anchor="middle",
            fill="#777",
        )
    )
    parts.append(FOOTER)
    (OUT / "fig6_fallback_feasibility.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 7 (current): robustness-family summary
# ---------------------------------------------------------------------------
def fig7_robustness_families():
    w, h = 920, 340
    counterfactual = _load_json("kvrm-bench/results/counterfactual_boundary_report.json")
    temporal = _load_json("kvrm-bench/results/temporal_transition_report.json")
    coordination = _load_json("kvrm-bench/results/coordination_chain_report.json")
    cards = [
        (
            "Counterfactual",
            counterfactual["summary"],
            "strict wins: finance, drone",
            "drone gain: +0.1583 semantic, +0.0025 regret",
            "#e8f0fe",
            "#1565c0",
        ),
        (
            "Temporal",
            temporal["summary"],
            "strict wins: finance, SRE, drone",
            "drone gain: +0.0254 success, +0.0051 seq regret",
            "#e8f5e9",
            "#2e7d32",
        ),
        (
            "Coordination",
            coordination["summary"],
            "strict wins: finance, SRE, drone",
            "drone gain: +0.2828 success, +0.0566 chain regret",
            "#fff3e0",
            "#ef6c00",
        ),
    ]

    parts = [_header(w, h)]
    parts.append(_text(w / 2, 28, 16, "Figure 7: Robustness Family Summary", anchor="middle", bold=True))
    parts.append(
        _text(
            w / 2,
            50,
            11,
            "Hybrid KVRM has zero losses to the best non-hybrid baseline across all three live robustness families.",
            anchor="middle",
            fill="#666",
        )
    )
    card_w = 255
    card_h = 210
    start_x = 40
    gap = 32
    y = 82
    for index, (title, summary, wins_text, gain_text, fill, stroke) in enumerate(cards):
        x = start_x + index * (card_w + gap)
        parts.append(_rect(x, y, card_w, card_h, fill, rx=10, stroke=stroke, sw=1.5))
        parts.append(_text(x + card_w / 2, y + 28, 14, title, anchor="middle", bold=True, fill=stroke))
        parts.append(_text(x + 22, y + 65, 12, f"Wins:   {summary['hybrid_win_count']}", fill="#1a1a2e"))
        parts.append(_text(x + 22, y + 90, 12, f"Ties:   {summary['hybrid_tie_count']}", fill="#1a1a2e"))
        parts.append(_text(x + 22, y + 115, 12, f"Losses: {summary['hybrid_loss_count']}", fill="#1a1a2e"))
        parts.append(_line(x + 18, y + 132, x + card_w - 18, y + 132, stroke="#c9d4dd", sw=1))
        parts.append(_text(x + 22, y + 160, 10, wins_text, fill="#333"))
        parts.append(_text(x + 22, y + 185, 10, gain_text, fill="#333"))

    parts.append(
        _text(
            w / 2,
            322,
            10,
            "Sources: counterfactual_boundary_report.json, temporal_transition_report.json, coordination_chain_report.json",
            anchor="middle",
            fill="#777",
        )
    )
    parts.append(FOOTER)
    (OUT / "fig7_robustness_families.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 2: Registry lifecycle
# ---------------------------------------------------------------------------
def fig2_registry_lifecycle():
    w, h = 550, 200
    parts = [_header(w, h)]
    parts.append(_text(275, 25, 14, "Figure 2: Registry Lifecycle — Version, Hash, Validate, Evolve", anchor="middle", bold=True))
    steps = ["Define\nActions", "Version\n(v1.0.0)", "Hash\n(SHA256)", "Load &\nValidate", "Runtime\nReference"]
    for i, label in enumerate(steps):
        x = 30 + i * 105
        parts.append(_rect(x, 60, 80, 50, "#e8f5e9", rx=6, stroke="#43a047", sw=1))
        lines = label.split("\n")
        for li, line in enumerate(lines):
            parts.append(_text(x + 40, 80 + li * 14, 10, line, anchor="middle", fill="#333"))
        if i < len(steps) - 1:
            parts.append(f"<line x1='{x+80}' y1='85' x2='{x+105}' y2='85' stroke='#43a047' stroke-width='1.5' marker-end='url(#arrow3)'/>")
    # Evolution path
    parts.append(_rect(30, 140, 490, 35, "#fff3e0", rx=4, stroke="#ff9800", sw=1))
    parts.append(_text(275, 162, 10, "Evolution: append-only (safe) → reorder (safe) → incompatible rename (KVRM: 0% stale, classifier: 19-44%)", anchor="middle", fill="#bf360c"))
    parts.append("<defs><marker id='arrow3' markerWidth='8' markerHeight='6' refX='8' refY='3' orient='auto'><polygon points='0 0, 8 3, 0 6' fill='#43a047'/></marker></defs>")
    parts.append(FOOTER)
    (OUT / "fig2_registry_lifecycle.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Figure 3: Supported vs Unsupported routing flow
# ---------------------------------------------------------------------------
def fig3_supported_unsupported():
    w, h = 500, 250
    parts = [_header(w, h)]
    parts.append(_text(250, 25, 14, "Figure 3: Supported vs Unsupported Case Routing", anchor="middle", bold=True))

    # Input
    parts.append(_rect(190, 50, 120, 35, "#e8f0fe", rx=4, stroke="#1565c0", sw=1))
    parts.append(_text(250, 72, 10, "Decision Input", anchor="middle"))

    # Selector
    parts.append(_rect(190, 110, 120, 35, "#fce8e8", rx=4, stroke="#e53935", sw=1))
    parts.append(_text(250, 132, 10, "Selector", anchor="middle"))
    parts.append(f"<line x1='250' y1='85' x2='250' y2='110' stroke='#555' stroke-width='1.5' marker-end='url(#arrow4)'/>")

    # Supported path
    parts.append(_rect(60, 175, 130, 35, "#e8f5e9", rx=4, stroke="#43a047", sw=1))
    parts.append(_text(125, 197, 10, "Validate → Execute", anchor="middle"))
    parts.append(f"<line x1='200' y1='145' x2='125' y2='175' stroke='#43a047' stroke-width='1.5' marker-end='url(#arrow4)'/>")
    parts.append(_text(60, 168, 9, "Supported", fill="#2e7d32", bold=True))

    # Unsupported path
    parts.append(_rect(310, 175, 130, 35, "#ffebee", rx=4, stroke="#e53935", sw=1))
    parts.append(_text(375, 197, 10, "Abstain / Fallback", anchor="middle"))
    parts.append(f"<line x1='300' y1='145' x2='375' y2='175' stroke='#e53935' stroke-width='1.5' stroke-dasharray='4,3' marker-end='url(#arrow4)'/>")
    parts.append(_text(370, 168, 9, "Unsupported", fill="#e53935", bold=True))

    parts.append("<defs><marker id='arrow4' markerWidth='8' markerHeight='6' refX='8' refY='3' orient='auto'><polygon points='0 0, 8 3, 0 6' fill='#555'/></marker></defs>")
    parts.append(FOOTER)
    (OUT / "fig3_supported_vs_unsupported.svg").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    fig1_architecture()
    fig2_registry_lifecycle()
    fig3_supported_unsupported()
    fig4_per_domain_accuracy()
    fig5_false_accept_rate()
    fig6_registry_evolution()
    fig7_architecture_comparison()
    fig4_canonical_suite()
    fig5_support_gate_stress()
    fig6_fallback_feasibility()
    fig7_robustness_families()
    print(f"Generated SVG figures in {OUT}/")
