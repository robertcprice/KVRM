from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class HybridMetricsSummary:
    semantic_correctness_rate: float | None = None
    false_accept_rate: float | None = None
    unsupported_case_rejection_rate: float | None = None
    abstention_rate: float | None = None
    mean_decision_cost: float | None = None


@dataclass
class TrainingSummary:
    selector_only_accuracy: float | None = None
    selector_only_false_accept_rate: float | None = None
    hybrid_augmented_accuracy: float | None = None
    hybrid_augmented_false_accept_rate: float | None = None
    selector_only_mean_decision_cost: float | None = None
    hybrid_augmented_mean_decision_cost: float | None = None


@dataclass
class DomainDashboardSummary:
    domain: str
    demo_hybrid: HybridMetricsSummary = field(default_factory=HybridMetricsSummary)
    training: TrainingSummary = field(default_factory=TrainingSummary)


@dataclass
class DashboardSnapshot:
    repo_root: str
    domains: list[DomainDashboardSummary]
    available_files: dict[str, str | None]


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _demo_hybrid_metrics(payload: dict | None, domain: str) -> HybridMetricsSummary:
    if not payload:
        return HybridMetricsSummary()
    metrics = (payload.get("demos", {}).get(f"{domain}_hybrid") or {})
    if metrics.get("missing"):
        return HybridMetricsSummary()
    return HybridMetricsSummary(
        semantic_correctness_rate=metrics.get("semantic_correctness_rate"),
        false_accept_rate=metrics.get("false_accept_rate"),
        unsupported_case_rejection_rate=metrics.get("unsupported_case_rejection_rate"),
        abstention_rate=metrics.get("abstention_rate"),
        mean_decision_cost=metrics.get("mean_decision_cost"),
    )


def _training_metrics(payload: dict | None, domain: str) -> TrainingSummary:
    if not payload or payload.get("domain") != domain:
        return TrainingSummary()
    selector_only = payload.get("selector_only", {})
    hybrid_augmented = payload.get("hybrid_augmented", {})
    return TrainingSummary(
        selector_only_accuracy=selector_only.get("semantic_correctness_rate"),
        selector_only_false_accept_rate=selector_only.get("false_accept_rate"),
        hybrid_augmented_accuracy=hybrid_augmented.get("semantic_correctness_rate"),
        hybrid_augmented_false_accept_rate=hybrid_augmented.get("false_accept_rate"),
        selector_only_mean_decision_cost=selector_only.get("mean_decision_cost"),
        hybrid_augmented_mean_decision_cost=hybrid_augmented.get("mean_decision_cost"),
    )


def load_dashboard_snapshot(repo_root: str | Path) -> DashboardSnapshot:
    root = Path(repo_root)
    results_dir = root / "kvrm-bench" / "results"
    demo_comparison_path = root / "kvrm-demos" / "reports" / "demo_comparison.json"

    demo_comparison = _load_json(demo_comparison_path)
    training_reports = {
        payload.get("domain"): payload
        for payload in (
            _load_json(path)
            for path in sorted(results_dir.glob("*compact_training_report*.json"))
        )
        if payload and payload.get("domain")
    }

    domains = [
        DomainDashboardSummary(
            domain=domain,
            demo_hybrid=_demo_hybrid_metrics(demo_comparison, domain),
            training=_training_metrics(training_reports.get(domain), domain),
        )
        for domain in ("soc", "sre", "drone", "grid", "finance", "medical", "iam")
    ]

    return DashboardSnapshot(
        repo_root=str(root),
        domains=domains,
        available_files={
            "demo_comparison": str(demo_comparison_path) if demo_comparison_path.exists() else None,
            "training_reports": str(results_dir) if training_reports else None,
            "legacy_results": str(results_dir / "legacy") if (results_dir / "legacy").exists() else None,
        },
    )
