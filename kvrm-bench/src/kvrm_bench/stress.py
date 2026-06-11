from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_core.context_schema import build_registry_unsupported_predicate
from kvrm_core.registry import load_registry
from kvrm_core.runtime import KVRMRuntime
from kvrm_core.selectors import BaseSelector, EvidenceFusionHybridSelector
from kvrm_core.support import evaluate_support_spec
from kvrm_core.types import DecisionCandidate, DecisionInput, RegistrySpec
from kvrm_core.validation import DeterministicValidator

from .demo import DOMAIN_CONFIG
from .runner import BenchmarkRunner

STRESS_VARIANTS = ("gated", "ungated")
DEFAULT_STRESS_THRESHOLD = 0.60
DEFAULT_INJECTED_CONFIDENCE = 0.999
DEFAULT_RESULTS_DIR = "kvrm-bench/results"
DEFAULT_ARTIFACT_DIR_NAME = "support_gate_stress_artifacts"
DEFAULT_REPORT_JSON = "support_gate_stress_report.json"
DEFAULT_REPORT_MD = "support_gate_stress_report.md"


class SupportIncompatibleCandidateInjector(BaseSelector):
    def __init__(
        self,
        *,
        wrapped: BaseSelector,
        registry: RegistrySpec,
        confidence: float = DEFAULT_INJECTED_CONFIDENCE,
        name: str = "support_incompatible_candidate_injector",
    ):
        self.wrapped = wrapped
        self.registry = registry
        self.confidence = confidence
        self.name = name

    def select(self, decision_input: DecisionInput) -> list[DecisionCandidate]:
        injected_action_id, reason = self._pick_incompatible_action_id(decision_input)
        injected_candidate = DecisionCandidate(
            action_id=injected_action_id,
            confidence=self.confidence,
            source=self.name,
            evidence={
                "stress_injected": True,
                "stress_reason": reason,
                "stress_expected_action_id": decision_input.expected_action_id,
            },
        )
        return [injected_candidate, *self.wrapped.select(decision_input)]

    def _pick_incompatible_action_id(self, decision_input: DecisionInput) -> tuple[str, str]:
        for action in self.registry.actions:
            if "fallback" in action.tags:
                continue
            if decision_input.expected_action_id and action.action_id == decision_input.expected_action_id:
                continue
            supported, reason = evaluate_support_spec(action.support_spec, decision_input.features)
            if not supported:
                return (action.action_id, reason or "unsupported_action")
        return ("__stress_unknown_action__", "unknown_action")


def build_support_gate_stress_runtime(
    *,
    repo_root: str | Path,
    domain: str,
    variant: str,
    threshold: float = DEFAULT_STRESS_THRESHOLD,
    learned_model_path: str | Path | None = None,
    injected_confidence: float = DEFAULT_INJECTED_CONFIDENCE,
) -> KVRMRuntime:
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"unsupported stress domain: {domain}")
    if variant not in STRESS_VARIANTS:
        raise ValueError(f"unsupported stress variant: {variant}")

    repo_root = Path(repo_root)
    config = DOMAIN_CONFIG[domain]
    data_dir = repo_root / config["data_dir"]
    registry_path = data_dir / "registry.json"
    train_cases_path = data_dir / "train_cases.jsonl"
    registry = load_registry(registry_path)

    selectors_module = importlib.import_module(config["selectors_module"])
    executor_module = importlib.import_module(config["executor_module"])

    retrieval_selector = SupportIncompatibleCandidateInjector(
        wrapped=selectors_module.build_retrieval_selector(train_cases_path),
        registry=registry,
        confidence=injected_confidence,
        name=f"{domain}_{variant}_stress_retrieval_injector",
    )
    rule_selector = SupportIncompatibleCandidateInjector(
        wrapped=selectors_module.build_rule_selector(),
        registry=registry,
        confidence=injected_confidence,
        name=f"{domain}_{variant}_stress_rule_injector",
    )
    prototype_selector = selectors_module.build_prototype_selector(train_cases_path)

    semantic_builder = getattr(selectors_module, "build_semantic_selector", None)
    semantic_selector = semantic_builder(train_cases_path) if callable(semantic_builder) else None

    learned_selector = None
    learned_builder = getattr(selectors_module, "build_learned_selector", None)
    model_path = _resolve_learned_model_path(repo_root, domain, learned_model_path)
    if callable(learned_builder) and model_path is not None:
        learned_selector = learned_builder(train_cases_path, model_path)

    hybrid_selector = EvidenceFusionHybridSelector(
        retrieval_selector=retrieval_selector,
        rule_selector=rule_selector,
        prototype_selector=prototype_selector,
        registry=registry if variant == "gated" else None,
        semantic_selector=semantic_selector,
        learned_selector=learned_selector,
        unsupported_predicate=build_registry_unsupported_predicate(registry) if variant == "gated" else None,
        fallback_action_id=config["fallback_action_id"],
        name=f"{domain}_{variant}_support_gate_stress_selector",
    )
    return KVRMRuntime(
        registry=registry,
        selector=hybrid_selector,
        validator=DeterministicValidator(registry),
        executor=executor_module.build_executor(),
        threshold=threshold,
        fallback_action_id=config["fallback_action_id"],
    )


