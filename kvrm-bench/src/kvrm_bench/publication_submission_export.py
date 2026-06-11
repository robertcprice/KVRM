from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PUBLICATION_SUBMISSION_DIRNAME = "submission"
DEFAULT_PUBLICATION_SUBMISSION_MANIFEST_JSON = "manifest.json"
DEFAULT_PUBLICATION_SUBMISSION_MANIFEST_MD = "manifest.md"
DEFAULT_PUBLICATION_SUBMISSION_README = "README.md"
DEFAULT_PUBLICATION_SUBMISSION_BUNDLE_ZIP = "submission_bundle.zip"
DEFAULT_PUBLICATION_SUBMISSION_PROFILE = "review-anonymous"
SUPPORTED_PUBLICATION_SUBMISSION_PROFILES = (
    "review-anonymous",
    "working-manuscript",
)

_SOURCE_FILES: tuple[tuple[str, str, str], ...] = (
    ("paper", "KVRM_FLAGSHIP_PAPER_DRAFT.md", "paper.md"),
    ("appendix", "KVRM_PUBLICATION_APPENDIX.md", "appendix.md"),
    ("references", "kvrm_refs.bib", "references.bib"),
)


def build_publication_submission_export(
    repo_root: str | Path,
    *,
    output_dir: str | Path | None = None,
    pandoc_bin: str = "pandoc",
    pdf_engine: str = "pdflatex",
    profile: str = DEFAULT_PUBLICATION_SUBMISSION_PROFILE,
    dirname: str | Path = DEFAULT_PUBLICATION_SUBMISSION_DIRNAME,
) -> dict[str, Any]:
    if profile not in SUPPORTED_PUBLICATION_SUBMISSION_PROFILES:
        raise ValueError(f"unsupported submission export profile: {profile}")
    repo_root_path = Path(repo_root)
    output_root = (
        Path(output_dir)
        if output_dir is not None
        else repo_root_path / "kvrm-bench" / "results" / "publication_bundle"
    )
    manuscript_root = output_root / "manuscript"
    submission_root = output_root / Path(dirname)

    shutil.rmtree(submission_root, ignore_errors=True)
    submission_root.mkdir(parents=True, exist_ok=True)

    copied_sources: list[dict[str, Any]] = []
    for label, filename, output_name in _SOURCE_FILES:
        source_path = manuscript_root / filename
        if not source_path.exists():
            raise FileNotFoundError(f"missing manuscript packet source: {source_path}")
        target_path = submission_root / output_name
        if filename.endswith(".md"):
            source_text = source_path.read_text(encoding="utf-8")
            rendered_text = _prepare_submission_markdown(
                label=label,
                source_text=source_text,
                profile=profile,
            )
            target_path.write_text(rendered_text, encoding="utf-8")
        else:
            shutil.copy2(source_path, target_path)
        copied_sources.append(
            {
                "label": label,
                "source_label": filename,
                "source_path": _display_path(source_path, repo_root_path),
                "submission_path": _display_path(target_path, repo_root_path),
                "size_bytes": target_path.stat().st_size,
                "sha256": _sha256_file(target_path),
            }
        )

    commands = [
        _build_pandoc_command(
            pandoc_bin=pandoc_bin,
            pdf_engine=pdf_engine,
            cwd=submission_root,
            input_name="paper.md",
            output_name="paper.tex",
            to_format="latex",
            write_pdf=False,
            profile=profile,
        ),
        _build_pandoc_command(
            pandoc_bin=pandoc_bin,
            pdf_engine=pdf_engine,
            cwd=submission_root,
            input_name="paper.md",
            output_name="paper.pdf",
            to_format=None,
            write_pdf=True,
            profile=profile,
        ),
        _build_pandoc_command(
            pandoc_bin=pandoc_bin,
            pdf_engine=pdf_engine,
            cwd=submission_root,
            input_name="appendix.md",
            output_name="appendix.tex",
            to_format="latex",
            write_pdf=False,
            profile=profile,
        ),
        _build_pandoc_command(
            pandoc_bin=pandoc_bin,
            pdf_engine=pdf_engine,
            cwd=submission_root,
            input_name="appendix.md",
            output_name="appendix.pdf",
            to_format=None,
            write_pdf=True,
            profile=profile,
        ),
    ]
    command_results = [_run_command(command) for command in commands]

    generated_files: list[dict[str, Any]] = []
    for filename in (
        "paper.tex",
        "paper.pdf",
        "appendix.tex",
        "appendix.pdf",
    ):
        path = submission_root / filename
        generated_files.append(
            {
                "label": filename,
                "submission_path": _display_path(path, repo_root_path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "sha256": _sha256_file(path) if path.exists() else None,
                "pdf_metadata": _pdfinfo_metadata(path) if path.exists() and path.suffix == ".pdf" else None,
            }
        )

    bundle_zip_path = submission_root / DEFAULT_PUBLICATION_SUBMISSION_BUNDLE_ZIP
    _write_submission_bundle_zip(
        bundle_zip_path,
        sources=[submission_root / item["submission_path"].split("/")[-1] for item in generated_files + copied_sources],
    )

    tool_versions = {
        "pandoc": _tool_version(pandoc_bin),
        pdf_engine: _tool_version(pdf_engine),
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_root": _display_path(output_root, repo_root_path),
        "manuscript_root": _display_path(manuscript_root, repo_root_path),
        "submission_root": _display_path(submission_root, repo_root_path),
        "profile": profile,
        "tool_versions": tool_versions,
        "source_files": copied_sources,
        "generated_files": generated_files,
        "bundle_zip_path": _display_path(bundle_zip_path, repo_root_path),
        "bundle_zip_size_bytes": bundle_zip_path.stat().st_size if bundle_zip_path.exists() else None,
        "commands": command_results,
        "all_exports_succeeded": all(item["passed"] for item in command_results),
        "all_pdf_authors_blank": all(
            not ((item.get("pdf_metadata") or {}).get("Author") or "").strip()
            for item in generated_files
            if item["label"].endswith(".pdf")
        ),
    }

    manifest_path = submission_root / DEFAULT_PUBLICATION_SUBMISSION_MANIFEST_JSON
    markdown_path = submission_root / DEFAULT_PUBLICATION_SUBMISSION_MANIFEST_MD
    readme_path = submission_root / DEFAULT_PUBLICATION_SUBMISSION_README
    markdown = render_publication_submission_export_markdown(payload)
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    readme_path.write_text(markdown, encoding="utf-8")
    return {
        "path": str(manifest_path),
        "markdown_path": str(markdown_path),
        "readme_path": str(readme_path),
        "export": payload,
    }


def build_publication_submission_export_matrix(
    repo_root: str | Path,
    *,
    output_dir: str | Path | None = None,
    pandoc_bin: str = "pandoc",
    pdf_engine: str = "pdflatex",
    profiles: tuple[str, ...] = SUPPORTED_PUBLICATION_SUBMISSION_PROFILES,
    dirname: str | Path = DEFAULT_PUBLICATION_SUBMISSION_DIRNAME,
) -> dict[str, Any]:
    repo_root_path = Path(repo_root)
    output_root = (
        Path(output_dir)
        if output_dir is not None
        else repo_root_path / "kvrm-bench" / "results" / "publication_bundle"
    )
    manuscript_root = output_root / "manuscript"
    submission_root = output_root / Path(dirname)

    if any(profile not in SUPPORTED_PUBLICATION_SUBMISSION_PROFILES for profile in profiles):
        raise ValueError(f"unsupported submission export profiles: {profiles}")

    shutil.rmtree(submission_root, ignore_errors=True)
    submission_root.mkdir(parents=True, exist_ok=True)

    profile_results: list[dict[str, Any]] = []
    for profile in profiles:
        profile_dirname = Path(dirname) / profile
        result = build_publication_submission_export(
            repo_root,
            output_dir=output_root,
            pandoc_bin=pandoc_bin,
            pdf_engine=pdf_engine,
            profile=profile,
            dirname=profile_dirname,
        )
        export = result["export"]
        profile_results.append(
            {
                "profile": profile,
                "submission_root": export["submission_root"],
                "manifest_path": _display_path(Path(result["path"]), repo_root_path),
                "markdown_path": _display_path(Path(result["markdown_path"]), repo_root_path),
                "readme_path": _display_path(Path(result["readme_path"]), repo_root_path),
                "paper_pdf_path": _generated_file_path(export["generated_files"], "paper.pdf"),
                "appendix_pdf_path": _generated_file_path(export["generated_files"], "appendix.pdf"),
                "bundle_zip_path": export["bundle_zip_path"],
                "all_exports_succeeded": export["all_exports_succeeded"],
                "all_pdf_authors_blank": export["all_pdf_authors_blank"],
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_root": _display_path(output_root, repo_root_path),
        "manuscript_root": _display_path(manuscript_root, repo_root_path),
        "submission_root": _display_path(submission_root, repo_root_path),
        "profile_count": len(profile_results),
        "profiles": profile_results,
        "all_exports_succeeded": all(item["all_exports_succeeded"] for item in profile_results),
        "all_pdf_authors_blank": all(item["all_pdf_authors_blank"] for item in profile_results),
    }

    manifest_path = submission_root / DEFAULT_PUBLICATION_SUBMISSION_MANIFEST_JSON
    markdown_path = submission_root / DEFAULT_PUBLICATION_SUBMISSION_MANIFEST_MD
    readme_path = submission_root / DEFAULT_PUBLICATION_SUBMISSION_README
    markdown = render_publication_submission_export_matrix_markdown(payload)
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    readme_path.write_text(markdown, encoding="utf-8")
    return {
        "path": str(manifest_path),
        "markdown_path": str(markdown_path),
        "readme_path": str(readme_path),
        "export": payload,
    }


def render_publication_submission_export_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Submission Export",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        f"Output root: `{payload['output_root']}`",
        f"Manuscript packet root: `{payload['manuscript_root']}`",
        f"Submission root: `{payload['submission_root']}`",
        f"Profile: `{payload['profile']}`",
        "",
        f"All exports succeeded: `{str(payload['all_exports_succeeded']).lower()}`",
        f"All PDF authors blank: `{str(payload['all_pdf_authors_blank']).lower()}`",
        f"Pandoc: `{payload['tool_versions'].get('pandoc') or 'unknown'}`",
    ]
    pdf_engine_name = next((key for key in payload["tool_versions"] if key != "pandoc"), None)
    if pdf_engine_name is not None:
        lines.append(f"{pdf_engine_name}: `{payload['tool_versions'].get(pdf_engine_name) or 'unknown'}`")
    lines.extend(
        [
            "",
            (
                "The submission sources are normalized to `paper.*`, `appendix.*`, and `references.bib`, "
                "and the exported markdown is rewritten into title-aware Pandoc input so the LaTeX/PDF outputs "
                "use a real title block instead of treating the title as the first section heading."
            ),
        ]
    )
    if payload["profile"] == "review-anonymous":
        lines.extend(
            [
                "",
                (
                    "The anonymous review profile strips repo-only workflow sections such as manuscript status, "
                    "artifact references, and bibliography workflow notes from the exported paper source."
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Source Files",
            "",
            "| File | Source | Submission Path | Size |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for item in payload["source_files"]:
        lines.append(
            f"| {item['label']} | `{item['source_path']}` | `{item['submission_path']}` | {item['size_bytes']} |"
        )

    lines.extend(
        [
            "",
            "## Generated Files",
            "",
            "| File | Status | Submission Path | Size | PDF Author |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for item in payload["generated_files"]:
        lines.append(
            f"| {item['label']} | {'ready' if item['exists'] else 'missing'} | "
            f"`{item['submission_path']}` | {int(item['size_bytes'] or 0)} | "
            f"{((item.get('pdf_metadata') or {}).get('Author') or '-')} |"
        )

    lines.extend(
        [
            "",
            f"Submission bundle zip: `{payload['bundle_zip_path']}`",
            "",
            "## Commands",
            "",
            "| Output | Status | Command |",
            "| --- | --- | --- |",
        ]
    )
    for item in payload["commands"]:
        lines.append(
            f"| {item['output_name']} | {'pass' if item['passed'] else 'fail'} | `{item['command']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def render_publication_submission_export_matrix_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Submission Export Matrix",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        f"Output root: `{payload['output_root']}`",
        f"Manuscript packet root: `{payload['manuscript_root']}`",
        f"Submission root: `{payload['submission_root']}`",
        f"Profiles: {payload['profile_count']}",
        "",
        f"All exports succeeded: `{str(payload['all_exports_succeeded']).lower()}`",
        f"All PDF authors blank: `{str(payload['all_pdf_authors_blank']).lower()}`",
        "",
        (
            "The bundle-level submission index keeps both publication profiles side by side so "
            "anonymous-review and working-manuscript exports are reproducible without overwriting each other."
        ),
        "",
        "| Profile | Status | PDF Authors Blank | README | Paper PDF | Bundle Zip |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["profiles"]:
        lines.append(
            f"| {item['profile']} | "
            f"{'pass' if item['all_exports_succeeded'] else 'fail'} | "
            f"{str(item['all_pdf_authors_blank']).lower()} | "
            f"`{item['readme_path']}` | "
            f"`{item['paper_pdf_path']}` | "
            f"`{item['bundle_zip_path']}` |"
        )
    lines.extend(
        [
            "",
            "Profile notes:",
            f"- `review-anonymous`: {_profile_note('review-anonymous')}",
            f"- `working-manuscript`: {_profile_note('working-manuscript')}",
            "",
        ]
    )
    return "\n".join(lines)


def _build_pandoc_command(
    *,
    pandoc_bin: str,
    pdf_engine: str,
    cwd: Path,
    input_name: str,
    output_name: str,
    to_format: str | None,
    write_pdf: bool,
    profile: str,
) -> dict[str, Any]:
    argv = [
        pandoc_bin,
        input_name,
        "--from",
        "markdown",
        "--standalone",
        "--citeproc",
        "--bibliography",
        "references.bib",
        "-o",
        output_name,
    ]
    argv.extend(_profile_pandoc_args(profile))
    if to_format is not None:
        argv.extend(["--to", to_format])
    if write_pdf:
        argv.extend(["--pdf-engine", pdf_engine])
    return {
        "argv": argv,
        "cwd": str(cwd),
        "output_name": output_name,
    }


def _run_command(spec: dict[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        [str(item) for item in spec["argv"]],
        cwd=spec["cwd"],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "output_name": spec["output_name"],
        "command": " ".join(str(item) for item in spec["argv"]),
        "passed": completed.returncode == 0,
        "returncode": int(completed.returncode),
        "stdout_tail": _tail_text(completed.stdout),
        "stderr_tail": _tail_text(completed.stderr),
    }


def _tool_version(tool: str) -> str | None:
    completed = subprocess.run(
        [tool, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    line = (completed.stdout or "").splitlines()
    return line[0].strip() if line else None


def _pdfinfo_metadata(path: Path) -> dict[str, str] | None:
    completed = subprocess.run(
        ["pdfinfo", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    metadata: dict[str, str] = {}
    for line in (completed.stdout or "").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def _sanitize_submission_manuscript(text: str) -> str:
    sanitized = text
    sanitized = re.sub(
        r"^Manuscript Status:\n(?:- .+\n)+\n",
        "",
        sanitized,
        flags=re.MULTILINE,
    )
    sanitized = _strip_markdown_section(sanitized, "## Artifact References")
    sanitized = _strip_markdown_section(sanitized, "## Bibliography Workflow")
    return sanitized.strip() + "\n"


def _strip_markdown_section(text: str, heading: str) -> str:
    pattern = rf"^{re.escape(heading)}\n.*?(?=^## |\Z)"
    return re.sub(pattern, "", text, flags=re.MULTILINE | re.DOTALL)


def _write_submission_bundle_zip(archive_path: Path, *, sources: list[Path]) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            archive.write(source, arcname=source.name)


def _prepare_submission_markdown(*, label: str, source_text: str, profile: str) -> str:
    working_text = source_text
    if profile == "review-anonymous" and label == "paper":
        working_text = _sanitize_submission_manuscript(working_text)

    title, body = _extract_markdown_title_and_body(working_text)
    body = _shift_markdown_headings(body)
    metadata = [
        "---",
        f'title: "{_escape_yaml(title)}"',
        'author: ""',
        'date: ""',
        "---",
        "",
    ]
    return "\n".join(metadata) + "\n" + body.strip() + "\n"


def _extract_markdown_title_and_body(text: str) -> tuple[str, str]:
    match = re.match(r"^#\s+(.+?)\n+", text)
    if match is None:
        raise ValueError("submission markdown is missing a top-level title heading")
    title = match.group(1).strip()
    body = text[match.end() :]
    return title, body


def _shift_markdown_headings(text: str) -> str:
    return re.sub(r"^(#{2,6})\s+", lambda match: "#" * (len(match.group(1)) - 1) + " ", text, flags=re.MULTILINE)


def _escape_yaml(text: str) -> str:
    return text.replace('"', '\\"')


def _profile_pandoc_args(profile: str) -> list[str]:
    if profile == "review-anonymous":
        return ["-V", "geometry:margin=1in"]
    if profile == "working-manuscript":
        return []
    raise ValueError(f"unsupported submission export profile: {profile}")


def _generated_file_path(generated_files: list[dict[str, Any]], label: str) -> str | None:
    match = next((item for item in generated_files if item["label"] == label), None)
    return None if match is None else str(match["submission_path"])


def _profile_note(profile: str) -> str:
    if profile == "review-anonymous":
        return (
            "strips repo-only workflow sections from the paper source and keeps the exported "
            "LaTeX/PDF metadata anonymous."
        )
    if profile == "working-manuscript":
        return "keeps the full manuscript prose while still normalizing the venue-facing filenames."
    raise ValueError(f"unsupported submission export profile: {profile}")


def _tail_text(text: str, *, max_lines: int = 10, max_chars: int = 1000) -> str:
    stripped = (text or "").strip()
    if not stripped:
        return ""
    tail = "\n".join(stripped.splitlines()[-max_lines:])
    if len(tail) <= max_chars:
        return tail
    return tail[-max_chars:]


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
