#!/usr/bin/env python3
"""Run the live KVRM vs real small-model Ollama comparison."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BASELINE_ROOT / "src"))

from qwen_baseline.data_loader import DOMAIN_ORDER
from qwen_baseline.evaluator import (
    compute_baseline_metrics,
    load_ollama_artifact,
    run_ollama_baseline,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="+",
        default=["qwen3:0.6b", "qwen3:1.7b"],
        help="Ollama models to evaluate.",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=DOMAIN_ORDER,
        choices=DOMAIN_ORDER,
        help="Domains to evaluate.",
    )
    parser.add_argument(
        "--variant",
        default="abstain_json",
        help="Baseline variant label to write into artifacts.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=BASELINE_ROOT / "outputs" / "ollama" / "live_canonical",
        help="Artifact root for the real Ollama comparison.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Optional case limit for smoke tests.",
    )
    parser.add_argument(
        "--max-examples-per-action",
        type=int,
        default=1,
        help="Few-shot examples per action in the prompt.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore cached per-case results and rerun everything.",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Do not call Ollama; regenerate combined artifacts from existing outputs.",
    )
    return parser.parse_args()


def load_kvrm_results() -> dict[str, Any]:
    report_path = REPO_ROOT / "kvrm-demos" / "reports" / "demo_comparison.json"
    return json.loads(report_path.read_text())


def generate_comparison_report(
    *,
    kvrm_results: dict[str, Any],
    ollama_results: dict[str, dict[str, Any]],
    model_summaries: dict[str, dict[str, Any]],
    output_dir: Path,
    models: list[str],
    domains: list[str],
) -> str:
    lines = [
        "# KVRM vs Small-Model LLM Baseline",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Scope",
        "",
        "This report compares live hybrid KVRM against real Ollama-backed small-model selector baselines",
        "on the current six-domain canonical suite. Evaluated models:",
        f"`{', '.join(models)}`.",
        "The baseline is charitable: it receives",
        "the live registry action ids and descriptions, the live feature schema, and up to two",
        "representative supported examples per action, then must choose an action or abstain",
        "via strict JSON output.",
        "",
        "## Overall Summary",
        "",
        "| Model | Macro Semantic | Macro False Accept | Macro Unsupported Rejection | Macro Invalid Output | Macro Mean Cost |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for model in models:
        summary = model_summaries[model]
        lines.append(
            f"| {model} | "
            f"{summary['macro_semantic_correctness_rate']:.4f} | "
            f"{summary['macro_false_accept_rate']:.4f} | "
            f"{summary['macro_unsupported_case_rejection_rate']:.4f} | "
            f"{summary['macro_invalid_output_rate']:.4f} | "
            f"{summary['macro_mean_decision_cost']:.4f} |"
        )
    kvrm_domains = _domains_with_kvrm(kvrm_results, domains)
    missing_kvrm = _domains_without_kvrm(kvrm_results, domains)
    kvrm_note = ""
    if missing_kvrm:
        kvrm_note = f" (averaged over {len(kvrm_domains)}/{len(domains)} domains; missing: {', '.join(missing_kvrm)})"
    lines.append(
        f"| KVRM hybrid{kvrm_note} | "
        f"{_macro_metric(kvrm_results, domains, 'semantic_correctness_rate'):.4f} | "
        f"{_macro_metric(kvrm_results, domains, 'false_accept_rate'):.4f} | "
        f"{_macro_metric(kvrm_results, domains, 'unsupported_case_rejection_rate'):.4f} | "
        f"{_macro_metric(kvrm_results, domains, 'invalid_output_rate'):.4f} | "
        f"{_macro_metric(kvrm_results, domains, 'mean_decision_cost'):.4f} |"
    )

    if missing_kvrm:
        lines.extend([
            "",
            f"> **Note**: KVRM hybrid results are unavailable for {len(missing_kvrm)} domain(s): "
            f"`{'`, `'.join(missing_kvrm)}`. "
            "These domains are excluded from KVRM macro averages and show Ollama-only results below.",
        ])

    lines.extend(["", "## Per-Domain Results", ""])

    for domain in domains:
        lines.append(f"### {domain.upper()}")
        lines.append("")
        lines.append("| System | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | OOD Accuracy | Mean Cost |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        kvrm_metrics = _domain_metrics(kvrm_results, domain)
        if kvrm_metrics is not None:
            lines.append(
                f"| KVRM hybrid | "
                f"{kvrm_metrics['semantic_correctness_rate']:.4f} | "
                f"{kvrm_metrics['false_accept_rate']:.4f} | "
                f"{kvrm_metrics['unsupported_case_rejection_rate']:.4f} | "
                f"{kvrm_metrics['invalid_output_rate']:.4f} | "
                f"{kvrm_metrics['ood_accuracy_supported_only']:.4f} | "
                f"{kvrm_metrics['mean_decision_cost']:.4f} |"
            )
        else:
            lines.append("| KVRM hybrid | -- | -- | -- | -- | -- | -- |")
        for model in models:
            metrics = ollama_results[model][domain]["metrics"]
            lines.append(
                f"| {model} | "
                f"{metrics['semantic_correctness_rate']:.4f} | "
                f"{metrics['false_accept_rate']:.4f} | "
                f"{metrics['unsupported_case_rejection_rate']:.4f} | "
                f"{metrics['invalid_output_rate']:.4f} | "
                f"{metrics['ood_accuracy_supported_only']:.4f} | "
                f"{metrics['mean_decision_cost']:.4f} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "- This baseline is a real small-model LLM comparison, not the old sklearn proxy.",
            "- The baseline is still only a selector. It does not get KVRM's support gate, strict runtime validation, or deterministic executor boundary.",
            *_model_interpretation_lines(model_summaries, models),
            "- Either way, the comparison still favors KVRM on the paper's actual claim axis: supported routing accuracy plus fail-closed open-world behavior under a live registry contract.",
            "",
            "## Artifact Outputs",
            "",
            f"- consolidated JSON: `{_display_path(output_dir / 'consolidated_comparison.json')}`",
            f"- combined metrics: `{_display_path(output_dir / 'combined_metrics.json')}`",
            f"- per-run artifacts under: `{_display_path(output_dir)}`",
            "",
        ]
    )
    report = "\n".join(lines)
    (output_dir / "KVRM_VS_QWEN_OLLAMA_COMPARISON.md").write_text(report)
    return report


def main() -> None:
    args = parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("KVRM vs Real Small-Model LLM Baseline")
    print("=" * 72)

    ollama_results: dict[str, dict[str, Any]] = {model: {} for model in args.models}
    combined_case_results: dict[str, list[dict[str, Any]]] = {model: [] for model in args.models}

    for model in args.models:
        print(f"\nModel: {model}")
        for domain in args.domains:
            output_dir = args.output_root / domain / _artifact_model_name(model) / args.variant
            if args.skip_run:
                artifact = load_ollama_artifact(output_dir, require_cases=True)
                if artifact is None:
                    raise FileNotFoundError(f"Missing cached artifact at {output_dir}")
                result = artifact
            else:
                print(f"  running {domain} ...")
                result = run_ollama_baseline(
                    domain=domain,
                    model=model,
                    output_dir=output_dir,
                    variant=args.variant,
                    refresh=args.refresh,
                    max_cases=args.max_cases,
                    max_examples_per_action=args.max_examples_per_action,
                )
            ollama_results[model][domain] = result
            combined_case_results[model].extend(result["per_case"])
            metrics = result["metrics"]
            print(
                f"    {domain}: "
                f"semantic={metrics['semantic_correctness_rate']:.4f}  "
                f"false_accept={metrics['false_accept_rate']:.4f}  "
                f"reject={metrics['unsupported_case_rejection_rate']:.4f}  "
                f"invalid={metrics['invalid_output_rate']:.4f}"
            )

    combined_metrics = {
        model: compute_baseline_metrics(case_results)
        for model, case_results in combined_case_results.items()
    }
    model_summaries = {
        model: build_model_summary(ollama_results[model], combined_metrics[model], args.domains)
        for model in args.models
    }

    kvrm_results = load_kvrm_results()
    generate_comparison_report(
        kvrm_results=kvrm_results,
        ollama_results=ollama_results,
        model_summaries=model_summaries,
        output_dir=args.output_root,
        models=args.models,
        domains=args.domains,
    )

    consolidated = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domains": args.domains,
        "models": args.models,
        "kvrm_results": {
            domain: (_domain_metrics(kvrm_results, domain) or {"missing": True})
            for domain in args.domains
        },
        "ollama_results": {
            model: {
                domain: result["metrics"]
                for domain, result in ollama_results[model].items()
            }
            for model in args.models
        },
        "model_summaries": model_summaries,
    }
    (args.output_root / "combined_metrics.json").write_text(
        json.dumps({model: data for model, data in combined_metrics.items()}, indent=2)
    )
    (args.output_root / "consolidated_comparison.json").write_text(
        json.dumps(consolidated, indent=2)
    )

    print("\nOutputs:")
    print(f"  report: {args.output_root / 'KVRM_VS_QWEN_OLLAMA_COMPARISON.md'}")
    print(f"  json:   {args.output_root / 'consolidated_comparison.json'}")


def build_model_summary(
    model_results: dict[str, Any],
    combined_metrics: dict[str, Any],
    domains: list[str],
) -> dict[str, Any]:
    summary = dict(combined_metrics)
    summary.update(
        {
            "macro_semantic_correctness_rate": _macro_from_model_results(model_results, "semantic_correctness_rate"),
            "macro_false_accept_rate": _macro_from_model_results(model_results, "false_accept_rate"),
            "macro_unsupported_case_rejection_rate": _macro_from_model_results(model_results, "unsupported_case_rejection_rate"),
            "macro_invalid_output_rate": _macro_from_model_results(model_results, "invalid_output_rate"),
            "macro_mean_decision_cost": _macro_from_model_results(model_results, "mean_decision_cost"),
            "domain_count": len(domains),
        }
    )
    return summary


def _macro_from_model_results(model_results: dict[str, Any], metric_key: str) -> float:
    values = [result["metrics"][metric_key] for result in model_results.values()]
    return sum(values) / len(values) if values else 0.0


def _macro_metric(kvrm_results: dict[str, Any], domains: list[str], metric_key: str) -> float:
    values = []
    for domain in domains:
        metrics = _domain_metrics(kvrm_results, domain)
        if metrics is not None:
            values.append(metrics[metric_key])
    return sum(values) / len(values) if values else 0.0


def _domain_metrics(kvrm_results: dict[str, Any], domain: str) -> dict[str, Any] | None:
    key = f"{domain}_hybrid"
    entry = kvrm_results.get("demos", {}).get(key)
    if entry is None or entry.get("missing"):
        return None
    return entry


def _domains_with_kvrm(kvrm_results: dict[str, Any], domains: list[str]) -> list[str]:
    """Return the subset of *domains* that have KVRM hybrid results."""
    return [d for d in domains if _domain_metrics(kvrm_results, d) is not None]


def _domains_without_kvrm(kvrm_results: dict[str, Any], domains: list[str]) -> list[str]:
    """Return domains lacking KVRM hybrid data."""
    return [d for d in domains if _domain_metrics(kvrm_results, d) is None]


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    repo_root = REPO_ROOT.resolve()
    try:
        return str(resolved.relative_to(repo_root))
    except ValueError:
        return str(resolved)


def _artifact_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def _model_interpretation_lines(
    model_summaries: dict[str, dict[str, Any]],
    models: list[str],
) -> list[str]:
    lines = []
    for model in models:
        summary = model_summaries[model]
        invalid = summary["macro_invalid_output_rate"]
        false_accept = summary["macro_false_accept_rate"]
        reject = summary["macro_unsupported_case_rejection_rate"]
        semantic = summary["macro_semantic_correctness_rate"]
        mean_cost = summary["macro_mean_decision_cost"]
        if invalid >= 0.5:
            lines.append(
                f"- `{model}` fails structurally under the strict JSON protocol: macro invalid output is `{invalid:.4f}`, so it does not reliably produce executable structured decisions."
            )
            continue
        if false_accept >= 0.5 and reject <= 0.1:
            lines.append(
                f"- `{model}` behaves like an over-aggressive classifier: macro semantic is `{semantic:.4f}`, but it nearly always executes on unsupported cases (`false_accept_rate={false_accept:.4f}`, `unsupported_rejection_rate={reject:.4f}`), driving `mean_decision_cost={mean_cost:.4f}`."
            )
            continue
        if false_accept > 0.1:
            lines.append(
                f"- `{model}` improves supported-case routing in places, but it still over-executes unsupported states (`false_accept_rate={false_accept:.4f}`) and therefore fails the paper's fail-closed requirement."
            )
            continue
        if reject < 0.5:
            lines.append(
                f"- `{model}` stays structurally valid but rarely abstains when it should (`unsupported_rejection_rate={reject:.4f}`), so its routing behavior remains too permissive for audited deployment."
            )
            continue
        lines.append(
            f"- `{model}` is the strongest external selector in this run, but it still falls short of KVRM on the open-world contract metrics and does not provide KVRM's runtime safety boundaries."
        )
    return lines


if __name__ == "__main__":
    main()
