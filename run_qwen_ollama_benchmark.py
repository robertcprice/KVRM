"""Run actual local Ollama Qwen baselines on the KVRM routing datasets."""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
ABSTAIN_SENTINEL = "ABSTAIN"

LABEL_ONLY_SCHEMA = {
    "type": "object",
    "properties": {
        "action_id": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["action_id", "confidence"],
    "additionalProperties": False,
}

ABSTAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["action", "abstain"]},
        "action_id": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["decision", "action_id", "confidence"],
    "additionalProperties": False,
}


def build_domains(base: Path, eval_filename: str) -> dict[str, dict[str, Path]]:
    return {
        "soc": {
            "registry": base / "kvrm-demos/soc-playbook-router/data/registry.json",
            "train_cases": base / "kvrm-demos/soc-playbook-router/data/train_cases.jsonl",
            "cases": base / f"kvrm-demos/soc-playbook-router/data/{eval_filename}",
        },
        "sre": {
            "registry": base / "kvrm-demos/sre-policy-router/data/registry.json",
            "train_cases": base / "kvrm-demos/sre-policy-router/data/train_cases.jsonl",
            "cases": base / f"kvrm-demos/sre-policy-router/data/{eval_filename}",
        },
        "drone": {
            "registry": base / "kvrm-demos/drone-mission-router/data/registry.json",
            "train_cases": base / "kvrm-demos/drone-mission-router/data/train_cases.jsonl",
            "cases": base / f"kvrm-demos/drone-mission-router/data/{eval_filename}",
        },
    }


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_registry(path: Path) -> dict:
    return json.loads(path.read_text())


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def clamp_confidence(value: Any, default: float = 0.5) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        conf = default
    return max(0.0, min(1.0, conf))


def parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}


def action_catalog(registry: dict) -> list[dict]:
    return registry.get("actions", [])


def example_block(train_cases: list[dict]) -> str:
    lines = []
    for case in train_cases:
        features = json.dumps(case["input_features"], sort_keys=True)
        lines.append(f"- {features} -> {case['expected_action_id']}")
    return "\n".join(lines)


def action_block(registry: dict) -> str:
    lines = []
    for action in action_catalog(registry):
        lines.append(f"- {action['action_id']}: {action.get('description', '').strip()}")
    return "\n".join(lines)


def feature_key_block(train_cases: list[dict]) -> str:
    keys = sorted({key for case in train_cases for key in case.get("input_features", {})})
    return ", ".join(keys)


def build_system_prompt(domain: str, registry: dict, train_cases: list[dict], variant: str) -> str:
    shared = (
        f"You are benchmarking a small language model as a finite action router for the {domain} domain.\n"
        "You must use only the structured input features, allowed actions, and training examples below.\n"
        "Never invent action ids.\n"
        "If values are malformed, unsupported, or require a compound remediation not represented by one action, treat that as unsupported.\n"
        f"Expected feature keys: {feature_key_block(train_cases)}\n"
        "Allowed actions:\n"
        f"{action_block(registry)}\n"
        "Training examples:\n"
        f"{example_block(train_cases)}\n"
    )
    if variant == "label_only":
        return (
            shared
            + "Return the single best action_id from the allowed set.\n"
            + "Return JSON only.\n"
        )
    return (
        shared
        + "You may either choose one allowed action or abstain.\n"
        + "Abstain when the case is malformed, unsupported, ambiguous, or outside the audited envelope shown by the examples.\n"
        + f'If you abstain, set action_id to "{ABSTAIN_SENTINEL}".\n'
        + "If you choose an action, action_id must be one allowed action id exactly.\n"
        + "Do not put the action label in the reason field.\n"
        + "Return JSON only.\n"
    )


def build_user_prompt(case: dict, variant: str) -> str:
    payload = json.dumps(case["input_features"], sort_keys=True)
    if variant == "label_only":
        return (
            f"Case ID: {case['case_id']}\n"
            f"Input features: {payload}\n"
            'Return {"action_id":"...", "confidence":0.0-1.0, "reason":"optional short note"}'
        )
    return (
        f"Case ID: {case['case_id']}\n"
        f"Input features: {payload}\n"
        f'Return {{"decision":"action"|"abstain", "action_id":"allowed_action_id|{ABSTAIN_SENTINEL}", "confidence":0.0-1.0, "reason":"optional short note"}}'
    )


