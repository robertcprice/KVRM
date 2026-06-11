"""Registry evolution tests: what happens when the action registry changes?

Three mutation types from the QWEN_BASELINE_COMPARISON_PROTOCOL:
  1. Append-only: add new actions to registry
  2. Reorder: shuffle action ordering
  3. Incompatible: rename/remove existing actions

KVRM should handle these deterministically because it validates against
the live registry. A fine-tuned model emits stale labels unless retrained.
"""
from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass
from pathlib import Path

from .classifier import DirectLabelClassifier, JsonActionClassifier, ConstrainedClassifier, BaselineResult
from .data_loader import load_domain_data
from .domain_schemas import DOMAINS
from .evaluator import compute_baseline_metrics


@dataclass
class EvolutionResult:
    mutation_type: str
    domain: str
    variant: str
    metrics: dict
    stale_label_count: int
    total_predictions: int
    stale_label_rate: float
    details: list[dict]


def mutate_registry_append(registry: dict) -> tuple[dict, list[str]]:
    """Add two new synthetic actions to the registry."""
    new_registry = copy.deepcopy(registry)
    new_actions = [
        {
            "action_id": "synthetic_new_action_alpha",
            "name": "Synthetic Action Alpha",
            "description": "A new action added after initial training",
            "parameters_schema": {"type": "object", "properties": {}, "required": []},
            "tags": ["synthetic", "post-training"],
        },
        {
            "action_id": "synthetic_new_action_beta",
            "name": "Synthetic Action Beta",
            "description": "Another new action added after initial training",
            "parameters_schema": {"type": "object", "properties": {}, "required": []},
            "tags": ["synthetic", "post-training"],
        },
    ]
    new_registry["actions"].extend(new_actions)
    new_ids = [a["action_id"] for a in new_actions]
    return new_registry, new_ids


def mutate_registry_reorder(registry: dict) -> dict:
    """Reverse the action ordering."""
    new_registry = copy.deepcopy(registry)
    new_registry["actions"] = list(reversed(new_registry["actions"]))
    return new_registry


def mutate_registry_incompatible(registry: dict) -> tuple[dict, dict[str, str]]:
    """Rename first two actions to simulate breaking change."""
    new_registry = copy.deepcopy(registry)
    renames = {}
    for i, action in enumerate(new_registry["actions"][:2]):
        old_id = action["action_id"]
        new_id = f"v2_{old_id}"
        action["action_id"] = new_id
        renames[old_id] = new_id
    return new_registry, renames


def test_evolution(domain: str, variant: str, mutation: str) -> EvolutionResult:
    """Train on original registry, evaluate after mutation."""
    data = load_domain_data(domain)
    train_cases = [c for c in data["train"] if c.get("expected_action_id") is not None]
    eval_cases = data["eval_all"]
    registry = data["registry"]
    cfg = DOMAINS[domain]

    # Train on original
    if variant == "direct_label":
        clf = DirectLabelClassifier(domain=domain)
    elif variant == "json_action":
        clf = JsonActionClassifier(domain=domain, threshold=0.60)
    elif variant == "constrained":
        clf = ConstrainedClassifier(domain=domain)
    else:
        raise ValueError(f"Unknown variant: {variant}")

    clf.train(train_cases)

    # Apply mutation
    if mutation == "append":
        new_registry, new_ids = mutate_registry_append(registry)
        valid_ids = set(a["action_id"] for a in new_registry["actions"])
    elif mutation == "reorder":
        new_registry = mutate_registry_reorder(registry)
        valid_ids = set(a["action_id"] for a in new_registry["actions"])
    elif mutation == "incompatible":
        new_registry, renames = mutate_registry_incompatible(registry)
        valid_ids = set(a["action_id"] for a in new_registry["actions"])
    else:
        raise ValueError(f"Unknown mutation: {mutation}")

    # Evaluate: model still predicts from old label set
    results: list[BaselineResult] = []
    stale_labels = []
    for case in eval_cases:
        r = clf.predict(case)
        # Check if predicted label exists in mutated registry
        if r.predicted_action_id not in valid_ids:
            r.valid = False
            stale_labels.append({
                "case_id": r.case_id,
                "predicted": r.predicted_action_id,
                "valid_in_new_registry": False,
            })
        results.append(r)

    metrics = compute_baseline_metrics(results, eval_cases)
    stale_rate = len(stale_labels) / len(results) if results else 0.0

    return EvolutionResult(
        mutation_type=mutation,
        domain=domain,
        variant=variant,
        metrics=metrics,
        stale_label_count=len(stale_labels),
        total_predictions=len(results),
        stale_label_rate=stale_rate,
        details=stale_labels,
    )


def run_all_evolution_tests(output_dir: Path | None = None) -> dict:
    """Run all evolution tests across domains, variants, mutations."""
    if output_dir is None:
        output_dir = Path(__file__).resolve().parents[2] / "outputs" / "registry_evolution"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}
    for domain in ["sre", "soc", "drone"]:
        for variant in ["direct_label", "json_action", "constrained"]:
            for mutation in ["append", "reorder", "incompatible"]:
                key = f"{domain}/{variant}/{mutation}"
                r = test_evolution(domain, variant, mutation)
                all_results[key] = {
                    "stale_label_rate": r.stale_label_rate,
                    "stale_label_count": r.stale_label_count,
                    "structural_validity": r.metrics["structural_validity_rate"],
                    "semantic_correctness": r.metrics["semantic_correctness_rate"],
                    "false_accept_rate": r.metrics["false_accept_rate"],
                }
                print(f"  {key}: stale_labels={r.stale_label_count}/{r.total_predictions}"
                      f"  validity={r.metrics['structural_validity_rate']:.3f}")

    (output_dir / "evolution_results.json").write_text(
        json.dumps(all_results, indent=2)
    )
    return all_results
