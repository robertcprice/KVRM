"""Command-line entry point for exploring KVRM domains interactively.

Installed as the ``kvrm`` console script. All commands run against a repo
checkout (the domain data files live in ``kvrm-demos/``), auto-detected by
walking up from the current directory.

Commands:
    kvrm domains                      List available domains with case counts.
    kvrm actions <domain>             List a domain's registered actions.
    kvrm case <domain> [-i N]         Route eval case N through the hybrid pipeline.
    kvrm case <domain> --matrix       Compare every selector strategy on one case.
    kvrm route <domain> -f '{...}'    Route custom feature JSON through the pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kvrm_core import DecisionInput, load_registry

from .demo import (
    DOMAIN_CONFIG,
    _cached_runtime_for_strategy,
    load_cases,
    run_demo_case,
    run_demo_case_matrix,
)


def find_repo_root(explicit: str | None = None) -> Path:
    if explicit:
        root = Path(explicit).resolve()
        if not (root / "kvrm-demos").is_dir():
            raise SystemExit(f"--repo-root {root} has no kvrm-demos/ directory")
        return root
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "kvrm-demos").is_dir():
            return candidate
    raise SystemExit(
        "could not find a KVRM checkout (no kvrm-demos/ in cwd or parents); "
        "run from inside the repo or pass --repo-root"
    )


def _registry_for(root: Path, domain: str):
    data_dir = root / DOMAIN_CONFIG[domain]["data_dir"]
    return load_registry(data_dir / "registry.json")


def cmd_domains(args: argparse.Namespace) -> None:
    root = find_repo_root(args.repo_root)
    rows = []
    for domain, config in sorted(DOMAIN_CONFIG.items()):
        data_dir = root / config["data_dir"]
        try:
            registry = load_registry(data_dir / "registry.json")
            cases = load_cases(data_dir / "cases.jsonl")
            rows.append((domain, registry.version, len(registry.actions), len(cases)))
        except FileNotFoundError:
            rows.append((domain, "missing", 0, 0))
    width = max(len(r[0]) for r in rows)
    print(f"{'domain':<{width}}  version  actions  eval cases")
    for domain, version, actions, cases in rows:
        print(f"{domain:<{width}}  {version:<7}  {actions:>7}  {cases:>10}")


def cmd_actions(args: argparse.Namespace) -> None:
    root = find_repo_root(args.repo_root)
    registry = _registry_for(root, args.domain)
    print(f"{registry.registry_name} v{registry.version} — {len(registry.actions)} actions")
    for action in registry.actions:
        leaf_count = _count_leaves(action.support_spec)
        print(f"  {action.action_id:<32} {leaf_count:>2} support constraints — {action.description}")


def _count_leaves(spec: dict) -> int:
    if not spec:
        return 0
    if "feature" in spec:
        return 1
    total = 0
    for key in ("all", "any"):
        for child in spec.get(key, []):
            total += _count_leaves(child)
    if "not" in spec:
        total += _count_leaves(spec["not"])
    return total


def cmd_case(args: argparse.Namespace) -> None:
    root = find_repo_root(args.repo_root)
    runner = run_demo_case_matrix if args.matrix else run_demo_case
    result = runner(
        repo_root=root,
        domain=args.domain,
        eval_filename=args.eval_file,
        case_index=args.index,
        threshold=args.threshold,
    )
    _emit(result, args)


def cmd_route(args: argparse.Namespace) -> None:
    root = find_repo_root(args.repo_root)
    try:
        features = json.loads(args.features)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--features is not valid JSON: {exc}")
    runtime, _ = _cached_runtime_for_strategy(
        str(root), args.domain, args.eval_file, "hybrid", None, args.threshold
    )
    if runtime is None:
        raise SystemExit(f"hybrid selector unavailable for {args.domain}")
    decision = runtime.decide_and_execute(
        DecisionInput(case_id="cli_route", features=features)
    )
    _emit(json.loads(decision.model_dump_json()), args)


def _emit(payload: dict, args: argparse.Namespace) -> None:
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    decision = payload.get("decision", payload)
    print(f"selected_action : {decision.get('selected_action_id')}")
    print(f"confidence      : {decision.get('confidence'):.4f}" if decision.get("confidence") is not None else "confidence      : n/a")
    print(f"final_status    : {decision.get('final_status')}")
    print(f"abstained       : {decision.get('abstained')}")
    print(f"fallback_used   : {decision.get('fallback_used')}")
    if decision.get("validation_reason"):
        print(f"validation      : {decision['validation_reason']}")
    execution = decision.get("execution_result") or {}
    if execution:
        print(f"execution       : {execution.get('status')} -> {json.dumps(execution.get('output'))}")
    audit = decision.get("audit_record") or {}
    if audit.get("registry_digest"):
        print(f"registry_digest : {audit['registry_digest'][:16]}…")
    if "strategy_results" in payload:
        print("\nstrategy comparison:")
        for entry in payload["strategy_results"]:
            inner = entry.get("decision", {})
            print(
                f"  {entry.get('strategy', '?'):<12} -> {inner.get('selected_action_id')} "
                f"(status={inner.get('final_status')})"
            )
    print("\n(use --json for the full decision + audit record)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="kvrm", description=__doc__.split("\n")[0])
    parser.add_argument("--repo-root", help="path to a KVRM checkout (default: auto-detect)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("domains", help="list available domains")

    p_actions = sub.add_parser("actions", help="list a domain's registered actions")
    p_actions.add_argument("domain", choices=sorted(DOMAIN_CONFIG))

    p_case = sub.add_parser("case", help="route one eval case through the pipeline")
    p_case.add_argument("domain", choices=sorted(DOMAIN_CONFIG))
    p_case.add_argument("-i", "--index", type=int, default=0, help="eval case index (default 0)")
    p_case.add_argument("--matrix", action="store_true", help="compare all selector strategies")
    p_case.add_argument("--eval-file", default="cases.jsonl")
    p_case.add_argument("--threshold", type=float, default=0.60)
    p_case.add_argument("--json", action="store_true", help="print full JSON payload")

    p_route = sub.add_parser("route", help="route custom features through the pipeline")
    p_route.add_argument("domain", choices=sorted(DOMAIN_CONFIG))
    p_route.add_argument("-f", "--features", required=True, help="feature dict as JSON")
    p_route.add_argument("--eval-file", default="cases.jsonl")
    p_route.add_argument("--threshold", type=float, default=0.60)
    p_route.add_argument("--json", action="store_true", help="print full JSON payload")

    args = parser.parse_args(argv)
    {
        "domains": cmd_domains,
        "actions": cmd_actions,
        "case": cmd_case,
        "route": cmd_route,
    }[args.command](args)


if __name__ == "__main__":
    main()