def ollama_generate(model: str, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "format": schema,
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "top_p": 0.1,
            "seed": 42,
            "num_predict": 96,
        },
    }
    started = time.perf_counter()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        raw = json.loads(response.read().decode())
    raw["wall_latency_ms"] = (time.perf_counter() - started) * 1000
    return raw


def evaluate_case(
    *,
    model: str,
    domain: str,
    registry: dict,
    train_cases: list[dict],
    case: dict,
    variant: str,
) -> dict[str, Any]:
    allowed_action_ids = {action["action_id"] for action in action_catalog(registry)}
    schema = LABEL_ONLY_SCHEMA if variant == "label_only" else ABSTAIN_SCHEMA
    system = build_system_prompt(domain, registry, train_cases, variant)
    prompt = build_user_prompt(case, variant)
    raw = ollama_generate(model=model, system=system, prompt=prompt, schema=schema)
    payload = parse_json_response(raw.get("response", ""))

    reason = payload.get("reason")
    action_id: str | None = None
    abstained = False
    if variant == "label_only":
        action_id = payload.get("action_id")
        if not action_id and isinstance(reason, str) and reason in allowed_action_ids:
            action_id = reason
    else:
        proposed_action_id = payload.get("action_id")
        if not proposed_action_id and isinstance(reason, str) and reason in allowed_action_ids:
            proposed_action_id = reason
        if payload.get("decision") == "abstain" or proposed_action_id == ABSTAIN_SENTINEL:
            abstained = True
        else:
            action_id = proposed_action_id

    valid = True
    if action_id is not None and action_id not in allowed_action_ids:
        valid = False
    if not abstained and action_id is None:
        valid = False

    confidence = clamp_confidence(payload.get("confidence"), default=0.5 if not abstained else 0.0)
    expected_action_id = case.get("expected_action_id")
    supported = case.get("supported", True)
    correct = bool(supported and action_id == expected_action_id)

    if abstained:
        final_status = "abstained"
    else:
        final_status = "executed"

    latency_ms = float(raw.get("total_duration", 0)) / 1_000_000
    if latency_ms <= 0:
        latency_ms = float(raw.get("wall_latency_ms", 0.0))

    return {
        "case_id": case["case_id"],
        "selected_action_id": action_id,
        "expected_action_id": expected_action_id,
        "confidence": confidence,
        "valid": valid,
        "correct": correct,
        "abstained": abstained,
        "fallback_used": False,
        "final_status": final_status,
        "latency_ms": latency_ms,
        "supported": supported,
        "ood": case.get("ood", False),
        "source": f"ollama:{model}:{variant}",
        "model": model,
        "variant": variant,
        "reason": payload.get("reason"),
        "raw_response": raw.get("response", ""),
    }


