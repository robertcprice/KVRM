#!/usr/bin/env python3
"""
Evaluation script for Rate Limiter KVRM.

Compares KVRM against baseline rate limiters on various scenarios.
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Optional

import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model import RateLimiterKVRM, RateLimiterKVRMLite
from src.tokenizer import RateLimiterTokenizer
from src.inference import RateLimiterInference
from src.baseline import TokenBucketLimiter, SlidingWindowLimiter, RuleBasedLimiter
from src.schemas import Action
from data.generator import RateLimitDataGenerator


def evaluate_on_scenarios(
    kvrm_engine: RateLimiterInference,
    n_samples: int = 1000,
    seed: int = 42,
) -> dict:
    """Evaluate KVRM and baselines on generated scenarios."""

    generator = RateLimitDataGenerator(seed=seed)

    # Initialize baselines
    baselines = {
        "token_bucket": TokenBucketLimiter(),
        "sliding_window": SlidingWindowLimiter(),
        "rule_based": RuleBasedLimiter(),
    }

    # Track results by scenario type
    results = {
        "kvrm": defaultdict(lambda: {"correct": 0, "total": 0, "actions": defaultdict(int)}),
        "token_bucket": defaultdict(lambda: {"correct": 0, "total": 0, "actions": defaultdict(int)}),
        "sliding_window": defaultdict(lambda: {"correct": 0, "total": 0, "actions": defaultdict(int)}),
        "rule_based": defaultdict(lambda: {"correct": 0, "total": 0, "actions": defaultdict(int)}),
    }

    # Scenario weights for tracking
    scenario_counts = defaultdict(int)

    print(f"\nEvaluating on {n_samples} samples...")

    for i, (input_data, ground_truth) in enumerate(generator.generate(n_samples)):
        if i >= n_samples:
            break

        # Determine scenario type from input characteristics
        scenario = _classify_scenario(input_data)
        scenario_counts[scenario] += 1

        # Get KVRM prediction
        kvrm_output = kvrm_engine.predict(input_data)

        # Get baseline predictions
        baseline_outputs = {
            name: limiter.check(input_data)
            for name, limiter in baselines.items()
        }

        # Compare to ground truth
        gt_action = ground_truth.action

        # KVRM accuracy
        kvrm_correct = _action_matches(kvrm_output.action, gt_action)
        results["kvrm"][scenario]["total"] += 1
        results["kvrm"][scenario]["actions"][kvrm_output.action.value] += 1
        if kvrm_correct:
            results["kvrm"][scenario]["correct"] += 1

        # Baseline accuracies
        for name, output in baseline_outputs.items():
            correct = _action_matches(output.action, gt_action)
            results[name][scenario]["total"] += 1
            results[name][scenario]["actions"][output.action.value] += 1
            if correct:
                results[name][scenario]["correct"] += 1

        # Progress
        if (i + 1) % 200 == 0:
            print(f"  Processed {i+1}/{n_samples} samples")

    return dict(results), dict(scenario_counts)


def _classify_scenario(input_data) -> str:
    """Classify input into a scenario type."""
    if input_data.patterns.credential_stuffing_pattern:
        return "credential_stuffing"
    elif input_data.patterns.scraping_pattern:
        return "scraping"
    elif input_data.system.current_load > 0.85:
        return "system_overload"
    elif input_data.patterns.burst_detected:
        if input_data.user.account_age_days > 90:
            return "legitimate_burst"
        else:
            return "suspicious_burst"
    elif input_data.user.account_age_days < 7:
        return "new_user"
    elif input_data.user.tier.value == "enterprise":
        return "premium_user"
    else:
        return "normal"


def _action_matches(predicted: Action, ground_truth: Action) -> bool:
    """Check if predicted action matches ground truth (with some tolerance)."""
    # Exact match
    if predicted == ground_truth:
        return True

    # Allow some similar actions to match
    allow_actions = {Action.ALLOW, Action.WARN}
    throttle_actions = {Action.THROTTLE_SOFT, Action.THROTTLE_HARD}
    block_actions = {Action.BLOCK_TEMPORARY, Action.BLOCK_EXTENDED, Action.CAPTCHA}

    if predicted in allow_actions and ground_truth in allow_actions:
        return True
    if predicted in throttle_actions and ground_truth in throttle_actions:
        return True
    if predicted in block_actions and ground_truth in block_actions:
        return True

    return False


def print_results(results: dict, scenario_counts: dict):
    """Print formatted results."""

    print("\n" + "=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)

    # Overall accuracy
    print("\n--- Overall Accuracy ---")
    for method in ["kvrm", "token_bucket", "sliding_window", "rule_based"]:
        total_correct = sum(r["correct"] for r in results[method].values())
        total_samples = sum(r["total"] for r in results[method].values())
        accuracy = total_correct / total_samples if total_samples > 0 else 0
        print(f"  {method:20s}: {accuracy*100:5.1f}%")

    # Per-scenario accuracy
    print("\n--- Accuracy by Scenario ---")
    scenarios = sorted(scenario_counts.keys())

    # Header
    header = f"{'Scenario':25s}"
    for method in ["kvrm", "token_bucket", "rule_based"]:
        header += f" | {method:12s}"
    print(header)
    print("-" * len(header))

    for scenario in scenarios:
        row = f"{scenario:25s}"
        for method in ["kvrm", "token_bucket", "rule_based"]:
            data = results[method][scenario]
            acc = data["correct"] / data["total"] if data["total"] > 0 else 0
            row += f" | {acc*100:10.1f}%"
        row += f"  (n={scenario_counts[scenario]})"
        print(row)

    # Key insights
    print("\n--- Key Insights ---")

    # Where KVRM beats rule-based
    print("\nScenarios where KVRM outperforms rule-based:")
    for scenario in scenarios:
        kvrm_acc = results["kvrm"][scenario]["correct"] / max(results["kvrm"][scenario]["total"], 1)
        rule_acc = results["rule_based"][scenario]["correct"] / max(results["rule_based"][scenario]["total"], 1)
        diff = kvrm_acc - rule_acc
        if diff > 0.05:  # 5% better
            print(f"  {scenario}: +{diff*100:.1f}% (KVRM: {kvrm_acc*100:.1f}%, Rules: {rule_acc*100:.1f}%)")

    # Where rule-based beats KVRM
    print("\nScenarios where rule-based outperforms KVRM:")
    for scenario in scenarios:
        kvrm_acc = results["kvrm"][scenario]["correct"] / max(results["kvrm"][scenario]["total"], 1)
        rule_acc = results["rule_based"][scenario]["correct"] / max(results["rule_based"][scenario]["total"], 1)
        diff = rule_acc - kvrm_acc
        if diff > 0.05:
            print(f"  {scenario}: +{diff*100:.1f}% (Rules: {rule_acc*100:.1f}%, KVRM: {kvrm_acc*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Rate Limiter KVRM")
    parser.add_argument("--model", help="Path to model checkpoint")
    parser.add_argument("--samples", type=int, default=1000, help="Number of samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--lite", action="store_true", help="Use lite model")
    parser.add_argument("--untrained", action="store_true", help="Evaluate untrained model")

    args = parser.parse_args()

    # Initialize KVRM
    if args.untrained:
        print("Evaluating UNTRAINED KVRM (random weights)...")
        engine = RateLimiterInference(use_lite=args.lite)
    elif args.model:
        print(f"Loading model from {args.model}...")
        engine = RateLimiterInference(model_path=args.model, use_lite=args.lite)
    else:
        print("Evaluating UNTRAINED KVRM (no model provided)...")
        engine = RateLimiterInference(use_lite=args.lite)

    print(f"Model info: {engine.get_model_info()}")

    # Warmup
    engine.warmup(10)

    # Evaluate
    results, scenario_counts = evaluate_on_scenarios(
        engine,
        n_samples=args.samples,
        seed=args.seed,
    )

    # Print results
    print_results(results, scenario_counts)

    # Latency stats
    print(f"\nLatency stats: {engine.get_latency_stats()}")


if __name__ == "__main__":
    main()
