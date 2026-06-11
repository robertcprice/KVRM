from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from kvrm_bench.stress import render_support_gate_stress_markdown, run_support_gate_stress


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the KVRM support-gate stress benchmark.")
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
        help="Hybrid calibration threshold.",
    )
    parser.add_argument(
        "--injected-confidence",
        type=float,
        default=0.999,
        help="Confidence assigned to injected invalid candidates.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "kvrm-bench" / "results"),
        help="Directory for stress artifacts and report files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_support_gate_stress(
        repo_root=ROOT,
        domains=args.domains,
        threshold=args.threshold,
        injected_confidence=args.injected_confidence,
        output_dir=args.output_dir,
    )
    print(render_support_gate_stress_markdown(payload), end="")


if __name__ == "__main__":
    main()
