from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from kvrm_bench.ambiguity import (
    render_ambiguity_regret_markdown,
    run_ambiguity_regret_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the KVRM ambiguity/regret benchmark.")
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
        help="Hybrid calibration threshold used when building the review frontier.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "kvrm-bench" / "results"),
        help="Directory for report files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_ambiguity_regret_benchmark(
        repo_root=ROOT,
        domains=args.domains,
        threshold=args.threshold,
        output_dir=args.output_dir,
    )
    print(render_ambiguity_regret_markdown(payload), end="")


if __name__ == "__main__":
    main()
