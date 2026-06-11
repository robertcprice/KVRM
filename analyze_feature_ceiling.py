from __future__ import annotations

import argparse
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--eval-filename",
        default="cases.jsonl",
        help="Evaluation filename under each domain data directory.",
    )
    parser.add_argument(
        "--benchmark-results",
        default=None,
        help="Optional benchmark results JSON. Defaults to the matching full benchmark artifact.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from kvrm_bench.ceiling import analyze_domain, render_markdown

    benchmark_results = args.benchmark_results
    if benchmark_results is None:
        benchmark_results = BASE_DIR / "kvrm-demos" / "reports" / "demo_comparison.json"

    domains = {
        "soc": {
            "registry": BASE_DIR / "kvrm-demos" / "soc-playbook-router" / "data" / "registry.json",
            "cases": BASE_DIR / "kvrm-demos" / "soc-playbook-router" / "data" / args.eval_filename,
        },
        "sre": {
            "registry": BASE_DIR / "kvrm-demos" / "sre-policy-router" / "data" / "registry.json",
            "cases": BASE_DIR / "kvrm-demos" / "sre-policy-router" / "data" / args.eval_filename,
        },
        "drone": {
            "registry": BASE_DIR / "kvrm-demos" / "drone-mission-router" / "data" / "registry.json",
            "cases": BASE_DIR / "kvrm-demos" / "drone-mission-router" / "data" / args.eval_filename,
        },
        "grid": {
            "registry": BASE_DIR / "kvrm-demos" / "grid-ops-router" / "data" / "registry.json",
            "cases": BASE_DIR / "kvrm-demos" / "grid-ops-router" / "data" / args.eval_filename,
        },
        "finance": {
            "registry": BASE_DIR / "kvrm-demos" / "finance-risk-router" / "data" / "registry.json",
            "cases": BASE_DIR / "kvrm-demos" / "finance-risk-router" / "data" / args.eval_filename,
        },
        "medical": {
            "registry": BASE_DIR / "kvrm-demos" / "medical-workflow-router" / "data" / "registry.json",
            "cases": BASE_DIR / "kvrm-demos" / "medical-workflow-router" / "data" / args.eval_filename,
        },
        "iam": {
            "registry": BASE_DIR / "kvrm-demos" / "iam-access-router" / "data" / "registry.json",
            "cases": BASE_DIR / "kvrm-demos" / "iam-access-router" / "data" / args.eval_filename,
        },
    }

    report = {
        "eval_filename": args.eval_filename,
        "benchmark_results": str(benchmark_results),
        "domains": [
            analyze_domain(
                domain_name=domain_name,
                registry_path=cfg["registry"],
                cases_path=cfg["cases"],
                benchmark_results_path=benchmark_results,
            )
            for domain_name, cfg in domains.items()
        ],
    }

    out_dir = BASE_DIR / "kvrm-bench" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.eval_filename.replace(".jsonl", "")
    json_path = out_dir / f"feature_ceiling_analysis_{stem}.json"
    md_path = out_dir / f"feature_ceiling_analysis_{stem}.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
