from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PUBLICATION_PORTAL_JSON = "publication_portal.json"
DEFAULT_PUBLICATION_PORTAL_MD = "publication_portal.md"
DEFAULT_PUBLICATION_PORTAL_README = "README.md"


def build_publication_portal(
    repo_root: str | Path,
    *,
    output_dir: str | Path | None = None,
    manifest: dict[str, Any],
    summary: dict[str, Any],
    paper_assets: dict[str, Any],
    paper_doc_audit: dict[str, Any],
    appendix_path: str,
    docs_appendix_path: str | None = None,
    manuscript_packet_path: str | None = None,
    submission_export_path: str | None = None,
    publication_check: dict[str, Any] | None = None,
    publication_check_path: str | None = None,
) -> dict[str, Any]:
    repo_root_path = Path(repo_root)
    output_root = (
        Path(output_dir)
        if output_dir is not None
        else repo_root_path / "kvrm-bench" / "results" / "publication_bundle"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    canonical = summary["sections"]["canonical_suite"]
    audit_checks = paper_doc_audit["checks"]
    failed_checks = [item["name"] for item in audit_checks if not item["passed"]]
    publication_check_failed = []
    if publication_check is not None:
        publication_check_failed = [
            str(item["name"])
            for item in publication_check.get("checks", [])
            if not item.get("passed")
        ]

    portal = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_root": _display_path(output_root, repo_root_path),
        "status": {
            "artifact_count": manifest["artifact_count"],
            "copied_artifact_count": manifest["copied_artifact_count"],
            "missing_artifact_count": manifest["missing_artifact_count"],
            "paper_doc_all_checks_passed": paper_doc_audit["all_checks_passed"],
            "paper_doc_check_count": len(audit_checks),
            "paper_doc_failed_checks": failed_checks,
            "publication_check_all_checks_passed": (
                publication_check["all_checks_passed"] if publication_check is not None else None
            ),
            "publication_check_check_count": (
                len(publication_check.get("checks", [])) if publication_check is not None else None
            ),
            "publication_check_failed_checks": publication_check_failed,
            "canonical_domain_count": canonical["domain_count"],
            "canonical_total_case_count": canonical["total_case_count"],
        },
        "bundle_files": [
            {"label": "bundle manifest", "path": "manifest.md"},
            {"label": "publication summary", "path": "publication_summary.md"},
            {"label": "paper tables", "path": "paper_tables.md"},
            {"label": "figure captions", "path": "figure_captions.md"},
            {"label": "paper appendix", "path": _display_path(Path(appendix_path), output_root)},
            {"label": "paper doc audit", "path": "paper_doc_audit.md"},
        ]
        + (
            [{"label": "manuscript packet", "path": _display_path(Path(manuscript_packet_path), output_root)}]
            if manuscript_packet_path is not None
            else []
        )
        + (
            [{"label": "submission export", "path": _display_path(Path(submission_export_path), output_root)}]
            if submission_export_path is not None
            else []
        )
        + (
            [{"label": "publication check", "path": _display_path(Path(publication_check_path), output_root)}]
            if publication_check_path is not None
            else []
        ),
        "docs_files": [
            {"label": "paper workflow README", "path": "docs/papers/README.md"},
            {"label": "flagship paper draft", "path": "docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md"},
            {"label": "flagship paper scaffold", "path": "docs/papers/KVRM_FLAGSHIP_PAPER_SCAFFOLD.md"},
            {"label": "evidence matrix", "path": "docs/papers/KVRM_EVIDENCE_MATRIX.md"},
            {"label": "figure source map", "path": "docs/papers/KVRM_FIGURE_SOURCE_MAP.md"},
        ]
        + (
            [{"label": "synced paper appendix", "path": _display_path(Path(docs_appendix_path), repo_root_path)}]
            if docs_appendix_path
            else []
        ),
        "headline_claims": summary["headline_claims"],
        "table_titles": [table["title"] for table in paper_assets["tables"]],
        "figure_titles": [figure["title"] for figure in paper_assets["figures"]],
    }

    json_path = output_root / DEFAULT_PUBLICATION_PORTAL_JSON
    markdown_path = output_root / DEFAULT_PUBLICATION_PORTAL_MD
    readme_path = output_root / DEFAULT_PUBLICATION_PORTAL_README
    markdown = render_publication_portal_markdown(portal)
    json_path.write_text(json.dumps(portal, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    readme_path.write_text(markdown, encoding="utf-8")
    return {
        "path": str(json_path),
        "markdown_path": str(markdown_path),
        "readme_path": str(readme_path),
        "portal": portal,
    }


def render_publication_portal_markdown(portal: dict[str, Any]) -> str:
    status = portal["status"]
    lines = [
        "# KVRM Publication Portal",
        "",
        f"Generated: {portal['generated_at']}",
        "",
        f"Output root: `{portal['output_root']}`",
        "",
        "## Status",
        "",
        f"- artifact count: {status['artifact_count']}",
        f"- copied artifacts: {status['copied_artifact_count']}",
        f"- missing artifacts: {status['missing_artifact_count']}",
        (
            f"- paper-doc audit: {status['paper_doc_check_count']}/"
            f"{status['paper_doc_check_count']} checks passed"
            if status["paper_doc_all_checks_passed"]
            else (
                f"- paper-doc audit: {status['paper_doc_check_count'] - len(status['paper_doc_failed_checks'])}/"
                f"{status['paper_doc_check_count']} checks passed; failed: "
                f"{', '.join(status['paper_doc_failed_checks'])}"
            )
        ),
        (
            f"- canonical suite: {status['canonical_domain_count']} domains, "
            f"{status['canonical_total_case_count']} cases"
        ),
    ]
    if status["publication_check_all_checks_passed"] is not None:
        if status["publication_check_all_checks_passed"]:
            lines.append(
                f"- publication check: {status['publication_check_check_count']}/"
                f"{status['publication_check_check_count']} checks passed"
            )
        else:
            failed = ", ".join(status["publication_check_failed_checks"]) or "unknown"
            lines.append(
                f"- publication check: "
                f"{status['publication_check_check_count'] - len(status['publication_check_failed_checks'])}/"
                f"{status['publication_check_check_count']} checks passed; failed: {failed}"
            )
    lines.extend(
        [
            "",
            "## Bundle Outputs",
            "",
        ]
    )
    for item in portal["bundle_files"]:
        lines.append(f"- {item['label']}: `{item['path']}`")

    lines.extend(
        [
            "",
            "## Manuscript Docs",
            "",
        ]
    )
    for item in portal["docs_files"]:
        lines.append(f"- {item['label']}: `{item['path']}`")

    lines.extend(
        [
            "",
            "## Headline Claims",
            "",
            "| Claim | Status | Evidence | Summary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for claim in portal["headline_claims"]:
        lines.append(
            f"| {claim['statement']} | {claim['status']} | `{claim['evidence']}` | {claim['summary']} |"
        )

    lines.extend(
        [
            "",
            "## Generated Tables",
            "",
        ]
    )
    for title in portal["table_titles"]:
        lines.append(f"- {title}")

    lines.extend(
        [
            "",
            "## Generated Figures",
            "",
        ]
    )
    for title in portal["figure_titles"]:
        lines.append(f"- {title}")
    lines.append("")
    return "\n".join(lines)


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
