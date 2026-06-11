from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kvrm_bench.publication_portal import build_publication_portal


DEFAULT_PUBLICATION_CHECK_JSON = "publication_check.json"
DEFAULT_PUBLICATION_CHECK_MD = "publication_check.md"

_PYTHONPATH_RELS: tuple[str, ...] = ()


def build_publication_check(
    repo_root: str | Path,
    *,
    output_dir: str | Path | None = None,
    commands: list[dict[str, Any]] | None = None,
    refresh_portal: bool = True,
) -> dict[str, Any]:
    repo_root_path = Path(repo_root)
    output_root = (
        Path(output_dir)
        if output_dir is not None
        else repo_root_path / "kvrm-bench" / "results" / "publication_bundle"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    command_specs = commands if commands is not None else default_publication_check_commands(repo_root_path, output_root)
    checks = [_run_check_command(repo_root_path, spec) for spec in command_specs]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_root": _display_path(output_root, repo_root_path),
        "all_checks_passed": all(item["passed"] for item in checks),
        "checks": checks,
    }
    payload["passed_check_count"] = sum(1 for item in checks if item["passed"])
    payload["failed_check_count"] = len(checks) - payload["passed_check_count"]
    payload["portal_refreshed"] = False

    if refresh_portal:
        payload["portal_refreshed"] = _refresh_publication_portal(repo_root_path, output_root, payload)

    json_path = output_root / DEFAULT_PUBLICATION_CHECK_JSON
    markdown_path = output_root / DEFAULT_PUBLICATION_CHECK_MD
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_publication_check_markdown(payload), encoding="utf-8")
    return {
        "path": str(json_path),
        "markdown_path": str(markdown_path),
        "check": payload,
    }


def default_publication_check_commands(repo_root: Path, output_root: Path) -> list[dict[str, Any]]:
    pythonpath = _repo_pythonpath(repo_root)
    return [
        {
            "name": "publication_bundle",
            "description": "refresh publication bundle and generated paper artifacts",
            "argv": [
                sys.executable,
                "kvrm-bench/scripts/run_publication_bundle.py",
                "--output-dir",
                str(output_root),
            ],
            "cwd": str(repo_root),
            "env": {"PYTHONPATH": pythonpath},
        },
        {
            "name": "paper_doc_audit",
            "description": "run direct paper-doc alignment audit",
            "argv": [
                sys.executable,
                "kvrm-bench/scripts/run_paper_doc_audit.py",
                "--output-dir",
                str(output_root),
            ],
            "cwd": str(repo_root),
            "env": {"PYTHONPATH": pythonpath},
        },
        {
            "name": "kvrm_bench_tests",
            "description": "run the publication-critical test suite",
            "argv": [
                sys.executable,
                "-m",
                "pytest",
                "tests/kvrm_bench",
                "-q",
            ],
            "cwd": str(repo_root),
            "env": {"PYTHONPATH": pythonpath},
        },
    ]


def render_publication_check_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# KVRM Publication Check",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        f"Output root: `{payload['output_root']}`",
        "",
        f"All checks passed: `{str(payload['all_checks_passed']).lower()}`",
        f"Passed checks: {payload['passed_check_count']}",
        f"Failed checks: {payload['failed_check_count']}",
        f"Portal refreshed: `{str(payload['portal_refreshed']).lower()}`",
        "",
        "| Check | Status | Exit Code | Duration (s) | Description |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for item in payload["checks"]:
        status = "pass" if item["passed"] else "fail"
        lines.append(
            f"| {item['name']} | {status} | {item['returncode']} | "
            f"{item['duration_seconds']:.2f} | {item['description']} |"
        )
    for item in payload["checks"]:
        if not item["stdout_tail"] and not item["stderr_tail"]:
            continue
        lines.extend(
            [
                "",
                f"## {item['name']}",
                "",
                f"Command: `{item['command']}`",
                "",
            ]
        )
        if item["stdout_tail"]:
            lines.extend(["### Stdout Tail", "", "```text", item["stdout_tail"], "```", ""])
        if item["stderr_tail"]:
            lines.extend(["### Stderr Tail", "", "```text", item["stderr_tail"], "```", ""])
    return "\n".join(lines)


def _run_check_command(repo_root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    argv = [str(item) for item in spec["argv"]]
    env = os.environ.copy()
    for key, value in (spec.get("env") or {}).items():
        if key == "PYTHONPATH" and env.get("PYTHONPATH"):
            env[key] = f"{value}:{env['PYTHONPATH']}"
        else:
            env[key] = str(value)

    started = time.perf_counter()
    completed = subprocess.run(
        argv,
        cwd=spec.get("cwd") or str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.perf_counter() - started
    return {
        "name": str(spec["name"]),
        "description": str(spec.get("description") or ""),
        "command": " ".join(argv),
        "returncode": int(completed.returncode),
        "passed": completed.returncode == 0,
        "duration_seconds": duration,
        "stdout_tail": _tail_text(completed.stdout),
        "stderr_tail": _tail_text(completed.stderr),
    }


def _refresh_publication_portal(repo_root: Path, output_root: Path, publication_check: dict[str, Any]) -> bool:
    manifest = _load_json(output_root / "manifest.json")
    summary = _load_json(output_root / "publication_summary.json")
    paper_assets = _load_json(output_root / "paper_assets.json")
    paper_doc_audit = _load_json(output_root / "paper_doc_audit.json")
    if not all((manifest, summary, paper_assets, paper_doc_audit)):
        return False

    build_publication_portal(
        repo_root,
        output_dir=output_root,
        manifest=manifest,
        summary=summary,
        paper_assets=paper_assets,
        paper_doc_audit=paper_doc_audit,
        appendix_path=str(output_root / "paper_appendix.md"),
        docs_appendix_path=str(repo_root / "docs" / "papers" / "KVRM_PUBLICATION_APPENDIX.md"),
        manuscript_packet_path=(
            str(output_root / "manuscript" / "README.md")
            if (output_root / "manuscript" / "README.md").exists()
            else None
        ),
        submission_export_path=(
            str(output_root / "submission" / "README.md")
            if (output_root / "submission" / "README.md").exists()
            else None
        ),
        publication_check=publication_check,
        publication_check_path=str(output_root / DEFAULT_PUBLICATION_CHECK_MD),
    )
    return True


def _repo_pythonpath(repo_root: Path) -> str:
    return ":".join(str(repo_root / rel) for rel in _PYTHONPATH_RELS)


def _tail_text(text: str, *, max_lines: int = 32, max_chars: int = 5000) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    lines = text.splitlines()
    tail = "\n".join(lines[-max_lines:])
    if len(tail) <= max_chars:
        return tail
    return tail[-max_chars:]


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
