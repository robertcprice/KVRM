#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


from kvrm_bench.demo import write_draft_export_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the KVRM draft export manifest and markdown audit index."
    )
    return parser.parse_args()


def main() -> None:
    parse_args()
    payload = write_draft_export_manifest(REPO_ROOT)
    print(json.dumps(payload["manifest"]["domain_counts"], indent=2, sort_keys=True))
    print(f"manifest_json={payload['path']}")
    print(f"manifest_md={payload['markdown_path']}")
    print(f"export_count={payload['export_count']}")


if __name__ == "__main__":
    main()
