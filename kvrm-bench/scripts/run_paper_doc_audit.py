#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


from kvrm_bench.paper_doc_audit import build_paper_doc_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit KVRM paper docs for appendix-backed workflow consistency."
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
    payload = build_paper_doc_audit(REPO_ROOT, output_dir=args.output_dir)
    summary = {
        "all_checks_passed": payload["audit"]["all_checks_passed"],
        "check_count": len(payload["audit"]["checks"]),
        "passed_check_count": sum(1 for item in payload["audit"]["checks"] if item["passed"]),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"audit_json={payload['path']}")
    print(f"audit_md={payload['markdown_path']}")


if __name__ == "__main__":
    main()
