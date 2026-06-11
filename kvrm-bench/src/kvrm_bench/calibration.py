"""ECE calibration analysis across all KVRM domains and selector strategies.

Computes Expected Calibration Error, Brier scores, and reliability diagram
data for every (domain, strategy) pair.  Writes JSON + markdown reports.

Also provides post-hoc recalibration sweep for the hybrid selector using
temperature scaling, Platt scaling, and isotonic regression with LOOCV.
"""

from __future__ import annotations

import importlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from kvrm_core.calibration import IsotonicScaler, PlattScaler, TemperatureScaler
from kvrm_core.logging import decision_result_to_case_result
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.types import DecisionInput
from kvrm_core.validation import DeterministicValidator

from .demo import DOMAIN_CONFIG, STRATEGY_ORDER

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class BinData:
    """One bin in a reliability diagram."""
    bin_lower: float
    bin_upper: float
    bin_midpoint: float
    count: int
    mean_confidence: float
    mean_accuracy: float
    gap: float  # |accuracy - confidence|


@dataclass
class CalibrationResult:
    """Per-(domain, strategy) calibration payload."""
    domain: str
    strategy: str
    n_cases: int
    n_confident: int
    ece: float
    mce: float  # Maximum Calibration Error
    brier: float
    overconfidence_ratio: float  # fraction of bins where confidence > accuracy
    bins: list[BinData] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Core calibration maths
# ---------------------------------------------------------------------------

def compute_ece_detailed(
    case_results: list[dict],
    n_bins: int = 10,
) -> tuple[float, float, list[BinData]]:
    """Compute ECE, MCE, and per-bin reliability data.

    Returns (ece, mce, bins).
    """
    confident = [r for r in case_results if r.get("confidence") is not None]
    if not confident:
        return 0.0, 0.0, []

    n = len(confident)
    bin_size = 1.0 / n_bins
    bins: list[BinData] = []
    ece = 0.0
    mce = 0.0

    for i in range(n_bins):
        lo = i * bin_size
        hi = (i + 1) * bin_size
        members = [r for r in confident if lo <= float(r["confidence"]) < hi]
        if not members:
            bins.append(BinData(
                bin_lower=lo, bin_upper=hi,
                bin_midpoint=(lo + hi) / 2,
                count=0,
                mean_confidence=0.0,
                mean_accuracy=0.0,
                gap=0.0,
            ))
            continue

        acc = sum(1 for r in members if bool(r.get("correct", False))) / len(members)
        conf = sum(float(r["confidence"]) for r in members) / len(members)
        gap = abs(acc - conf)
        weight = len(members) / n
        ece += weight * gap
        mce = max(mce, gap)

        bins.append(BinData(
            bin_lower=lo, bin_upper=hi,
            bin_midpoint=(lo + hi) / 2,
            count=len(members),
            mean_confidence=conf,
            mean_accuracy=acc,
            gap=gap,
        ))

    return ece, mce, bins


def compute_brier_score(case_results: list[dict]) -> float:
    """Brier score = mean( (confidence - correct)^2 ).

    Lower is better.  Perfect = 0.0, worst = 1.0.
    """
    confident = [r for r in case_results if r.get("confidence") is not None]
    if not confident:
        return 0.0
    total = 0.0
    for r in confident:
        c = float(r["confidence"])
        y = 1.0 if bool(r.get("correct", False)) else 0.0
        total += (c - y) ** 2
    return total / len(confident)


def overconfidence_ratio(bins: list[BinData]) -> float:
    """Fraction of non-empty bins where confidence > accuracy."""
    populated = [b for b in bins if b.count > 0]
    if not populated:
        return 0.0
    over = sum(1 for b in populated if b.mean_confidence > b.mean_accuracy)
    return over / len(populated)


# ---------------------------------------------------------------------------
# Domain / strategy runner
# ---------------------------------------------------------------------------

def _load_eval_cases(data_dir: Path) -> list[DecisionInput]:
    """Load cases.jsonl as DecisionInput objects."""
    cases_path = data_dir / "cases.jsonl"
    rows: list[DecisionInput] = []
    with cases_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            rows.append(DecisionInput(
                case_id=payload["case_id"],
                features=payload["input_features"],
                expected_action_id=payload.get("expected_action_id"),
                supported=payload.get("supported", True),
                ood=payload.get("ood", False),
            ))
    return rows


