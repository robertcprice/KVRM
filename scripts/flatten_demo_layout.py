#!/usr/bin/env python3
"""
One-time refactoring script: Flatten the redundant src/ layout in all KVRM domain demos.

Before (hated structure):
    kvrm-demos/sre-policy-router/
      src/
        sre_policy_router/
          __init__.py
          selectors.py
          executor.py
      pyproject.toml   # where = ["src"]

After (clean):
    kvrm-demos/sre-policy-router/
      sre_policy_router/
        __init__.py
        selectors.py
        executor.py
      pyproject.toml   # where = ["."]

This removes one pointless level of nesting that the user correctly called out as terrible.
Only affects the 12 small domain demo packages. kvrm-core and kvrm-bench keep their src/ layout
because they are real reusable libraries.
"""

from pathlib import Path
import shutil
import sys

DEMO_ROOT = Path("kvrm-demos")

# All the known demo package directories (kebab-case on disk)
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

def flatten_one_demo(demo_name: str) -> bool:
    demo_dir = DEMO_ROOT / demo_name
    src_dir = demo_dir / "src"

    if not src_dir.exists():
        print(f"  [skip] {demo_name}: no src/ directory")
        return False

    # Find the single inner package directory
    children = [p for p in src_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
    if len(children) != 1:
        print(f"  [ERROR] {demo_name}: expected exactly one package under src/, found {children}")
        return False

    inner_pkg = children[0]
    target = demo_dir / inner_pkg.name

    if target.exists():
        print(f"  [ERROR] {demo_name}: target {target} already exists — aborting to avoid overwrite")
        return False

    # Move the package up
    shutil.move(str(inner_pkg), str(target))
    print(f"  [moved] {inner_pkg} -> {target}")

    # Remove the now-empty src/ directory
    try:
        src_dir.rmdir()
        print(f"  [removed] {src_dir}")
    except OSError as e:
        print(f"  [warn] could not remove {src_dir}: {e}")

    # Update pyproject.toml
    pyproject = demo_dir / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text()
        if 'where = ["src"]' in text:
            text = text.replace('where = ["src"]', 'where = ["."]')
            pyproject.write_text(text)
            print(f"  [updated] {pyproject} (where = [\".\"])")
        else:
            print(f"  [note] {pyproject} did not contain where = [\"src\"]")

    # Clean up misplaced egg-info if it ended up at the wrong level
    for egg in demo_dir.glob("*.egg-info"):
        if egg.is_dir():
            print(f"  [cleanup] removing stale egg-info at wrong level: {egg}")
            shutil.rmtree(egg, ignore_errors=True)

    return True

def main():
    print("=== Flattening redundant src/ layout in all KVRM domain demos ===\n")
    changed = 0
    for demo in DEMOS:
        print(f"Processing {demo}...")
        if flatten_one_demo(demo):
            changed += 1
        print()

    print(f"\n=== Done. Flattened {changed} demos. ===")
    print("Next steps:")
    print("  1. Update all PYTHONPATH strings that still contain /src/ for these demos")
    print("  2. Re-run tests + py_compile to verify")
    print("  3. Delete this script (scripts/flatten_demo_layout.py) after verification")

if __name__ == "__main__":
    main()