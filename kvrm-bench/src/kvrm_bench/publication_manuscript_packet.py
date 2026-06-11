from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PUBLICATION_MANUSCRIPT_DIRNAME = "manuscript"
DEFAULT_PUBLICATION_MANUSCRIPT_MANIFEST_JSON = "manifest.json"
DEFAULT_PUBLICATION_MANUSCRIPT_MANIFEST_MD = "manifest.md"
DEFAULT_PUBLICATION_MANUSCRIPT_README = "README.md"

_PACKET_ITEMS: tuple[tuple[str, str, str, str, str], ...] = (
    ("manuscript", "flagship paper draft", "repo", "docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md", "KVRM_FLAGSHIP_PAPER_DRAFT.md"),
    ("manuscript", "publication appendix", "repo", "docs/papers/KVRM_PUBLICATION_APPENDIX.md", "KVRM_PUBLICATION_APPENDIX.md"),
    ("manuscript", "bibliography", "repo", "docs/papers/kvrm_refs.bib", "kvrm_refs.bib"),
    ("workflow", "paper workflow", "repo", "docs/papers/README.md", "PAPER_WORKFLOW.md"),
    ("workflow", "evidence matrix", "repo", "docs/papers/KVRM_EVIDENCE_MATRIX.md", "KVRM_EVIDENCE_MATRIX.md"),
    ("workflow", "figure source map", "repo", "docs/papers/KVRM_FIGURE_SOURCE_MAP.md", "KVRM_FIGURE_SOURCE_MAP.md"),
    ("generated", "publication summary", "bundle", "publication_summary.md", "publication_summary.md"),
    ("generated", "paper tables", "bundle", "paper_tables.md", "paper_tables.md"),
    ("generated", "figure captions", "bundle", "figure_captions.md", "figure_captions.md"),
    ("generated", "paper doc audit", "bundle", "paper_doc_audit.md", "paper_doc_audit.md"),
)


def build_publication_manuscript_packet(
    repo_root: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root_path = Path(repo_root)
    output_root = (
        Path(output_dir)
        if output_dir is not None
        else repo_root_path / "kvrm-bench" / "results" / "publication_bundle"
    )
    packet_root = output_root / DEFAULT_PUBLICATION_MANUSCRIPT_DIRNAME
    shutil.rmtree(packet_root, ignore_errors=True)
    packet_root.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, Any]] = []
    copied_count = 0
    missing_count = 0
    copied_bytes = 0

    for section, label, source_root, relative_source, packet_name in _PACKET_ITEMS:
        source_path = (
            repo_root_path / relative_source
            if source_root == "repo"
            else output_root / relative_source
        )
        exists = source_path.is_file()
        size_bytes = source_path.stat().st_size if exists else None
        target_path = packet_root / packet_name
        if exists:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            copied_count += 1
            copied_bytes += int(size_bytes or 0)
        else:
            missing_count += 1
        files.append(
            {
                "section": section,
                "label": label,
                "source_root": source_root,
                "source_path": relative_source,
                "packet_path": str(Path(DEFAULT_PUBLICATION_MANUSCRIPT_DIRNAME) / packet_name),
                "exists": exists,
                "size_bytes": size_bytes,
                "sha256": _sha256_file(source_path) if exists else None,
            }
        )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_root": _display_path(output_root, repo_root_path),
        "packet_root": _display_path(packet_root, repo_root_path),
        "file_count": len(files),
        "copied_file_count": copied_count,
        "missing_file_count": missing_count,
        "copied_bytes": copied_bytes,
        "files": files,
    }

    manifest_path = packet_root / DEFAULT_PUBLICATION_MANUSCRIPT_MANIFEST_JSON
    markdown_path = packet_root / DEFAULT_PUBLICATION_MANUSCRIPT_MANIFEST_MD
    readme_path = packet_root / DEFAULT_PUBLICATION_MANUSCRIPT_README
    markdown = render_publication_manuscript_packet_markdown(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    readme_path.write_text(markdown, encoding="utf-8")
    return {
        "path": str(manifest_path),
        "markdown_path": str(markdown_path),
        "readme_path": str(readme_path),
        "packet": manifest,
    }


def render_publication_manuscript_packet_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# KVRM Manuscript Packet",
        "",
        f"Generated: {manifest['generated_at']}",
        "",
        f"Output root: `{manifest['output_root']}`",
        f"Packet root: `{manifest['packet_root']}`",
        "",
        (
            "This packet stages the manuscript-facing draft, appendix, bibliography, and paper-facing "
            "generated outputs into one deterministic subdirectory so paper handoff does not require "
            "walking the full evidence tree."
        ),
        "",
        f"File count: {manifest['file_count']}",
        f"Copied files: {manifest['copied_file_count']}",
        f"Missing files: {manifest['missing_file_count']}",
        f"Copied bytes: {manifest['copied_bytes']}",
        "",
        "| Section | Label | Source | Status | Packet Path | Size |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    for item in manifest["files"]:
        lines.append(
            "| "
            f"{item['section']} | "
            f"{item['label']} | "
            f"`{item['source_path']}` | "
            f"{'copied' if item['exists'] else 'missing'} | "
            f"`{item['packet_path']}` | "
            f"{int(item['size_bytes'] or 0)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