def run_support_gate_stress(
    *,
    repo_root: str | Path,
    domains: list[str] | tuple[str, ...] | None = None,
    threshold: float = DEFAULT_STRESS_THRESHOLD,
    learned_model_paths: dict[str, str | Path] | None = None,
    injected_confidence: float = DEFAULT_INJECTED_CONFIDENCE,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    active_domains = list(domains or DOMAIN_CONFIG.keys())
    results_dir = repo_root / DEFAULT_RESULTS_DIR if output_dir is None else Path(output_dir)
    artifact_dir = results_dir / DEFAULT_ARTIFACT_DIR_NAME
    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "injected_confidence": injected_confidence,
        "artifact_dir": str(artifact_dir),
        "domains": {},
    }

    for domain in active_domains:
        if domain not in DOMAIN_CONFIG:
            raise ValueError(f"unsupported stress domain: {domain}")
        config = DOMAIN_CONFIG[domain]
        data_dir = repo_root / config["data_dir"]
        registry_path = data_dir / "registry.json"
        cases_path = data_dir / "cases.jsonl"
        payload["domains"][domain] = {}

        for variant in STRESS_VARIANTS:
            runtime = build_support_gate_stress_runtime(
                repo_root=repo_root,
                domain=domain,
                variant=variant,
                threshold=threshold,
                learned_model_path=(learned_model_paths or {}).get(domain),
                injected_confidence=injected_confidence,
            )
            run_output_dir = artifact_dir / domain / variant
            run_name = f"{domain}_{variant}_support_gate_stress"
            result = BenchmarkRunner(runtime, registry_path, cases_path, run_output_dir).run(run_name=run_name)
            payload["domains"][domain][variant] = {
                "run_name": run_name,
                "output_dir": str(run_output_dir),
                "metrics": result["metrics"],
                "summary": result["summary"],
            }

        gated_metrics = payload["domains"][domain]["gated"]["metrics"]
        ungated_metrics = payload["domains"][domain]["ungated"]["metrics"]
        payload["domains"][domain]["comparison"] = {
            "semantic_correctness_gain": gated_metrics["semantic_correctness_rate"] - ungated_metrics["semantic_correctness_rate"],
            "fallback_rate_reduction": ungated_metrics["fallback_rate"] - gated_metrics["fallback_rate"],
            "mean_decision_cost_reduction": ungated_metrics["mean_decision_cost"] - gated_metrics["mean_decision_cost"],
            "supported_support_gate_rescue_gain": gated_metrics["supported_support_gate_rescue_rate"] - ungated_metrics["supported_support_gate_rescue_rate"],
        }

    report_paths = write_support_gate_stress_reports(payload, results_dir)
    payload["report_json"] = str(report_paths["json"])
    payload["report_md"] = str(report_paths["md"])
    return payload


def render_support_gate_stress_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Support-Gate Stress Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        (
            "Injected support-incompatible high-confidence candidates into the retrieval and rule stages "
            f"at confidence `{payload['injected_confidence']}`. The gated variant keeps registry-aware "
            "support filtering inside the hybrid selector; the ungated variant leaves invalid candidates "
            "to post-hoc runtime validation."
        ),
        "",
        (
            "This benchmark is intentionally architecture-focused: both variants keep deterministic runtime "
            "validation, so the gap shows up in supported-case correctness, fallback pressure, and decision "
            "cost rather than in false accepts."
        ),
        "",
        "| Domain | Gated Semantic | Ungated Semantic | Gain | Gated Cost | Ungated Cost | Cost Reduction | Gated Trigger | Rescue | False Accept |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for domain, domain_payload in payload["domains"].items():
        gated_metrics = domain_payload["gated"]["metrics"]
        ungated_metrics = domain_payload["ungated"]["metrics"]
        comparison = domain_payload["comparison"]
        lines.append(
            "| "
            f"{domain} | "
            f"{gated_metrics['semantic_correctness_rate']:.4f} | "
            f"{ungated_metrics['semantic_correctness_rate']:.4f} | "
            f"{comparison['semantic_correctness_gain']:.4f} | "
            f"{gated_metrics['mean_decision_cost']:.4f} | "
            f"{ungated_metrics['mean_decision_cost']:.4f} | "
            f"{comparison['mean_decision_cost_reduction']:.4f} | "
            f"{gated_metrics['support_gate_trigger_rate']:.4f} | "
            f"{gated_metrics['supported_support_gate_rescue_rate']:.4f} | "
            f"{gated_metrics['false_accept_rate']:.4f} |"
        )

    return "\n".join(lines) + "\n"


def write_support_gate_stress_reports(
    payload: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / DEFAULT_REPORT_JSON
    report_md = output_dir / DEFAULT_REPORT_MD
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(render_support_gate_stress_markdown(payload), encoding="utf-8")
    return {"json": report_json, "md": report_md}


def _resolve_learned_model_path(
    repo_root: Path,
    domain: str,
    learned_model_path: str | Path | None,
) -> Path | None:
    if learned_model_path is not None:
        path = Path(learned_model_path)
        return path if path.exists() else None
    default_path = repo_root / "kvrm-models" / f"{domain}_compact_selector_v1.joblib"
    return default_path if default_path.exists() else None
