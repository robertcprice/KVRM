#!/usr/bin/env python3
"""
After the layout flattening, fix every stale PYTHONPATH / path reference that still
contains the old "kvrm-demos/xxx-router/src" pattern.

We only touch the demo parts — kvrm-core/src and kvrm-bench/src stay as they are.
"""

from pathlib import Path
import re

ROOT = Path(".")

# All demo kebab names that had the old layout
DEMOS = [
    "sre-policy-router",
    "soc-playbook-router",
    "drone-mission-router",
    "grid-ops-router",
    "finance-risk-router",
    "medical-workflow-router",
    "iam-access-router",
    "customer-support-router",
    "content-moderation-router",
    "legal-compliance-router",
    "cicd-pipeline-router",
    "insurance-claims-router",
]

def fix_text(text: str) -> tuple[str, int]:
    changes = 0
    for demo in DEMOS:
        old = f"kvrm-demos/{demo}/src"
        new = f"kvrm-demos/{demo}"
        if old in text:
            text = text.replace(old, new)
            changes += 1
    return text, changes

def main():
    total_files = 0
    total_changes = 0

    # Only touch text files that are likely to have the strings
    patterns = ["*.py", "*.md", "*.txt", "*.sh"]

    files = []
    for pat in patterns:
        files.extend(ROOT.rglob(pat))

    # Skip obvious generated / binary / venv areas
    skip_dirs = {"venv", ".venv", "__pycache__", "node_modules", ".git", "kvrm-vector", "kvrm-gpu/venv", "kvrm-ecosystem/venv"}

    for f in files:
        if any(part in skip_dirs for part in f.parts):
            continue
        if f.is_file():
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue

            new_text, n = fix_text(text)
            if n > 0:
                f.write_text(new_text, encoding="utf-8")
                print(f"[fixed {n}] {f}")
                total_files += 1
                total_changes += n

    print(f"\n=== Updated {total_files} files, {total_changes} path occurrences removed ===")

if __name__ == "__main__":
    main()