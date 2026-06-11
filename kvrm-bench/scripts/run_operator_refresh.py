from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


from kvrm_bench.operator_pipeline import build_operator_refresh_plan, run_operator_refresh_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the KVRM operator refresh pipeline.")
    parser.add_argument("--domains", nargs="*", help="Optional focused domains to refresh.")
    parser.add_argument(
        "--stale-only",
        action="store_true",
        help="Refresh only domains whose compact-model artifacts are stale or missing.",
    )
    parser.add_argument(
        "--skip-benchmark",
        action="store_true",
        help="Train compact models without rerunning domain benchmark scripts.",
    )
    parser.add_argument(
        "--skip-report-refresh",
        action="store_true",
        help="Skip kvrm-demos/compare_demos.py after the domain steps complete.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    steps = build_operator_refresh_plan(
        REPO_ROOT,
        domains=args.domains,
        stale_only=args.stale_only,
        include_benchmark=not args.skip_benchmark,
        include_report_refresh=not args.skip_report_refresh,
    )
    if not steps:
        print("no operator refresh steps to run")
        return
    run_operator_refresh_plan(REPO_ROOT, steps)


if __name__ == "__main__":
    main()
