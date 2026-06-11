#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


from kvrm_bench.publication_submission_export import (
    build_publication_submission_export,
    build_publication_submission_export_matrix,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build pandoc/LaTeX submission exports from the KVRM manuscript packet."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional publication bundle output directory. Defaults to kvrm-bench/results/publication_bundle.",
    )
    parser.add_argument(
        "--profile",
        default="review-anonymous",
        choices=("review-anonymous", "working-manuscript"),
        help="Submission export profile. Defaults to review-anonymous.",
    )
    parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Build both submission profiles side by side under submission/<profile>/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.all_profiles:
        payload = build_publication_submission_export_matrix(
            REPO_ROOT,
            output_dir=args.output_dir,
        )
        summary = {
            "all_exports_succeeded": payload["export"]["all_exports_succeeded"],
            "all_pdf_authors_blank": payload["export"]["all_pdf_authors_blank"],
            "profile_count": payload["export"]["profile_count"],
        }
    else:
        payload = build_publication_submission_export(
            REPO_ROOT,
            output_dir=args.output_dir,
            profile=args.profile,
        )
        summary = {
            "all_exports_succeeded": payload["export"]["all_exports_succeeded"],
            "generated_file_count": len(payload["export"]["generated_files"]),
            "profile": payload["export"]["profile"],
        }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"submission_export_json={payload['path']}")
    print(f"submission_export_md={payload['markdown_path']}")
    print(f"submission_export_readme_md={payload['readme_path']}")


if __name__ == "__main__":
    main()
