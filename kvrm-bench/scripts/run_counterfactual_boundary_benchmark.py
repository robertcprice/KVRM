from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from kvrm_bench.counterfactual import (
    render_counterfactual_boundary_markdown,
    run_counterfactual_boundary_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the KVRM counterfactual boundary benchmark.")
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
        help="Regenerate cached counterfactual case packs even when matching artifacts already exist.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_counterfactual_boundary_benchmark(
        repo_root=ROOT,
        domains=args.domains,
        threshold=args.threshold,
        output_dir=args.output_dir,
        refresh_case_cache=args.refresh_cases,
    )
    print(render_counterfactual_boundary_markdown(payload), end="")


if __name__ == "__main__":
    main()
