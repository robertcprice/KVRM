"""The ``kvrm`` command — fail-closed action routing for your own domains.

A domain is a plain directory (no Python code required):

    my-domain/
    ├── registry.json        # versioned action registry with support_specs
    ├── train_cases.jsonl    # labeled examples that power the selectors
    ├── cases.jsonl          # (optional) evaluation cases
    ├── kvrm.json            # (optional) tuning overrides
    └── model.joblib         # (optional) trained compact selector

Workflow:
    kvrm init my-domain              # scaffold a small working example
    kvrm validate my-domain          # registry + support specs + case schemas
    kvrm train my-domain             # train the compact learned selector
    kvrm route my-domain -f '{...}'  # route features through the pipeline
    kvrm explain my-domain -f '{..}' # routed decision + factor explanation
    kvrm eval my-domain              # fail-closed metrics over cases.jsonl

The bundled research packs (SOC, SRE, drone, …) live behind ``kvrm demo``
(requires kvrm-bench and the demo packages from a repo checkout).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .context_schema import validate_context_features, validate_context_schema
from .domain_dir import (
    DomainDir,
    DomainDirError,
    _load_jsonl,
    build_domain_runtime,
    decision_input_from_case,
    evaluate_domain,
    load_domain_dir,
    scaffold_domain,
)
from .explainer import DecisionExplainer, render_explanation_text
from .learned import save_compact_model_artifact, train_compact_model
from .registry import RegistryValidationError, validate_registry
from .types import DecisionInput

STRATEGIES = ("hybrid", "rule", "retrieval", "prototype", "semantic", "learned")


def _domain(args: argparse.Namespace) -> DomainDir:
    return load_domain_dir(args.domain_dir)


def _parse_features(raw: str) -> dict:
    try:
        features = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--features is not valid JSON: {exc}")
    if not isinstance(features, dict):
        raise SystemExit("--features must be a JSON object")
    return features


def _print_decision(decision, *, as_json: bool) -> None:
    payload = json.loads(decision.model_dump_json())
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"selected_action : {payload['selected_action_id']}")
    confidence = payload.get("confidence")
    print(f"confidence      : {confidence:.4f}" if confidence is not None else "confidence      : n/a")
    print(f"final_status    : {payload['final_status']}")
    print(f"abstained       : {payload['abstained']}")
    print(f"fallback_used   : {payload['fallback_used']}")
    if payload.get("validation_reason"):
        print(f"validation      : {payload['validation_reason']}")
    execution = payload.get("execution_result") or {}
    if execution:
        print(f"execution       : {execution.get('status')} -> {json.dumps(execution.get('output'))}")
    audit = payload.get("audit_record") or {}
    if audit.get("registry_digest"):
        print(f"registry_digest : {audit['registry_digest'][:16]}…")
    print("\n(--json for the full decision + audit record)")


def cmd_init(args: argparse.Namespace) -> None:
    root = scaffold_domain(args.domain_dir, name=args.name)
    print(f"scaffolded example domain in {root}/")
    print("  registry.json train_cases.jsonl cases.jsonl kvrm.json")
    print(f"next: kvrm validate {root.name}  &&  kvrm eval {root.name}")


def cmd_validate(args: argparse.Namespace) -> None:
    domain = _domain(args)
    problems = 0

    try:
        validate_registry(domain.registry)
        print(f"registry        : OK — {domain.registry.registry_name} "
              f"v{domain.registry.version}, {len(domain.registry.actions)} actions")
    except RegistryValidationError as exc:
        problems += 1
        print(f"registry        : INVALID — {exc}")

    try:
        validate_context_schema(domain.registry.context_schema, domain.registry.required_features)
        print("context_schema  : OK")
    except ValueError as exc:
        problems += 1
        print(f"context_schema  : INVALID — {exc}")

    for label, path in (("train_cases", domain.train_cases_path), ("cases", domain.cases_path)):
        if not path.is_file():
            print(f"{label:<15} : (absent)")
            continue
        cases = _load_jsonl(path)
        action_ids = {action.action_id for action in domain.registry.actions}
        bad = 0
        for index, case in enumerate(cases):
            try:
                validate_context_features(
                    domain.registry.context_schema,
                    domain.registry.required_features,
                    case.get("input_features", {}),
                    path=f"{label}[{index}]",
                )
            except ValueError as exc:
                bad += 1
                if bad <= args.max_errors:
                    print(f"  {exc}")
            expected = case.get("expected_action_id")
            if expected is not None and expected not in action_ids:
                bad += 1
                if bad <= args.max_errors:
                    print(f"  {label}[{index}]: expected_action_id {expected!r} not in registry")
        problems += bad
        status = "OK" if bad == 0 else f"{bad} INVALID"
        print(f"{label:<15} : {status} — {len(cases)} cases")

    if domain.config.fallback_action_id:
        print(f"fallback        : {domain.config.fallback_action_id}")
    else:
        print("fallback        : none configured (will abstain on unsupported inputs); "
              f"set fallback_action_id in kvrm.json")

    if problems:
        raise SystemExit(f"\nvalidation failed: {problems} problem(s)")
    print("\nvalidation passed")


def cmd_train(args: argparse.Namespace) -> None:
    domain = _domain(args)
    train_cases = _load_jsonl(domain.train_cases_path)
    artifact = train_compact_model(train_cases=train_cases, registry=domain.registry)
    out = Path(args.out) if args.out else domain.default_model_path
    save_compact_model_artifact(out, artifact)
    metadata = artifact.get("metadata", {})
    print(f"trained compact selector on {len(train_cases)} cases")
    print(f"train_accuracy  : {metadata.get('train_accuracy', float('nan')):.4f}")
    print(f"model           : {out}")
    print("hybrid routing picks this up automatically (model.joblib in the domain dir)")


def cmd_route(args: argparse.Namespace) -> None:
    domain = _domain(args)
    runtime = build_domain_runtime(
        domain, strategy=args.strategy, model_path=args.model, threshold=args.threshold
    )
    decision = runtime.decide_and_execute(
        DecisionInput(case_id="cli_route", features=_parse_features(args.features))
    )
    _print_decision(decision, as_json=args.json)


def cmd_explain(args: argparse.Namespace) -> None:
    domain = _domain(args)
    runtime = build_domain_runtime(
        domain, strategy=args.strategy, model_path=args.model, threshold=args.threshold
    )
    features = _parse_features(args.features)
    decision = runtime.decide_and_execute(
        DecisionInput(case_id="cli_explain", features=features)
    )
    explainer = DecisionExplainer(domain=domain.config.name, registry=domain.registry)
    explanation = explainer.explain(decision, features)
    if args.json:
        print(explanation.model_dump_json(indent=2))
    else:
        print(render_explanation_text(explanation))


def cmd_eval(args: argparse.Namespace) -> None:
    domain = _domain(args)
    runtime = build_domain_runtime(
        domain, strategy=args.strategy, model_path=args.model, threshold=args.threshold
    )
    cases = _load_jsonl(Path(args.cases)) if args.cases else None
    metrics = evaluate_domain(domain, runtime, cases)
    failures = metrics.pop("failures")
    if args.json:
        metrics["failures"] = failures
        print(json.dumps(metrics, indent=2))
        return
    print(f"domain          : {domain.config.name} ({domain.registry.registry_name} "
          f"v{domain.registry.version}, strategy={args.strategy})")
    print(f"cases           : {metrics['total_cases']} "
          f"({metrics['supported_cases']} supported / {metrics['unsupported_cases']} unsupported)")

    def fmt(value):
        return f"{value:.4f}" if value is not None else "n/a"

    print(f"semantic_correctness_rate       : {fmt(metrics['semantic_correctness_rate'])}")
    print(f"false_accept_rate               : {fmt(metrics['false_accept_rate'])}")
    print(f"unsupported_case_rejection_rate : {fmt(metrics['unsupported_case_rejection_rate'])}")
    print(f"invalid_output_rate             : {fmt(metrics['invalid_output_rate'])}")
    if failures:
        print(f"\nfailures ({len(failures)}):")
        for failure in failures[: args.max_errors]:
            print(f"  {json.dumps(failure)}")
        if len(failures) > args.max_errors:
            print(f"  … {len(failures) - args.max_errors} more (--json for all)")
    else:
        print("\nno failures")


def cmd_demo(args: argparse.Namespace) -> None:
    try:
        from kvrm_bench.cli import main as demo_main
    except ImportError:
        raise SystemExit(
            "kvrm demo requires the research benchmark install:\n"
            "  pip install -e kvrm-bench/  (plus the kvrm-demos packages)\n"
            "from a KVRM repo checkout — https://github.com/robertcprice/KVRM"
        )
    demo_main(args.demo_args)


def _add_runtime_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--strategy", choices=STRATEGIES, default="hybrid")
    parser.add_argument("--model", help="path to a trained compact selector (.joblib)")
    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument("--json", action="store_true", help="full JSON output")


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    # Delegate `kvrm demo …` verbatim before argparse: REMAINDER mis-parses
    # leading option-like tokens (e.g. `kvrm demo --repo-root X case grid`).
    if argv and argv[0] == "demo":
        cmd_demo(argparse.Namespace(demo_args=argv[1:]))
        return

    parser = argparse.ArgumentParser(
        prog="kvrm",
        description="Fail-closed action routing over versioned registries.",
        epilog="docs: https://github.com/robertcprice/KVRM",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="scaffold a new domain directory")
    p_init.add_argument("domain_dir")
    p_init.add_argument("--name", help="registry name (default: directory name)")

    p_validate = sub.add_parser("validate", help="validate registry, support specs, and cases")
    p_validate.add_argument("domain_dir")
    p_validate.add_argument("--max-errors", type=int, default=10)

    p_train = sub.add_parser("train", help="train the compact learned selector")
    p_train.add_argument("domain_dir")
    p_train.add_argument("--out", help="model output path (default: <domain>/model.joblib)")

    p_route = sub.add_parser("route", help="route features through the decision pipeline")
    p_route.add_argument("domain_dir")
    p_route.add_argument("-f", "--features", required=True, help="feature dict as JSON")
    _add_runtime_flags(p_route)

    p_explain = sub.add_parser("explain", help="route and explain a decision")
    p_explain.add_argument("domain_dir")
    p_explain.add_argument("-f", "--features", required=True, help="feature dict as JSON")
    _add_runtime_flags(p_explain)

    p_eval = sub.add_parser("eval", help="fail-closed metrics over evaluation cases")
    p_eval.add_argument("domain_dir")
    p_eval.add_argument("--cases", help="cases file (default: <domain>/cases.jsonl)")
    p_eval.add_argument("--max-errors", type=int, default=10)
    _add_runtime_flags(p_eval)

    p_demo = sub.add_parser(
        "demo", help="bundled research packs (requires kvrm-bench)", add_help=False
    )
    p_demo.add_argument("demo_args", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)
    try:
        {
            "init": cmd_init,
            "validate": cmd_validate,
            "train": cmd_train,
            "route": cmd_route,
            "explain": cmd_explain,
            "eval": cmd_eval,
            "demo": cmd_demo,
        }[args.command](args)
    except DomainDirError as exc:
        raise SystemExit(f"error: {exc}")


if __name__ == "__main__":
    main()
