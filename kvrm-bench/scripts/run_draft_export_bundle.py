#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


from kvrm_bench.demo import (
    DOMAIN_CONFIG,
    DRAFT_FILE_NAMES,
    DRAFT_FILTERS,
    DRAFT_SORTS,
    export_draft_case_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a deterministic KVRM draft-audit bundle and refresh its manifest."
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        choices=sorted(DOMAIN_CONFIG),
        default=sorted(DOMAIN_CONFIG),
        help="Domains to include in the bundle. Defaults to all active domains.",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        choices=sorted(DRAFT_FILE_NAMES),
        default=list(DRAFT_FILE_NAMES),
        help="Draft targets to export. Defaults to review/train/eval.",
    )
    parser.add_argument(
        "--filters",
        nargs="+",
        choices=DRAFT_FILTERS,
        default=["all"],
        help="Draft queue filters to export. Defaults to the full queue.",
    )
    parser.add_argument(
        "--sorts",
        nargs="+",
        choices=DRAFT_SORTS,
        default=["queue"],
        help="Draft queue sort/grouping modes to export. Defaults to queue order.",
    )
    parser.add_argument(
        "--include-groups",
        action="store_true",
        help="Also export one packet per visible group for grouped sort modes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = export_draft_case_bundle(
        repo_root=REPO_ROOT,
        domains=args.domains,
        targets=args.targets,
        draft_filters=args.filters,
        draft_sorts=args.sorts,
        include_group_exports=args.include_groups,
    )
    summary = {
        "domains": payload["domains"],
        "targets": payload["targets"],
        "draft_filters": payload["draft_filters"],
        "draft_sorts": payload["draft_sorts"],
        "include_group_exports": payload["include_group_exports"],
        "export_count": payload["export_count"],
        "slice_export_count": payload["slice_export_count"],
        "group_export_count": payload["group_export_count"],
        "selection_count_total": payload["selection_count_total"],
        "skipped_count": payload["skipped_count"],
        "manifest_export_count": payload["manifest_export_count"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"manifest_json={payload['manifest_path']}")
    print(f"manifest_md={payload['manifest_markdown_path']}")


if __name__ == "__main__":
    main()
