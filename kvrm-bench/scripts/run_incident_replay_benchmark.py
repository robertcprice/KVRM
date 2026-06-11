#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

from kvrm_bench.demo import DOMAIN_CONFIG
from kvrm_bench.incident_replay import run_incident_replay_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the KVRM incident replay benchmark.")
    parser.add_argument(
        "--domains",
        nargs="+",
        choices=sorted(DOMAIN_CONFIG),
        default=sorted(DOMAIN_CONFIG),
        help="Domains to evaluate. Defaults to all active domains.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.60,
        help="Hybrid runtime threshold to use for the replay benchmark.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to kvrm-bench/results under the repo root.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_incident_replay_benchmark(
        repo_root=REPO_ROOT,
        domains=args.domains,
        threshold=args.threshold,
        output_dir=args.output_dir,
    )
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"report_json={payload['report_json']}")
    print(f"report_md={payload['report_md']}")
    print(f"episodes_json={payload['episodes_json']}")


if __name__ == "__main__":
    main()
