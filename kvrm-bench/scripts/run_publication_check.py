#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


from kvrm_bench.publication_check import build_publication_check


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the KVRM publication bundle plus publication-critical verification checks."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to kvrm-bench/results/publication_bundle.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_publication_check(REPO_ROOT, output_dir=args.output_dir)
    summary = {
        "all_checks_passed": payload["check"]["all_checks_passed"],
        "passed_check_count": payload["check"]["passed_check_count"],
        "failed_check_count": payload["check"]["failed_check_count"],
        "portal_refreshed": payload["check"]["portal_refreshed"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"publication_check_json={payload['path']}")
    print(f"publication_check_md={payload['markdown_path']}")


if __name__ == "__main__":
    main()
