"""Load live KVRM demo JSONL datasets into train/eval splits."""
from __future__ import annotations

import json
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parents[4] / "kvrm-demos"

DOMAIN_ORDER = [
    "soc",
    "sre",
    "drone",
    "grid",
    "finance",
    "medical",
    "customer_support",
    "content_moderation",
]

DEMO_PATHS = {
    "soc": {
        "train": DEMO_ROOT / "soc-playbook-router" / "data" / "train_cases.jsonl",
        "eval":  DEMO_ROOT / "soc-playbook-router" / "data" / "cases.jsonl",
        "registry": DEMO_ROOT / "soc-playbook-router" / "data" / "registry.json",
    },
    "sre": {
        "train": DEMO_ROOT / "sre-policy-router" / "data" / "train_cases.jsonl",
        "eval":  DEMO_ROOT / "sre-policy-router" / "data" / "cases.jsonl",
        "registry": DEMO_ROOT / "sre-policy-router" / "data" / "registry.json",
    },
    "drone": {
        "train": DEMO_ROOT / "drone-mission-router" / "data" / "train_cases.jsonl",
        "eval":  DEMO_ROOT / "drone-mission-router" / "data" / "cases.jsonl",
        "registry": DEMO_ROOT / "drone-mission-router" / "data" / "registry.json",
    },
    "grid": {
        "train": DEMO_ROOT / "grid-ops-router" / "data" / "train_cases.jsonl",
        "eval":  DEMO_ROOT / "grid-ops-router" / "data" / "cases.jsonl",
        "registry": DEMO_ROOT / "grid-ops-router" / "data" / "registry.json",
    },
    "finance": {
        "train": DEMO_ROOT / "finance-risk-router" / "data" / "train_cases.jsonl",
        "eval":  DEMO_ROOT / "finance-risk-router" / "data" / "cases.jsonl",
        "registry": DEMO_ROOT / "finance-risk-router" / "data" / "registry.json",
    },
    "medical": {
        "train": DEMO_ROOT / "medical-workflow-router" / "data" / "train_cases.jsonl",
        "eval":  DEMO_ROOT / "medical-workflow-router" / "data" / "cases.jsonl",
        "registry": DEMO_ROOT / "medical-workflow-router" / "data" / "registry.json",
    },
    "customer_support": {
        "train": DEMO_ROOT / "customer-support-router" / "data" / "train_cases.jsonl",
        "eval":  DEMO_ROOT / "customer-support-router" / "data" / "cases.jsonl",
        "registry": DEMO_ROOT / "customer-support-router" / "data" / "registry.json",
    },
    "content_moderation": {
        "train": DEMO_ROOT / "content-moderation-router" / "data" / "train_cases.jsonl",
        "eval":  DEMO_ROOT / "content-moderation-router" / "data" / "cases.jsonl",
        "registry": DEMO_ROOT / "content-moderation-router" / "data" / "registry.json",
    },
}


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def load_registry(path: Path) -> dict:
    """Load a registry JSON file."""
    return json.loads(path.read_text())


def load_domain_data(domain: str) -> dict:
    """Load train cases, eval cases, and registry for a domain."""
    paths = DEMO_PATHS[domain]
    train_cases = load_jsonl(paths["train"])
    eval_cases = load_jsonl(paths["eval"])
    registry = load_registry(paths["registry"])

    # separate eval into supported and unsupported
    supported_eval = [c for c in eval_cases if c.get("supported", True)]
    unsupported_eval = [c for c in eval_cases if not c.get("supported", True)]

    return {
        "train": train_cases,
        "eval_all": eval_cases,
        "eval_supported": supported_eval,
        "eval_unsupported": unsupported_eval,
        "registry": registry,
    }
