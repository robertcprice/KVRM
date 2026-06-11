from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from kvrm_bench.coordination import (
    render_coordination_chain_markdown,
    run_coordination_chain_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the KVRM coordination chain benchmark.")
    parser.add_argument(
        "--domains",
        nargs="*",
        default=None,
        help="Optional subset of domains to run.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.60,
        help="Hybrid calibration threshold used during runtime evaluation.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "kvrm-bench" / "results"),
        help="Directory for report files.",
    )
    parser.add_argument(
        "--refresh-cases",
        action="store_true",
        help="Regenerate cached counterfactual case packs before building coordination chains.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_coordination_chain_benchmark(
        repo_root=ROOT,
        domains=args.domains,
        threshold=args.threshold,
        output_dir=args.output_dir,
        refresh_counterfactual_cases=args.refresh_cases,
    )
    print(render_coordination_chain_markdown(payload), end="")


if __name__ == "__main__":
    main()
