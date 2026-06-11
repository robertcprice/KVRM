from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PAPER_DOC_AUDIT_JSON = "paper_doc_audit.json"
DEFAULT_PAPER_DOC_AUDIT_MD = "paper_doc_audit.md"

_DRAFT_DUPLICATE_TABLE_HEADERS = (
    "| Domain  | Semantic Correctness | False Accept | Unsupported Rejection | Invalid Output | Mean Cost |",
    "| Domain | Gated Semantic | Ungated Semantic | Gated Cost | Ungated Cost | Gated Rescue |",
    (
        "| Domain | Cases | Live Continuity | Stale Validated Continuity | "
        "Stale Unvalidated Obsolete Execution | Live Tight Reject | "
        "Stale Unvalidated Tight False Accept |"
    ),
    "| Benchmark Family | Win / Tie / Loss vs Best Non-Hybrid | Strict Hybrid-Win Domains |",
)

_DRAFT_INTERNAL_ONLY_MARKERS = (
    "draft for internal revision",
    "prose-first draft; final citations and venue formatting still pending",
    "This draft supports five core claims.",
    "Primary artifacts for this draft:",
)

_SCAFFOLD_DUPLICATE_TABLE_HEADERS = (
    "| Domain  | Total | Supported | Unsupported | Hybrid Semantic | False Accept | Unsupported Rejection | Invalid Output | Mean Cost |",
    "| Benchmark Slice | Gated Hybrid | Ungated/Post-hoc Baseline |",
    "| Domain | Cases | Strict Unsupported Unsafe Execution | Legacy Unsupported Unsafe Execution | Strict Mean Feasibility Cost | Legacy Mean Feasibility Cost |",
    "| Benchmark family | Win / Tie / Loss vs best non-hybrid | Strict hybrid-win domains |",
)


def build_paper_doc_audit(
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
    output_root.mkdir(parents=True, exist_ok=True)

    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_root": _display_path(output_root, repo_root_path),
        "checks": _build_checks(repo_root_path),
    }
    audit["all_checks_passed"] = all(item["passed"] for item in audit["checks"])

    json_path = output_root / DEFAULT_PAPER_DOC_AUDIT_JSON
    markdown_path = output_root / DEFAULT_PAPER_DOC_AUDIT_MD
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_paper_doc_audit_markdown(audit), encoding="utf-8")
    return {
        "path": str(json_path),
        "markdown_path": str(markdown_path),
        "audit": audit,
    }


def render_paper_doc_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# KVRM Paper Doc Audit",
        "",
        f"Generated: {audit['generated_at']}",
        "",
        f"Output root: `{audit['output_root']}`",
        "",
        f"All checks passed: `{str(audit['all_checks_passed']).lower()}`",
        "",
        "| Check | Status | Details |",
        "| --- | --- | --- |",
    ]
    for item in audit["checks"]:
        status = "pass" if item["passed"] else "fail"
        lines.append(f"| {item['name']} | {status} | {item['details']} |")
    lines.append("")
    return "\n".join(lines)


