from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from kvrm_bench.temporal import (
    render_temporal_transition_markdown,
    run_temporal_transition_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the KVRM temporal transition benchmark.")
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
        help="Regenerate cached counterfactual case packs before building temporal transitions.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_temporal_transition_benchmark(
        repo_root=ROOT,
        domains=args.domains,
        threshold=args.threshold,
        output_dir=args.output_dir,
        refresh_counterfactual_cases=args.refresh_cases,
    )
    print(render_temporal_transition_markdown(payload), end="")


if __name__ == "__main__":
    main()
