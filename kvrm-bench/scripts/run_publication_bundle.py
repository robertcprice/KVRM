#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


from kvrm_bench.publication_bundle import build_publication_bundle
from kvrm_bench.paper_doc_audit import build_paper_doc_audit
from kvrm_bench.publication_manuscript_packet import build_publication_manuscript_packet
from kvrm_bench.publication_paper_assets import (
    build_publication_paper_appendix,
    build_publication_paper_assets,
)
from kvrm_bench.publication_submission_export import build_publication_submission_export_matrix
from kvrm_bench.publication_portal import build_publication_portal
from kvrm_bench.publication_summary import build_publication_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic KVRM publication bundle under kvrm-bench/results."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional bundle output directory. Defaults to kvrm-bench/results/publication_bundle.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_publication_bundle(REPO_ROOT, output_dir=args.output_dir)
    summary_payload = build_publication_summary(REPO_ROOT, output_dir=payload["output_dir"])
    paper_assets_payload = build_publication_paper_assets(
        REPO_ROOT,
        output_dir=payload["output_dir"],
        summary=summary_payload["summary"],
    )
    appendix_payload = build_publication_paper_appendix(
        REPO_ROOT,
        output_dir=payload["output_dir"],
        docs_output_path=REPO_ROOT / "docs" / "papers" / "KVRM_PUBLICATION_APPENDIX.md",
        summary=summary_payload["summary"],
        paper_assets=paper_assets_payload["assets"],
    )
    paper_doc_audit_payload = build_paper_doc_audit(REPO_ROOT, output_dir=payload["output_dir"])
    manuscript_packet_payload = build_publication_manuscript_packet(REPO_ROOT, output_dir=payload["output_dir"])
    submission_export_payload = build_publication_submission_export_matrix(REPO_ROOT, output_dir=payload["output_dir"])
    portal_payload = build_publication_portal(
        REPO_ROOT,
        output_dir=payload["output_dir"],
        manifest=payload["manifest"],
        summary=summary_payload["summary"],
        paper_assets=paper_assets_payload["assets"],
        paper_doc_audit=paper_doc_audit_payload["audit"],
        appendix_path=appendix_payload["path"],
        docs_appendix_path=appendix_payload["docs_path"],
        manuscript_packet_path=manuscript_packet_payload["readme_path"],
        submission_export_path=submission_export_payload["readme_path"],
    )
    summary = {
        "bundle_root": payload["manifest"]["bundle_root"],
        "artifact_root": payload["manifest"]["artifact_root"],
        "artifact_count": payload["manifest"]["artifact_count"],
        "copied_artifact_count": payload["manifest"]["copied_artifact_count"],
        "missing_artifact_count": payload["manifest"]["missing_artifact_count"],
        "copied_bytes": payload["manifest"]["copied_bytes"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"manifest_json={payload['manifest_path']}")
    print(f"manifest_md={payload['markdown_path']}")
    print(f"summary_json={summary_payload['path']}")
    print(f"summary_md={summary_payload['markdown_path']}")
    print(f"paper_assets_json={paper_assets_payload['path']}")
    print(f"paper_tables_md={paper_assets_payload['tables_path']}")
    print(f"figure_captions_md={paper_assets_payload['captions_path']}")
    print(f"paper_appendix_md={appendix_payload['path']}")
    if appendix_payload["docs_path"] is not None:
        print(f"paper_appendix_docs_md={appendix_payload['docs_path']}")
    print(f"paper_doc_audit_json={paper_doc_audit_payload['path']}")
    print(f"paper_doc_audit_md={paper_doc_audit_payload['markdown_path']}")
    print(f"manuscript_packet_json={manuscript_packet_payload['path']}")
    print(f"manuscript_packet_md={manuscript_packet_payload['markdown_path']}")
    print(f"manuscript_packet_readme_md={manuscript_packet_payload['readme_path']}")
    print(f"submission_export_json={submission_export_payload['path']}")
    print(f"submission_export_md={submission_export_payload['markdown_path']}")
    print(f"submission_export_readme_md={submission_export_payload['readme_path']}")
    print(f"publication_portal_json={portal_payload['path']}")
    print(f"publication_portal_md={portal_payload['markdown_path']}")
    print(f"publication_portal_readme_md={portal_payload['readme_path']}")


if __name__ == "__main__":
    main()
