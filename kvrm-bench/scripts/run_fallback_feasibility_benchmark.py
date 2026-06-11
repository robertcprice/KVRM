from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from kvrm_bench.fallback_feasibility import (
    render_fallback_feasibility_markdown,
    run_fallback_feasibility_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the KVRM fallback-feasibility benchmark.")
    parser.add_argument(
        "--domains",
        nargs="*",
        default=None,
        help="Optional subset of domains to run. Defaults to SRE and drone.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.60,
        help="Hybrid calibration threshold.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "kvrm-bench" / "results"),
        help="Directory for benchmark report files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_fallback_feasibility_benchmark(
        repo_root=ROOT,
        domains=args.domains,
        threshold=args.threshold,
        output_dir=args.output_dir,
    )
    print(render_fallback_feasibility_markdown(payload), end="")


if __name__ == "__main__":
    main()