def _build_selector(
    selectors_module: Any,
    strategy: str,
    train_cases_path: Path,
    learned_model_path: str | None,
) -> Any:
    """Build the selector for a given strategy, mirroring demo._build_selector."""
    if strategy == "rule":
        return selectors_module.build_rule_selector()
    if strategy == "retrieval":
        return selectors_module.build_retrieval_selector(train_cases_path)
    if strategy == "prototype":
        return selectors_module.build_prototype_selector(train_cases_path)
    if strategy == "semantic":
        return selectors_module.build_semantic_selector(train_cases_path)
    if strategy == "learned":
        if not learned_model_path or not Path(learned_model_path).exists():
            return None
        return selectors_module.build_learned_selector(train_cases_path, learned_model_path)
    if strategy == "hybrid":
        return selectors_module.build_hybrid_selector(
            train_cases_path,
            learned_model_path=learned_model_path,
        )
    raise ValueError(f"unsupported strategy: {strategy}")


def _run_strategy_on_domain(
    repo_root: Path,
    domain: str,
    strategy: str,
    threshold: float = 0.60,
    n_bins: int = 10,
) -> CalibrationResult:
    """Execute *strategy* on all eval cases for *domain* and compute calibration."""
    config = DOMAIN_CONFIG[domain]
    data_dir = repo_root / config["data_dir"]
    registry_path = data_dir / "registry.json"
    train_cases_path = data_dir / "train_cases.jsonl"
    learned_model_path = str(
        repo_root / "kvrm-models" / f"{domain}_compact_selector_v1.joblib"
    )

    try:
        registry = load_registry(registry_path)
        validator = DeterministicValidator(registry)
        selectors_mod = importlib.import_module(config["selectors_module"])
        executor_mod = importlib.import_module(config["executor_module"])
        executor = executor_mod.build_executor()

        selector = _build_selector(
            selectors_mod, strategy, train_cases_path, learned_model_path,
        )
        if selector is None:
            return CalibrationResult(
                domain=domain, strategy=strategy,
                n_cases=0, n_confident=0,
                ece=0.0, mce=0.0, brier=0.0,
                overconfidence_ratio=0.0,
                error="selector_unavailable",
            )

        runtime = KVRMRuntime(
            registry=registry,
            selector=selector,
            validator=validator,
            executor=executor,
            threshold=threshold,
            fallback_action_id=config["fallback_action_id"],
        )

        cases = _load_eval_cases(data_dir)
        case_results: list[dict] = []
        for case in cases:
            result = runtime.decide_and_execute(case)
            case_results.append(
                decision_result_to_case_result(
                    result, case.expected_action_id, case.supported, case.ood,
                )
            )

        ece, mce, bins = compute_ece_detailed(case_results, n_bins=n_bins)
        brier = compute_brier_score(case_results)
        oc_ratio = overconfidence_ratio(bins)
        n_confident = sum(1 for r in case_results if r.get("confidence") is not None)

        return CalibrationResult(
            domain=domain,
            strategy=strategy,
            n_cases=len(case_results),
            n_confident=n_confident,
            ece=ece,
            mce=mce,
            brier=brier,
            overconfidence_ratio=oc_ratio,
            bins=bins,
        )

    except Exception as exc:
        return CalibrationResult(
            domain=domain, strategy=strategy,
            n_cases=0, n_confident=0,
            ece=0.0, mce=0.0, brier=0.0,
            overconfidence_ratio=0.0,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Full cross-domain sweep
# ---------------------------------------------------------------------------

def run_calibration_sweep(
    repo_root: Path,
    *,
    domains: list[str] | None = None,
    strategies: tuple[str, ...] = STRATEGY_ORDER,
    threshold: float = 0.60,
    n_bins: int = 10,
) -> list[CalibrationResult]:
    """Run calibration analysis for every (domain, strategy) pair."""
    target_domains = domains or list(DOMAIN_CONFIG.keys())
    results: list[CalibrationResult] = []

    for domain in target_domains:
        for strategy in strategies:
            print(f"  [{domain:>20s}] {strategy:>10s} ...", end=" ", flush=True)
            t0 = time.monotonic()
            cr = _run_strategy_on_domain(
                repo_root, domain, strategy,
                threshold=threshold, n_bins=n_bins,
            )
            elapsed = time.monotonic() - t0
            status = f"ECE={cr.ece:.4f}" if not cr.error else f"ERROR: {cr.error}"
            print(f"{status}  ({elapsed:.1f}s)")
            results.append(cr)

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _result_to_dict(cr: CalibrationResult) -> dict[str, Any]:
    return {
        "domain": cr.domain,
        "strategy": cr.strategy,
        "n_cases": cr.n_cases,
        "n_confident": cr.n_confident,
        "ece": round(cr.ece, 6),
        "mce": round(cr.mce, 6),
        "brier": round(cr.brier, 6),
        "overconfidence_ratio": round(cr.overconfidence_ratio, 4),
        "error": cr.error,
        "bins": [
            {
                "bin_lower": round(b.bin_lower, 2),
                "bin_upper": round(b.bin_upper, 2),
                "count": b.count,
                "mean_confidence": round(b.mean_confidence, 4),
                "mean_accuracy": round(b.mean_accuracy, 4),
                "gap": round(b.gap, 4),
            }
            for b in cr.bins
        ],
    }


def _best_strategy_per_domain(results: list[CalibrationResult]) -> dict[str, str]:
    """For each domain, which strategy has lowest ECE (excluding errors)?"""
    by_domain: dict[str, list[CalibrationResult]] = {}
    for r in results:
        if r.error:
            continue
        by_domain.setdefault(r.domain, []).append(r)

    best: dict[str, str] = {}
    for domain, crs in by_domain.items():
        winner = min(crs, key=lambda c: c.ece)
        best[domain] = winner.strategy
    return best


def _strategy_mean_ece(results: list[CalibrationResult]) -> dict[str, float]:
    """Mean ECE per strategy across all domains."""
    totals: dict[str, list[float]] = {}
    for r in results:
        if r.error:
            continue
        totals.setdefault(r.strategy, []).append(r.ece)
    return {
        s: sum(vals) / len(vals) if vals else 0.0
        for s, vals in totals.items()
    }


def _strategy_mean_brier(results: list[CalibrationResult]) -> dict[str, float]:
    """Mean Brier score per strategy across all domains."""
    totals: dict[str, list[float]] = {}
    for r in results:
        if r.error:
            continue
        totals.setdefault(r.strategy, []).append(r.brier)
    return {
        s: sum(vals) / len(vals) if vals else 0.0
        for s, vals in totals.items()
    }


def write_json_report(results: list[CalibrationResult], out_path: Path) -> None:
    """Write full JSON report."""
    best_per_domain = _best_strategy_per_domain(results)
    mean_ece = _strategy_mean_ece(results)
    mean_brier = _strategy_mean_brier(results)
    global_best = min(mean_ece, key=mean_ece.get) if mean_ece else "n/a"

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_domains": len(set(r.domain for r in results)),
        "n_strategies": len(set(r.strategy for r in results)),
        "total_evaluations": len(results),
        "global_best_calibrated_strategy": global_best,
        "mean_ece_by_strategy": {s: round(v, 6) for s, v in sorted(mean_ece.items(), key=lambda x: x[1])},
        "mean_brier_by_strategy": {s: round(v, 6) for s, v in sorted(mean_brier.items(), key=lambda x: x[1])},
        "best_strategy_per_domain": best_per_domain,
        "per_strategy_domain_results": [_result_to_dict(r) for r in results],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def render_markdown_report(results: list[CalibrationResult]) -> str:
    """Produce a publication-grade markdown summary."""
    best_per_domain = _best_strategy_per_domain(results)
    mean_ece = _strategy_mean_ece(results)
    mean_brier = _strategy_mean_brier(results)
    global_best = min(mean_ece, key=mean_ece.get) if mean_ece else "n/a"

    lines: list[str] = []
    lines.append("# KVRM Calibration Analysis (ECE)")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Domains**: {len(set(r.domain for r in results))}")
    lines.append(f"**Strategies**: {', '.join(STRATEGY_ORDER)}")
    lines.append(f"**Bins**: 10 equal-width")
    lines.append(f"**Threshold**: 0.60")
    lines.append("")

    # --- Cross-domain summary table ---
    lines.append("## Cross-Domain Strategy Ranking")
    lines.append("")
    lines.append("| Rank | Strategy | Mean ECE | Mean Brier | Interpretation |")
    lines.append("|------|----------|----------|------------|----------------|")
    sorted_strategies = sorted(mean_ece.items(), key=lambda x: x[1])
    for rank, (strat, ece_val) in enumerate(sorted_strategies, 1):
        brier_val = mean_brier.get(strat, 0.0)
        if ece_val < 0.05:
            interp = "Excellent"
        elif ece_val < 0.10:
            interp = "Good"
        elif ece_val < 0.20:
            interp = "Moderate"
        else:
            interp = "Poor"
        lines.append(f"| {rank} | {strat} | {ece_val:.4f} | {brier_val:.4f} | {interp} |")
    lines.append("")
    lines.append(f"**Best overall calibration**: `{global_best}`")
    lines.append("")

    # --- Per-domain heatmap table ---
    lines.append("## ECE Heatmap (Domain x Strategy)")
    lines.append("")
    strat_list = list(STRATEGY_ORDER)
    header = "| Domain | " + " | ".join(strat_list) + " | Best |"
    sep = "|--------|" + "|".join(["-------"] * len(strat_list)) + "|------|"
    lines.append(header)
    lines.append(sep)

    domains_seen = list(dict.fromkeys(r.domain for r in results))
    for domain in domains_seen:
        cells = []
        for strat in strat_list:
            match = [r for r in results if r.domain == domain and r.strategy == strat]
            if match and not match[0].error:
                val = match[0].ece
                cells.append(f"{val:.4f}")
            elif match and match[0].error:
                cells.append("--")
            else:
                cells.append("--")
        best = best_per_domain.get(domain, "n/a")
        lines.append(f"| {domain} | " + " | ".join(cells) + f" | {best} |")
    lines.append("")

    # --- Brier score heatmap ---
    lines.append("## Brier Score Heatmap (Domain x Strategy)")
    lines.append("")
    lines.append(header.replace("ECE", "Brier"))
    lines.append(sep)
    for domain in domains_seen:
        cells = []
        for strat in strat_list:
            match = [r for r in results if r.domain == domain and r.strategy == strat]
            if match and not match[0].error:
                val = match[0].brier
                cells.append(f"{val:.4f}")
            elif match and match[0].error:
                cells.append("--")
            else:
                cells.append("--")
        # best brier for domain
        domain_results = [r for r in results if r.domain == domain and not r.error]
        best_brier_strat = min(domain_results, key=lambda r: r.brier).strategy if domain_results else "n/a"
        lines.append(f"| {domain} | " + " | ".join(cells) + f" | {best_brier_strat} |")
    lines.append("")

    # --- Overconfidence analysis ---
    lines.append("## Overconfidence Analysis")
    lines.append("")
    lines.append("Fraction of populated bins where `confidence > accuracy` (1.0 = always overconfident):")
    lines.append("")
    lines.append("| Domain | " + " | ".join(strat_list) + " |")
    lines.append("|--------|" + "|".join(["-------"] * len(strat_list)) + "|")
    for domain in domains_seen:
        cells = []
        for strat in strat_list:
            match = [r for r in results if r.domain == domain and r.strategy == strat]
            if match and not match[0].error:
                cells.append(f"{match[0].overconfidence_ratio:.2f}")
            else:
                cells.append("--")
        lines.append(f"| {domain} | " + " | ".join(cells) + " |")
    lines.append("")

    # --- Reliability diagrams per domain ---
    lines.append("## Reliability Diagrams (Per Domain, Best Strategy)")
    lines.append("")
    for domain in domains_seen:
        best_strat = best_per_domain.get(domain, "n/a")
        match = [r for r in results if r.domain == domain and r.strategy == best_strat]
        if not match or match[0].error:
            continue
        cr = match[0]
        lines.append(f"### {domain} ({cr.strategy}, ECE={cr.ece:.4f})")
        lines.append("")
        lines.append("| Bin | Count | Mean Conf | Mean Acc | Gap |")
        lines.append("|-----|-------|-----------|----------|-----|")
        for b in cr.bins:
            if b.count == 0:
                lines.append(f"| [{b.bin_lower:.1f},{b.bin_upper:.1f}) | 0 | -- | -- | -- |")
            else:
                lines.append(
                    f"| [{b.bin_lower:.1f},{b.bin_upper:.1f}) "
                    f"| {b.count} "
                    f"| {b.mean_confidence:.4f} "
                    f"| {b.mean_accuracy:.4f} "
                    f"| {b.gap:.4f} |"
                )
        lines.append("")

    # --- Key findings ---
    lines.append("## Key Findings")
    lines.append("")

    # Check for systematic overconfidence
    all_oc = [r.overconfidence_ratio for r in results if not r.error]
    mean_oc = sum(all_oc) / len(all_oc) if all_oc else 0.0
    if mean_oc > 0.6:
        lines.append(f"- **Systematic overconfidence detected**: mean overconfidence ratio = {mean_oc:.2f}")
    elif mean_oc < 0.4:
        lines.append(f"- **Slight underconfidence tendency**: mean overconfidence ratio = {mean_oc:.2f}")
    else:
        lines.append(f"- **Balanced calibration**: mean overconfidence ratio = {mean_oc:.2f}")

    # Strategy consistency
    best_counts: dict[str, int] = {}
    for s in best_per_domain.values():
        best_counts[s] = best_counts.get(s, 0) + 1
    dominant = max(best_counts, key=best_counts.get) if best_counts else "n/a"
    lines.append(f"- **Most frequently best-calibrated**: `{dominant}` ({best_counts.get(dominant, 0)}/{len(best_per_domain)} domains)")

    # ECE range
    valid_eces = [r.ece for r in results if not r.error]
    if valid_eces:
        lines.append(f"- **ECE range**: [{min(valid_eces):.4f}, {max(valid_eces):.4f}]")
        lines.append(f"- **Mean ECE across all evaluations**: {sum(valid_eces) / len(valid_eces):.4f}")

    # Brier range
    valid_briers = [r.brier for r in results if not r.error]
    if valid_briers:
        lines.append(f"- **Brier range**: [{min(valid_briers):.4f}, {max(valid_briers):.4f}]")

    lines.append("")
    return "\n".join(lines)


def write_markdown_report(results: list[CalibrationResult], out_path: Path) -> None:
    """Write markdown report."""
    md = render_markdown_report(results)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")


# ---------------------------------------------------------------------------
# Post-hoc recalibration sweep (LOOCV)
# ---------------------------------------------------------------------------

@dataclass
class RecalibrationResult:
    """Per-(domain, scaler) recalibration outcome."""
    domain: str
    scaler_name: str
    n_cases: int
    pre_ece: float
    post_ece: float
    pre_brier: float
    post_brier: float
    ece_delta: float        # post - pre (negative = improvement)
    brier_delta: float      # post - pre (negative = improvement)
    ece_improvement_pct: float  # 100 * (pre - post) / pre
    brier_improvement_pct: float


def _collect_hybrid_predictions(
    repo_root: Path,
    domain: str,
    threshold: float = 0.60,
) -> list[dict]:
    """Run the hybrid selector on a domain and collect case results."""
    config = DOMAIN_CONFIG[domain]
    data_dir = repo_root / config["data_dir"]
    registry_path = data_dir / "registry.json"
    train_cases_path = data_dir / "train_cases.jsonl"
    learned_model_path = str(
        repo_root / "kvrm-models" / f"{domain}_compact_selector_v1.joblib"
    )

    registry = load_registry(registry_path)
    validator = DeterministicValidator(registry)
    selectors_mod = importlib.import_module(config["selectors_module"])
    executor_mod = importlib.import_module(config["executor_module"])
    executor = executor_mod.build_executor()

    selector = selectors_mod.build_hybrid_selector(
        train_cases_path, learned_model_path=learned_model_path,
    )

    runtime = KVRMRuntime(
        registry=registry,
        selector=selector,
        validator=validator,
        executor=executor,
        threshold=threshold,
        fallback_action_id=config["fallback_action_id"],
    )

    cases = _load_eval_cases(data_dir)
    case_results: list[dict] = []
    for case in cases:
        result = runtime.decide_and_execute(case)
        case_results.append(
            decision_result_to_case_result(
                result, case.expected_action_id, case.supported, case.ood,
            )
        )
    return case_results


def _loocv_calibrate(
    confidences: np.ndarray,
    labels: np.ndarray,
    scaler_factory: type,
) -> np.ndarray:
    """Leave-one-out cross-validation for a post-hoc scaler.

    For each sample i, fit the scaler on all samples except i, then
    predict the calibrated confidence for sample i.  Returns an array
    of calibrated confidences, one per sample.
    """
    n = len(confidences)
    calibrated = np.zeros(n, dtype=np.float64)

    for i in range(n):
        train_mask = np.ones(n, dtype=bool)
        train_mask[i] = False
        train_confs = confidences[train_mask]
        train_labels = labels[train_mask]

        scaler = scaler_factory()
        scaler.fit(train_confs.tolist(), train_labels.tolist())
        calibrated[i] = scaler.transform(float(confidences[i]))

    return calibrated


def _ece_from_arrays(confidences: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Compute ECE directly from numpy arrays."""
    n = len(confidences)
    if n == 0:
        return 0.0

    bin_size = 1.0 / n_bins
    ece = 0.0
    for b in range(n_bins):
        lo = b * bin_size
        hi = (b + 1) * bin_size
        mask = (confidences >= lo) & (confidences < hi)
        count = int(mask.sum())
        if count == 0:
            continue
        acc = float(labels[mask].mean())
        conf = float(confidences[mask].mean())
        ece += (count / n) * abs(acc - conf)
    return ece


def _brier_from_arrays(confidences: np.ndarray, labels: np.ndarray) -> float:
    """Compute Brier score directly from numpy arrays."""
    if len(confidences) == 0:
        return 0.0
    return float(np.mean((confidences - labels) ** 2))


def run_recalibration_sweep(
    repo_root: Path,
    *,
    domains: list[str] | None = None,
    threshold: float = 0.60,
    n_bins: int = 10,
) -> list[RecalibrationResult]:
    """Run post-hoc recalibration on hybrid selector across all domains.

    For each domain:
    1. Collect hybrid confidence scores and correctness labels.
    2. Fit TemperatureScaler, PlattScaler, IsotonicScaler via LOOCV.
    3. Measure pre- and post-calibration ECE and Brier.

    Returns a list of RecalibrationResult, one per (domain, scaler).
    """
    target_domains = domains or list(DOMAIN_CONFIG.keys())

    scaler_configs = [
        ("temperature", TemperatureScaler),
        ("platt", PlattScaler),
        ("isotonic", IsotonicScaler),
    ]

    results: list[RecalibrationResult] = []

    for domain in target_domains:
        print(f"  [{domain:>20s}] collecting hybrid predictions ...", end=" ", flush=True)
        t0 = time.monotonic()

        try:
            case_results = _collect_hybrid_predictions(repo_root, domain, threshold)
        except Exception as exc:
            print(f"ERROR: {exc}")
            continue

        # Extract confidence/label arrays
        confident = [r for r in case_results if r.get("confidence") is not None]
        if not confident:
            print(f"no confident cases")
            continue

        confs = np.array([float(r["confidence"]) for r in confident], dtype=np.float64)
        labels = np.array(
            [1.0 if bool(r.get("correct", False)) else 0.0 for r in confident],
            dtype=np.float64,
        )

        pre_ece = _ece_from_arrays(confs, labels, n_bins=n_bins)
        pre_brier = _brier_from_arrays(confs, labels)

        elapsed_collect = time.monotonic() - t0
        print(f"n={len(confs)}, pre-ECE={pre_ece:.4f}  ({elapsed_collect:.1f}s)")

        for scaler_name, scaler_cls in scaler_configs:
            t1 = time.monotonic()
            calibrated = _loocv_calibrate(confs, labels, scaler_cls)
            post_ece = _ece_from_arrays(calibrated, labels, n_bins=n_bins)
            post_brier = _brier_from_arrays(calibrated, labels)

            ece_delta = post_ece - pre_ece
            brier_delta = post_brier - pre_brier
            ece_improv = 100.0 * (pre_ece - post_ece) / pre_ece if pre_ece > 0 else 0.0
            brier_improv = 100.0 * (pre_brier - post_brier) / pre_brier if pre_brier > 0 else 0.0

            elapsed_scaler = time.monotonic() - t1
            tag = "+" if ece_delta > 0 else ""
            print(
                f"    {scaler_name:>12s}: post-ECE={post_ece:.4f} "
                f"({tag}{ece_improv:+.1f}%), "
                f"post-Brier={post_brier:.4f}  ({elapsed_scaler:.1f}s)"
            )

            results.append(RecalibrationResult(
                domain=domain,
                scaler_name=scaler_name,
                n_cases=len(confs),
                pre_ece=pre_ece,
                post_ece=post_ece,
                pre_brier=pre_brier,
                post_brier=post_brier,
                ece_delta=ece_delta,
                brier_delta=brier_delta,
                ece_improvement_pct=ece_improv,
                brier_improvement_pct=brier_improv,
            ))

    return results


def write_recalibration_json_report(
    results: list[RecalibrationResult],
    out_path: Path,
) -> None:
    """Write recalibration sweep results as JSON."""
    # Aggregate by scaler
    scaler_agg: dict[str, list[RecalibrationResult]] = {}
    for r in results:
        scaler_agg.setdefault(r.scaler_name, []).append(r)

    scaler_summary = {}
    for name, items in scaler_agg.items():
        scaler_summary[name] = {
            "mean_pre_ece": round(np.mean([r.pre_ece for r in items]), 6),
            "mean_post_ece": round(np.mean([r.post_ece for r in items]), 6),
            "mean_ece_improvement_pct": round(np.mean([r.ece_improvement_pct for r in items]), 2),
            "mean_pre_brier": round(np.mean([r.pre_brier for r in items]), 6),
            "mean_post_brier": round(np.mean([r.post_brier for r in items]), 6),
            "mean_brier_improvement_pct": round(np.mean([r.brier_improvement_pct for r in items]), 2),
        }

    best_scaler = min(scaler_summary, key=lambda s: scaler_summary[s]["mean_post_ece"]) if scaler_summary else "n/a"

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": "Post-hoc recalibration of hybrid selector using LOOCV",
        "strategy": "hybrid",
        "scalers": ["temperature", "platt", "isotonic"],
        "cv_method": "LOOCV",
        "n_domains": len(set(r.domain for r in results)),
        "best_scaler": best_scaler,
        "scaler_summary": scaler_summary,
        "per_domain_results": [
            {
                "domain": r.domain,
                "scaler": r.scaler_name,
                "n_cases": r.n_cases,
                "pre_ece": round(r.pre_ece, 6),
                "post_ece": round(r.post_ece, 6),
                "ece_delta": round(r.ece_delta, 6),
                "ece_improvement_pct": round(r.ece_improvement_pct, 2),
                "pre_brier": round(r.pre_brier, 6),
                "post_brier": round(r.post_brier, 6),
                "brier_delta": round(r.brier_delta, 6),
                "brier_improvement_pct": round(r.brier_improvement_pct, 2),
            }
            for r in results
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def render_recalibration_markdown(results: list[RecalibrationResult]) -> str:
    """Generate a markdown report for the recalibration sweep."""
    lines: list[str] = []
    lines.append("# KVRM Hybrid Selector Post-Hoc Recalibration Report")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("**Strategy**: hybrid")
    lines.append("**CV Method**: Leave-One-Out Cross-Validation (LOOCV)")
    lines.append(f"**Scalers**: temperature, platt, isotonic")
    lines.append(f"**Domains**: {len(set(r.domain for r in results))}")
    lines.append("")

    # Aggregate by scaler
    scaler_agg: dict[str, list[RecalibrationResult]] = {}
    for r in results:
        scaler_agg.setdefault(r.scaler_name, []).append(r)

    # --- Cross-domain summary ---
    lines.append("## Cross-Domain Scaler Ranking")
    lines.append("")
    lines.append("| Scaler | Mean Pre-ECE | Mean Post-ECE | ECE Improvement | Mean Pre-Brier | Mean Post-Brier | Brier Improvement |")
    lines.append("|--------|-------------|--------------|-----------------|---------------|----------------|-------------------|")

    scaler_rows = []
    for name, items in scaler_agg.items():
        mean_pre_ece = float(np.mean([r.pre_ece for r in items]))
        mean_post_ece = float(np.mean([r.post_ece for r in items]))
        mean_ece_improv = float(np.mean([r.ece_improvement_pct for r in items]))
        mean_pre_brier = float(np.mean([r.pre_brier for r in items]))
        mean_post_brier = float(np.mean([r.post_brier for r in items]))
        mean_brier_improv = float(np.mean([r.brier_improvement_pct for r in items]))
        scaler_rows.append((name, mean_pre_ece, mean_post_ece, mean_ece_improv, mean_pre_brier, mean_post_brier, mean_brier_improv))

    scaler_rows.sort(key=lambda x: x[2])  # sort by post-ECE ascending
    for name, pre_ece, post_ece, ece_imp, pre_b, post_b, b_imp in scaler_rows:
        lines.append(
            f"| {name} | {pre_ece:.4f} | {post_ece:.4f} | {ece_imp:+.1f}% "
            f"| {pre_b:.4f} | {post_b:.4f} | {b_imp:+.1f}% |"
        )
    lines.append("")

    if scaler_rows:
        best = scaler_rows[0]
        lines.append(f"**Best scaler**: `{best[0]}` (mean post-ECE = {best[2]:.4f}, improvement = {best[3]:+.1f}%)")
        lines.append("")

    # --- Per-domain detail ---
    lines.append("## Per-Domain Results")
    lines.append("")
    lines.append("| Domain | Scaler | n | Pre-ECE | Post-ECE | ECE Delta | ECE Improvement | Pre-Brier | Post-Brier | Brier Delta |")
    lines.append("|--------|--------|---|---------|----------|-----------|-----------------|-----------|------------|-------------|")

    domains_seen = list(dict.fromkeys(r.domain for r in results))
    for domain in domains_seen:
        domain_results = [r for r in results if r.domain == domain]
        for r in domain_results:
            tag = "+" if r.ece_delta > 0 else ""
            lines.append(
                f"| {r.domain} | {r.scaler_name} | {r.n_cases} "
                f"| {r.pre_ece:.4f} | {r.post_ece:.4f} "
                f"| {tag}{r.ece_delta:.4f} | {r.ece_improvement_pct:+.1f}% "
                f"| {r.pre_brier:.4f} | {r.post_brier:.4f} "
                f"| {r.brier_delta:+.4f} |"
            )
    lines.append("")

    # --- Key findings ---
    lines.append("## Key Findings")
    lines.append("")

    all_ece_improvs = [r.ece_improvement_pct for r in results]
    if all_ece_improvs:
        lines.append(f"- **ECE improvement range**: [{min(all_ece_improvs):+.1f}%, {max(all_ece_improvs):+.1f}%]")
        lines.append(f"- **Mean ECE improvement**: {np.mean(all_ece_improvs):+.1f}%")

    all_brier_improvs = [r.brier_improvement_pct for r in results]
    if all_brier_improvs:
        lines.append(f"- **Mean Brier improvement**: {np.mean(all_brier_improvs):+.1f}%")

    # Check how many domains each scaler wins
    for name, items in scaler_agg.items():
        improved_domains = sum(1 for r in items if r.ece_improvement_pct > 0)
        lines.append(f"- **{name}**: improved ECE in {improved_domains}/{len(items)} domains")

    lines.append("")
    return "\n".join(lines)


def write_recalibration_markdown(results: list[RecalibrationResult], out_path: Path) -> None:
    """Write recalibration markdown report."""
    md = render_recalibration_markdown(results)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run full calibration sweep and write reports."""
    repo_root = Path(__file__).resolve().parents[3]  # kvrm-bench/src/kvrm_bench -> KVRM

    out_dir = repo_root / "kvrm-bench-results" / "calibration"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("KVRM Calibration Analysis (ECE)")
    print("=" * 72)
    print()

    results = run_calibration_sweep(repo_root)

    json_path = out_dir / "calibration_report.json"
    md_path = out_dir / "calibration_report.md"

    write_json_report(results, json_path)
    write_markdown_report(results, md_path)

    print()
    print("=" * 72)
    print("REPORTS WRITTEN")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")
    print("=" * 72)
    print()

    # Print summary to stdout
    md = render_markdown_report(results)
    print(md)


if __name__ == "__main__":
    main()