def write_summary(
    *,
    output_dir: Path,
    domain: str,
    model: str,
    variant: str,
    eval_filename: str,
    metrics: dict[str, Any],
) -> None:
    lines = [
        f"# {domain.upper()} / {model} / {variant}",
        "",
        f"- Eval set: `{eval_filename}`",
        f"- Structural validity: {metrics['structural_validity_rate']:.4f}",
        f"- Semantic correctness: {metrics['semantic_correctness_rate']:.4f}",
        f"- False accept rate: {metrics['false_accept_rate']:.4f}",
        f"- Unsupported rejection: {metrics['unsupported_case_rejection_rate']:.4f}",
        f"- Abstention rate: {metrics['abstention_rate']:.4f}",
        f"- OOD supported accuracy: {metrics['ood_accuracy_supported_only']:.4f}",
        f"- ECE: {metrics['calibration_ece']:.4f}",
        f"- Latency p50/p95/p99 ms: {metrics['latency_p50_ms']:.1f} / {metrics['latency_p95_ms']:.1f} / {metrics['latency_p99_ms']:.1f}",
    ]
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="+",
        default=["qwen3:0.6b", "qwen3:1.7b"],
        help="Ollama models to benchmark.",
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=["label_only", "abstain_json"],
        default=["abstain_json"],
        help="Prompting variants to run.",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        choices=["soc", "sre", "drone"],
        default=["soc", "sre", "drone"],
        help="Domains to evaluate.",
    )
    parser.add_argument(
        "--eval-filename",
        default="cases_v2.jsonl",
        help="Evaluation JSONL filename under each domain data directory.",
    )
    parser.add_argument(
        "--output-root",
        default=str(BASE_DIR / "baselines" / "qwen-baseline" / "outputs" / "ollama"),
        help="Root directory for artifacts.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of eval cases per domain for smoke tests.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Discard cached per-case results and rerun all requests.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from kvrm_bench.metrics import compute_metrics_with_ci

    eval_stem = args.eval_filename.replace(".jsonl", "")
    output_root = Path(args.output_root) / eval_stem
    domains = build_domains(BASE_DIR, args.eval_filename)

    combined_metrics: dict[str, dict[str, dict[str, Any]]] = {}

    for domain in args.domains:
        cfg = domains[domain]
        registry = load_registry(cfg["registry"])
        train_cases = load_jsonl(cfg["train_cases"])
        eval_cases = load_jsonl(cfg["cases"])
        if args.limit:
            eval_cases = eval_cases[: args.limit]

        domain_metrics: dict[str, dict[str, Any]] = {}
        for model in args.models:
            for variant in args.variants:
                variant_key = f"{model}:{variant}"
                output_dir = output_root / domain / model.replace(":", "_") / variant
                output_dir.mkdir(parents=True, exist_ok=True)
                result_path = output_dir / "per_case_results.jsonl"

                existing: dict[str, dict[str, Any]] = {}
                if result_path.exists() and not args.overwrite:
                    for row in load_jsonl(result_path):
                        existing[row["case_id"]] = row

                rows: list[dict[str, Any]] = []
                updated = False
                for idx, case in enumerate(eval_cases, start=1):
                    cached = existing.get(case["case_id"])
                    if cached is not None:
                        rows.append(cached)
                        continue
                    try:
                        row = evaluate_case(
                            model=model,
                            domain=domain,
                            registry=registry,
                            train_cases=train_cases,
                            case=case,
                            variant=variant,
                        )
                    except urllib.error.URLError as exc:
                        raise SystemExit(f"Ollama request failed for {model} {domain} {variant}: {exc}") from exc
                    rows.append(row)
                    updated = True
                    if idx % 10 == 0 or idx == len(eval_cases):
                        print(f"{domain}/{model}/{variant}: {idx}/{len(eval_cases)} cases")
                        dump_jsonl(result_path, rows)

                if updated or not result_path.exists():
                    dump_jsonl(result_path, rows)

                metrics = compute_metrics_with_ci(rows)
                config = {
                    "domain": domain,
                    "model": model,
                    "variant": variant,
                    "eval_filename": args.eval_filename,
                    "train_cases": len(train_cases),
                    "eval_cases": len(eval_cases),
                }
                (output_dir / "config.json").write_text(json.dumps(config, indent=2))
                (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
                write_summary(
                    output_dir=output_dir,
                    domain=domain,
                    model=model,
                    variant=variant,
                    eval_filename=args.eval_filename,
                    metrics=metrics,
                )
                domain_metrics[variant_key] = metrics
                print(
                    f"{domain}/{model}/{variant}: "
                    f"semantic_correctness={metrics['semantic_correctness_rate']:.3f} "
                    f"false_accept={metrics['false_accept_rate']:.3f} "
                    f"unsupported_rejection={metrics['unsupported_case_rejection_rate']:.3f}"
                )
        combined_metrics[domain] = domain_metrics

    combined_path = output_root / "combined_metrics.json"
    combined_path.write_text(json.dumps(combined_metrics, indent=2))
    print(f"Saved combined metrics to {combined_path}")


if __name__ == "__main__":
    main()
