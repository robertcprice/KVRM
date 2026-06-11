"""Run full KVRM benchmark across all 3 domains with all selector variants."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent  # repo root (this script lives in scripts/)


def build_domains(base: Path, eval_filename: str) -> dict[str, dict[str, Path | str]]:
    return {
        "soc": {
            "registry": base / "kvrm-demos/soc-playbook-router/data/registry.json",
            "train_cases": base / "kvrm-demos/soc-playbook-router/data/train_cases.jsonl",
            "cases": base / f"kvrm-demos/soc-playbook-router/data/{eval_filename}",
            "selectors_module": "soc_playbook_router.selectors",
            "executor_module": "soc_playbook_router.executor",
            "fallback_action_id": "request_human_triage",
        },
        "sre": {
            "registry": base / "kvrm-demos/sre-policy-router/data/registry.json",
            "train_cases": base / "kvrm-demos/sre-policy-router/data/train_cases.jsonl",
            "cases": base / f"kvrm-demos/sre-policy-router/data/{eval_filename}",
            "selectors_module": "sre_policy_router.selectors",
            "executor_module": "sre_policy_router.executor",
            "fallback_action_id": "page_human_operator",
        },
        "drone": {
            "registry": base / "kvrm-demos/drone-mission-router/data/registry.json",
            "train_cases": base / "kvrm-demos/drone-mission-router/data/train_cases.jsonl",
            "cases": base / f"kvrm-demos/drone-mission-router/data/{eval_filename}",
            "selectors_module": "drone_mission_router.selectors",
            "executor_module": "drone_mission_router.executor",
            "fallback_action_id": "manual_handoff",
        },
    }

def load_cases(path: Path) -> list[dict]:
    cases = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def run_selector_on_cases(
    selector,
    registry,
    validator,
    executor,
    cases,
    label: str,
    *,
    threshold: float,
    fallback_action_id: str | None,
) -> list[dict]:
    """Run a single selector variant over all cases and return result dicts."""
    from kvrm_core.runtime import KVRMRuntime
    from kvrm_core.types import DecisionInput

    rt = KVRMRuntime(
        registry=registry,
        selector=selector,
        validator=validator,
        executor=executor,
        threshold=threshold,
        fallback_action_id=fallback_action_id,
    )
    results = []
    for case in cases:
        di = DecisionInput(
            case_id=case["case_id"],
            features=case["input_features"],
            supported=case.get("supported", True),
            ood=case.get("ood", False),
            expected_action_id=case.get("expected_action_id"),
        )
        dr = rt.decide_and_execute(di)
        results.append({
            "case_id": dr.case_id,
            "selected_action_id": dr.selected_action_id,
            "expected_action_id": case.get("expected_action_id"),
            "confidence": dr.confidence,
            "valid": dr.valid,
            "correct": dr.correct,
            "abstained": dr.abstained,
            "fallback_used": dr.fallback_used,
            "final_status": dr.final_status.value,
            "latency_ms": dr.latency_ms,
            "supported": case.get("supported", True),
            "ood": case.get("ood", False),
            "source": dr.audit_record.candidate_scores[0]["source"] if dr.audit_record.candidate_scores else "none",
        })
    return results


def print_metrics(metrics: dict, label: str):
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    print(f"  Total cases:              {metrics['total_cases']}")
    print(f"  Supported / Unsupported:  {metrics['supported_cases']} / {metrics['unsupported_cases']}")
    print(f"  Structural validity:      {metrics['structural_validity_rate']:.4f}")
    print(f"  Semantic correctness:     {metrics['semantic_correctness_rate']:.4f}")
    print(f"  False accept rate:        {metrics['false_accept_rate']:.4f}")
    print(f"  Unsupported rejection:    {metrics['unsupported_case_rejection_rate']:.4f}")
    print(f"  Abstention rate:          {metrics['abstention_rate']:.4f}")
    print(f"  OOD accuracy (supported): {metrics['ood_accuracy_supported_only']:.4f}")
    print(f"  Calibration ECE:          {metrics['calibration_ece']:.4f}")
    print(f"  Latency p50/p95/p99:      {metrics['latency_p50_ms']:.3f} / {metrics['latency_p95_ms']:.3f} / {metrics['latency_p99_ms']:.3f} ms")

    # CIs if present
    for key in sorted(metrics.keys()):
        if key.endswith("_ci") and isinstance(metrics[key], dict):
            ci = metrics[key]
            short = key.replace("_ci", "")
            print(f"  {short}: {ci['rate']:.4f}  CI({ci['ci_lower']:.4f}, {ci['ci_upper']:.4f})  n={ci['n']}")


# ── main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--eval-filename",
        default="cases_v2.jsonl",
        help="Evaluation JSONL filename under each domain data directory.",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=10_000,
        help="Bootstrap resamples for hybrid confidence intervals.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.60,
        help="Runtime confidence threshold before abstention/fallback.",
    )
    parser.add_argument(
        "--strict-no-fallback",
        action="store_true",
        help="Disable domain fallback actions and keep strict abstention semantics.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    base = BASE_DIR
    domains = build_domains(base, args.eval_filename)

    from kvrm_core.registry import load_registry
    from kvrm_core.validation import DeterministicValidator
    from kvrm_bench.metrics import compute_metrics_with_ci, bootstrap_metrics

    all_results = {}

    for domain_name, cfg in domains.items():
        print(f"\n{'#'*70}")
        print(f"# DOMAIN: {domain_name.upper()}")
        print(f"{'#'*70}")

        registry = load_registry(str(cfg["registry"]))
        validator = DeterministicValidator(registry)

        import importlib
        sel_mod = importlib.import_module(cfg["selectors_module"])
        exe_mod = importlib.import_module(cfg["executor_module"])
        executor = exe_mod.build_executor()

        cases = load_cases(cfg["cases"])
        train_cases = load_cases(cfg["train_cases"])
        fallback_action_id = None if args.strict_no_fallback else cfg["fallback_action_id"]
        print(f"Loaded {len(cases)} cases ({sum(1 for c in cases if c.get('supported', True))} supported, "
              f"{sum(1 for c in cases if not c.get('supported', True))} unsupported)")
        print(f"Using {len(train_cases)} train support cases for retrieval/prototype selectors")
        print(f"Runtime threshold={args.threshold:.2f} fallback={fallback_action_id!r}")

        # ── variant 1: rule-only ─────────────────────────────────────────
        rule_sel = sel_mod.build_rule_selector()
        rule_results = run_selector_on_cases(
            rule_sel,
            registry,
            validator,
            executor,
            cases,
            "rule-only",
            threshold=args.threshold,
            fallback_action_id=fallback_action_id,
        )
        rule_m = compute_metrics_with_ci(rule_results)
        print_metrics(rule_m, f"{domain_name} / rule-only")

        # ── variant 2: retrieval-only ────────────────────────────────────
        retr_sel = sel_mod.build_retrieval_selector(str(cfg["train_cases"]))
        retr_results = run_selector_on_cases(
            retr_sel,
            registry,
            validator,
            executor,
            cases,
            "retrieval-only",
            threshold=args.threshold,
            fallback_action_id=fallback_action_id,
        )
        retr_m = compute_metrics_with_ci(retr_results)
        print_metrics(retr_m, f"{domain_name} / retrieval-only")

        # ── variant 3: prototype-only ────────────────────────────────────
        proto_sel = sel_mod.build_prototype_selector(str(cfg["train_cases"]))
        proto_results = run_selector_on_cases(
            proto_sel,
            registry,
            validator,
            executor,
            cases,
            "prototype-only",
            threshold=args.threshold,
            fallback_action_id=fallback_action_id,
        )
        proto_m = compute_metrics_with_ci(proto_results)
        print_metrics(proto_m, f"{domain_name} / prototype-only")

        # ── variant 4: hybrid (full KVRM) ────────────────────────────────
        hybrid_sel = sel_mod.build_hybrid_selector(str(cfg["train_cases"]))
        hybrid_results = run_selector_on_cases(
            hybrid_sel,
            registry,
            validator,
            executor,
            cases,
            "hybrid",
            threshold=args.threshold,
            fallback_action_id=fallback_action_id,
        )
        hybrid_m = compute_metrics_with_ci(hybrid_results)
        hybrid_m_bootstrap = bootstrap_metrics(hybrid_results, n_bootstrap=args.bootstrap_samples)
        print_metrics(hybrid_m, f"{domain_name} / hybrid (full KVRM)")

        # ── ablation: no validator ───────────────────────────────────────
        no_op_validator = DeterministicValidator(registry)
        no_op_validator.validate = lambda c: __import__("kvrm_core.types", fromlist=["ValidationResult"]).ValidationResult(valid=True, reason=None)
        hybrid_no_val = sel_mod.build_hybrid_selector(str(cfg["train_cases"]))
        noval_results = run_selector_on_cases(
            hybrid_no_val,
            registry,
            no_op_validator,
            executor,
            cases,
            "hybrid-no-validator",
            threshold=args.threshold,
            fallback_action_id=fallback_action_id,
        )
        noval_m = compute_metrics_with_ci(noval_results)
        print_metrics(noval_m, f"{domain_name} / hybrid no-validator (ablation)")

        all_results[domain_name] = {
            "rule": {"metrics": rule_m, "results": rule_results},
            "retrieval": {"metrics": retr_m, "results": retr_results},
            "prototype": {"metrics": proto_m, "results": proto_results},
            "hybrid": {"metrics": hybrid_m, "results": hybrid_results},
            "hybrid_bootstrap": hybrid_m_bootstrap,
            "hybrid_no_validator": {"metrics": noval_m},
        }

    # ── cross-domain summary ─────────────────────────────────────────────
    print(f"\n{'#'*70}")
    print("# CROSS-DOMAIN SUMMARY")
    print(f"{'#'*70}")
    print(f"{'Domain':<10} {'Variant':<22} {'Validity':>10} {'Correct':>10} {'FalseAcc':>10} {'Reject':>10} {'ECE':>8}")
    print("-" * 80)
    for domain_name, data in all_results.items():
        for variant in ["rule", "retrieval", "prototype", "hybrid", "hybrid_no_validator"]:
            m = data[variant]["metrics"]
            label = variant if variant != "hybrid_no_validator" else "hybrid-no-val"
            print(f"{domain_name:<10} {label:<22} {m['structural_validity_rate']:>10.4f} {m['semantic_correctness_rate']:>10.4f} {m['false_accept_rate']:>10.4f} {m['unsupported_case_rejection_rate']:>10.4f} {m['calibration_ece']:>8.4f}")
        print()

    # ── save JSON results ────────────────────────────────────────────────
    output = {}
    for domain_name, data in all_results.items():
        output[domain_name] = {}
        for variant in ["rule", "retrieval", "prototype", "hybrid", "hybrid_no_validator"]:
            m = data[variant]["metrics"]
            # strip non-serializable bootstrap tuples
            clean = {}
            for k, v in m.items():
                if isinstance(v, tuple):
                    clean[k] = list(v)
                else:
                    clean[k] = v
            output[domain_name][variant] = {"metrics": clean}
            if "results" in data[variant]:
                output[domain_name][variant]["per_case"] = data[variant]["results"]

    out_path = base / "kvrm-bench" / "results" / f"full_benchmark_results_{args.eval_filename.replace('.jsonl', '')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}")

    # ── bootstrap CIs for hybrid ─────────────────────────────────────────
    print(f"\n{'#'*70}")
    print(f"# BOOTSTRAP 95% CIs FOR HYBRID ({args.bootstrap_samples:,} resamples)")
    print(f"{'#'*70}")
    rate_keys = [
        'structural_validity_rate', 'semantic_correctness_rate',
        'false_accept_rate', 'unsupported_case_rejection_rate',
        'abstention_rate', 'ood_accuracy_supported_only',
    ]
    print(f"{'Domain':<10} {'Metric':<35} {'Point':>8} {'CI_lo':>8} {'CI_hi':>8}")
    print("-" * 75)
    for domain_name, data in all_results.items():
        bm = data.get("hybrid_bootstrap", {})
        for k in rate_keys:
            point = bm.get(k, 0)
            ci = bm.get(f"{k}_bootstrap_ci", (0, 0))
            print(f"{domain_name:<10} {k:<35} {point:>8.4f} {ci[0]:>8.4f} {ci[1]:>8.4f}")
        print()


if __name__ == "__main__":
    main()