def _build_checks(repo_root: Path) -> list[dict[str, Any]]:
    paper_dir = repo_root / "docs" / "papers"
    paths = {
        "draft": paper_dir / "KVRM_FLAGSHIP_PAPER_DRAFT.md",
        "scaffold": paper_dir / "KVRM_FLAGSHIP_PAPER_SCAFFOLD.md",
        "evidence_matrix": paper_dir / "KVRM_EVIDENCE_MATRIX.md",
        "figure_source_map": paper_dir / "KVRM_FIGURE_SOURCE_MAP.md",
        "appendix": paper_dir / "KVRM_PUBLICATION_APPENDIX.md",
        "readme": paper_dir / "README.md",
        "refs": paper_dir / "kvrm_refs.bib",
    }

    texts = {name: _read_text(path) for name, path in paths.items()}
    draft_citation_keys = _extract_citation_keys(texts["draft"])
    bibliography_keys = _extract_bibliography_keys(texts["refs"])

    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "paper docs present",
            all(text is not None for text in texts.values()),
            ", ".join(name for name, text in texts.items() if text is not None),
        )
    )
    checks.append(
        _check(
            "draft points to workflow and appendix",
            _contains_all(texts["draft"], ("docs/papers/README.md", "docs/papers/KVRM_PUBLICATION_APPENDIX.md")),
            "flagship draft references both the workflow README and the generated appendix",
        )
    )
    checks.append(
        _check(
            "draft appendix table refs present",
            _contains_all(
                texts["draft"],
                ("Appendix Table 1", "Appendix Table 2", "Appendix Table 3", "Appendix Table 5", "Appendix Table 6"),
            ),
            "flagship draft references Appendix Tables 1, 2, 3, 5, and 6",
        )
    )
    checks.append(
        _check(
            "draft duplicate benchmark tables absent",
            _contains_none(texts["draft"], _DRAFT_DUPLICATE_TABLE_HEADERS),
            "flagship draft does not carry duplicated canonical/support-gate/registry-evolution/robustness tables",
        )
    )
    checks.append(
        _check(
            "draft internal-only markers absent",
            _contains_none(texts["draft"], _DRAFT_INTERNAL_ONLY_MARKERS),
            "flagship draft avoids internal-revision markers and uses manuscript-facing wording",
        )
    )
    checks.append(
        _check(
            "draft citekeys present",
            bool(draft_citation_keys),
            "flagship draft uses bibliography citekeys rather than prose-only literature references",
        )
    )
    checks.append(
        _check(
            "draft citekeys resolve in bibliography",
            bool(draft_citation_keys) and draft_citation_keys.issubset(bibliography_keys),
            (
                "all citekeys used by the flagship draft resolve in docs/papers/kvrm_refs.bib"
                if draft_citation_keys.issubset(bibliography_keys)
                else "missing bibliography keys: " + ", ".join(sorted(draft_citation_keys - bibliography_keys))
            ),
        )
    )
    checks.append(
        _check(
            "draft duplicate references block absent",
            _contains_none(texts["draft"], ("## References (Working)",)),
            "flagship draft uses docs/papers/kvrm_refs.bib instead of a second manual references block",
        )
    )
    checks.append(
        _check(
            "scaffold points to workflow and appendix",
            _contains_all(texts["scaffold"], ("docs/papers/README.md", "docs/papers/KVRM_PUBLICATION_APPENDIX.md")),
            "scaffold references the workflow README and the generated appendix",
        )
    )
    checks.append(
        _check(
            "scaffold appendix refs present",
            _contains_all(texts["scaffold"], ("Appendix Table 1", "Appendix Table 2", "Appendix Table 3", "Appendix Table 6")),
            "scaffold references Appendix Tables 1, 2, 3, and 6",
        )
    )
    checks.append(
        _check(
            "scaffold duplicate benchmark tables absent",
            _contains_none(texts["scaffold"], _SCAFFOLD_DUPLICATE_TABLE_HEADERS),
            "scaffold does not carry duplicated benchmark tables that are now appendix-backed",
        )
    )
    checks.append(
        _check(
            "evidence matrix points to workflow and appendix",
            _contains_all(texts["evidence_matrix"], ("docs/papers/README.md", "docs/papers/KVRM_PUBLICATION_APPENDIX.md")),
            "evidence matrix points authors to the workflow README and generated appendix",
        )
    )
    checks.append(
        _check(
            "figure source map points to appendix",
            _contains_all(texts["figure_source_map"], ("docs/papers/KVRM_PUBLICATION_APPENDIX.md", "generated appendix/caption outputs")),
            "figure source map documents the manuscript-facing caption snapshot",
        )
    )
    checks.append(
        _check(
            "paper README documents generated appendix rules",
            _contains_all(
                texts["readme"],
                (
                    "docs/papers/KVRM_PUBLICATION_APPENDIX.md",
                    "do not hand-edit the generated appendix",
                    "The flagship draft should reference Appendix Tables/Figures",
                    "docs/papers/kvrm_refs.bib",
                ),
            ),
            "paper README documents the generated-vs-hand-edited workflow",
        )
    )
    checks.append(
        _check(
            "checked-in appendix contains core sections",
            _contains_all(
                texts["appendix"],
                (
                    "# KVRM Publication Appendix",
                    "## Headline Claims",
                    "### Table 1. Canonical Seven-Domain Hybrid KVRM Results",
                    "### Table 5. Evaluated Small-Model Ollama Baseline Comparison",
                    "### Figure 7: Replay, counterfactual, temporal, and coordination robustness summary",
                ),
            ),
            "checked-in appendix still exposes the expected headline/table/figure sections",
        )
    )
    return checks


def _check(name: str, passed: bool, details: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "details": details,
    }


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _contains_all(text: str | None, patterns: tuple[str, ...]) -> bool:
    if text is None:
        return False
    return all(pattern in text for pattern in patterns)


def _contains_none(text: str | None, patterns: tuple[str, ...]) -> bool:
    if text is None:
        return False
    return all(pattern not in text for pattern in patterns)


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _extract_citation_keys(text: str | None) -> set[str]:
    if text is None:
        return set()
    return set(re.findall(r"@([A-Za-z0-9:_-]+)", text))


def _extract_bibliography_keys(text: str | None) -> set[str]:
    if text is None:
        return set()
    return set(re.findall(r"@\w+\{([^,\s]+),", text))
