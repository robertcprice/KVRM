"""Load a KVRM domain from a plain data directory — no Python code required.

A *domain directory* is the bring-your-own-domain interface to KVRM:

    my-domain/
    ├── registry.json        # versioned action registry with support_specs
    ├── train_cases.jsonl    # labeled examples that power the selectors
    ├── cases.jsonl          # (optional) evaluation cases
    ├── kvrm.json            # (optional) tuning overrides
    └── model.joblib         # (optional) trained compact selector

Everything the domain factory needs (feature schema, distance metric, rules,
executor handlers) is derived from the registry's ``context_schema`` and the
training cases, with ``kvrm.json`` providing optional overrides. This is what
makes ``kvrm route|eval|train|explain`` work on arbitrary user domains instead
of only the bundled research packs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .context import feature_key
from .domain_factory import DomainConfig, build_domain_executor, build_domain_selectors
from .registry import load_registry
from .runtime import KVRMRuntime
from .types import DecisionInput, DecisionResult, RegistrySpec
from .validation import DeterministicValidator

REGISTRY_FILENAME = "registry.json"
TRAIN_FILENAME = "train_cases.jsonl"
CASES_FILENAME = "cases.jsonl"
CONFIG_FILENAME = "kvrm.json"
MODEL_FILENAME = "model.joblib"

FALLBACK_TAG_HINTS = ("fallback", "handoff", "human", "escalation")


class DomainDirError(ValueError):
    """A domain directory is missing required files or contains invalid data."""


@dataclass
class DomainDir:
    """A resolved domain directory with its derived configuration."""

    path: Path
    registry: RegistrySpec
    config: DomainConfig
    overrides: dict[str, Any] = field(default_factory=dict)

    @property
    def train_cases_path(self) -> Path:
        return self.path / TRAIN_FILENAME

    @property
    def cases_path(self) -> Path:
        return self.path / CASES_FILENAME

    @property
    def default_model_path(self) -> Path:
        return self.path / MODEL_FILENAME


def _load_jsonl(path: Path) -> list[dict]:
    cases = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise DomainDirError(f"{path}:{line_number} is not valid JSON: {exc}") from exc
    return cases


def load_domain_dir(path: str | Path) -> DomainDir:
    """Resolve a domain directory into a registry plus derived DomainConfig."""
    root = Path(path).resolve()
    if not root.is_dir():
        raise DomainDirError(f"{root} is not a directory")
    registry_path = root / REGISTRY_FILENAME
    train_path = root / TRAIN_FILENAME
    if not registry_path.is_file():
        raise DomainDirError(f"{root} has no {REGISTRY_FILENAME}")
    if not train_path.is_file():
        raise DomainDirError(f"{root} has no {TRAIN_FILENAME}")

    registry = load_registry(registry_path)
    train_cases = _load_jsonl(train_path)
    overrides: dict[str, Any] = {}
    config_path = root / CONFIG_FILENAME
    if config_path.is_file():
        overrides = json.loads(config_path.read_text())

    config = derive_domain_config(
        registry,
        train_cases,
        name=overrides.get("name", registry.registry_name.replace("-", "_")),
        overrides=overrides,
    )
    return DomainDir(path=root, registry=registry, config=config, overrides=overrides)


def derive_domain_config(
    registry: RegistrySpec,
    train_cases: list[dict],
    *,
    name: str,
    overrides: dict[str, Any] | None = None,
) -> DomainConfig:
    """Derive a full DomainConfig from a registry and training cases."""
    overrides = overrides or {}
    schema = registry.context_schema

    categorical_values = {
        key: list(spec["enum"]) for key, spec in schema.items() if spec.get("enum")
    }

    numeric_ranges: dict[str, tuple[float, float]] = {}
    for key, spec in schema.items():
        if spec.get("enum") or spec.get("type") not in ("number", "integer"):
            continue
        if "minimum" in spec and "maximum" in spec:
            numeric_ranges[key] = (float(spec["minimum"]), float(spec["maximum"]))
            continue
        observed = [
            float(case["input_features"][key])
            for case in train_cases
            if isinstance(case.get("input_features", {}).get(key), (int, float))
            and not isinstance(case["input_features"][key], bool)
        ]
        if observed:
            numeric_ranges[key] = (min(observed), max(observed))
        else:
            numeric_ranges[key] = (0.0, 1.0)

    rules: dict[str, tuple[str, float]] = {}
    for case in train_cases:
        expected = case.get("expected_action_id")
        features = case.get("input_features")
        if expected is None or features is None or not case.get("supported", True):
            continue
        rules[feature_key(features)] = (expected, 0.9)

    fallback = overrides.get("fallback_action_id")
    if fallback is None:
        fallback = _infer_fallback_action(registry)

    feature_order = list(registry.required_features) or sorted(schema)

    return DomainConfig(
        name=name,
        feature_order=feature_order,
        categorical_values=categorical_values,
        rules=rules,
        executor_handlers={action.action_id: action.action_id for action in registry.actions},
        executor_output_key=overrides.get("executor_output_key", "action"),
        fallback_action_id=fallback or "",
        numeric_feature_ranges=numeric_ranges or None,
        unsupported_penalty=overrides.get("unsupported_penalty", 1.25),
        support_aware_retrieval=overrides.get("support_aware_retrieval", False),
        prototype_max_distance=overrides.get("prototype_max_distance", 5.0),
        semantic_min_leaf_count=overrides.get("semantic_min_leaf_count", 5),
        learned_min_confidence=overrides.get("learned_min_confidence", 0.42),
    )


def _infer_fallback_action(registry: RegistrySpec) -> str | None:
    for action in registry.actions:
        haystack = " ".join([action.action_id, *action.tags]).lower()
        if any(hint in haystack for hint in FALLBACK_TAG_HINTS):
            return action.action_id
    return None


def build_domain_runtime(
    domain: DomainDir,
    *,
    strategy: str = "hybrid",
    model_path: str | Path | None = None,
    threshold: float = 0.60,
) -> KVRMRuntime:
    """Build a ready-to-route runtime for a domain directory."""
    selectors = build_domain_selectors(domain.config)
    train_path = domain.train_cases_path

    if model_path is None and domain.default_model_path.is_file():
        model_path = domain.default_model_path

    if strategy == "hybrid":
        selector = selectors.build_hybrid_selector(train_path, model_path)
    elif strategy == "rule":
        selector = selectors.build_rule_selector()
    elif strategy == "retrieval":
        selector = selectors.build_retrieval_selector(train_path)
    elif strategy == "prototype":
        selector = selectors.build_prototype_selector(train_path)
    elif strategy == "semantic":
        selector = selectors.build_semantic_selector(train_path)
    elif strategy == "learned":
        if model_path is None:
            raise DomainDirError("learned strategy requires a trained model (kvrm train)")
        selector = selectors.build_learned_selector(train_path, model_path)
    else:
        raise DomainDirError(f"unknown strategy: {strategy}")

    return KVRMRuntime(
        registry=domain.registry,
        selector=selector,
        validator=DeterministicValidator(domain.registry),
        executor=build_domain_executor(domain.config),
        threshold=threshold,
        fallback_action_id=domain.config.fallback_action_id or None,
    )


def decision_input_from_case(case: dict, *, index: int = 0) -> DecisionInput:
    return DecisionInput(
        case_id=str(case.get("case_id", f"case_{index}")),
        features=case["input_features"],
        supported=bool(case.get("supported", True)),
        ood=bool(case.get("ood", False)),
        expected_action_id=case.get("expected_action_id"),
    )


def evaluate_domain(
    domain: DomainDir,
    runtime: KVRMRuntime,
    cases: list[dict] | None = None,
) -> dict[str, Any]:
    """Route every evaluation case and compute the canonical fail-closed metrics."""
    if cases is None:
        if not domain.cases_path.is_file():
            raise DomainDirError(f"{domain.path} has no {CASES_FILENAME}")
        cases = _load_jsonl(domain.cases_path)
    if not cases:
        raise DomainDirError("no evaluation cases")

    valid_action_ids = {action.action_id for action in domain.registry.actions}
    fallback_id = domain.config.fallback_action_id or None

    supported_total = supported_correct = 0
    unsupported_total = unsupported_rejected = false_accepts = 0
    invalid_outputs = 0
    failures: list[dict[str, Any]] = []

    for index, case in enumerate(cases):
        decision: DecisionResult = runtime.decide_and_execute(
            decision_input_from_case(case, index=index)
        )
        selected = decision.selected_action_id
        executed_real_action = (
            decision.final_status == "executed"
            and not decision.fallback_used
            and not decision.abstained
        )
        if selected is not None and selected not in valid_action_ids:
            invalid_outputs += 1

        if case.get("supported", True):
            supported_total += 1
            expected = case.get("expected_action_id")
            # The runtime scores correctness against expected_action_id and
            # accepts fallback execution when the fallback IS the expected
            # action — mirror that rather than re-deriving it here.
            if decision.correct if decision.correct is not None else (
                executed_real_action and selected == expected
            ):
                supported_correct += 1
            else:
                failures.append(
                    {
                        "case_id": case.get("case_id", index),
                        "kind": "supported_miss",
                        "expected": expected,
                        "selected": selected,
                        "final_status": str(decision.final_status),
                    }
                )
        else:
            unsupported_total += 1
            if executed_real_action and selected != fallback_id:
                false_accepts += 1
                failures.append(
                    {
                        "case_id": case.get("case_id", index),
                        "kind": "false_accept",
                        "selected": selected,
                        "final_status": str(decision.final_status),
                    }
                )
            else:
                unsupported_rejected += 1

    return {
        "total_cases": len(cases),
        "supported_cases": supported_total,
        "unsupported_cases": unsupported_total,
        "semantic_correctness_rate": (supported_correct / supported_total) if supported_total else None,
        "false_accept_rate": (false_accepts / unsupported_total) if unsupported_total else None,
        "unsupported_case_rejection_rate": (unsupported_rejected / unsupported_total) if unsupported_total else None,
        "invalid_output_rate": invalid_outputs / len(cases),
        "failures": failures,
    }


# --------------------------------------------------------------------------
# Scaffolding
# --------------------------------------------------------------------------

_SCAFFOLD_REGISTRY = {
    "registry_name": "{name}",
    "version": "0.1.0",
    "required_features": ["risk_level", "amount", "account_verified"],
    "context_schema": {
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "amount": {"type": "number", "minimum": 0, "maximum": 10000},
        "account_verified": {"type": "boolean"},
    },
    "actions": [
        {
            "action_id": "approve_request",
            "name": "Approve Request",
            "description": "Approve automatically when risk is low and the account is verified.",
            "support_spec": {
                "all": [
                    {"feature": "risk_level", "op": "eq", "value": "low"},
                    {"feature": "account_verified", "op": "eq", "value": True},
                    {"feature": "amount", "op": "lte", "value": 5000},
                ]
            },
            "tags": ["automated"],
        },
        {
            "action_id": "deny_request",
            "name": "Deny Request",
            "description": "Deny automatically when risk is high and the account is unverified.",
            "support_spec": {
                "all": [
                    {"feature": "risk_level", "op": "eq", "value": "high"},
                    {"feature": "account_verified", "op": "eq", "value": False},
                ]
            },
            "tags": ["automated"],
        },
        {
            "action_id": "escalate_to_human",
            "name": "Escalate to Human",
            "description": "Route to a human reviewer for everything between the automatic envelopes.",
            "support_spec": {
                "all": [
                    {"feature": "risk_level", "op": "in", "value": ["low", "medium", "high"]},
                ]
            },
            "tags": ["fallback", "handoff"],
        },
    ],
}

_SCAFFOLD_TRAIN = [
    {"case_id": "train_001", "input_features": {"risk_level": "low", "amount": 120.0, "account_verified": True}, "expected_action_id": "approve_request", "supported": True},
    {"case_id": "train_002", "input_features": {"risk_level": "low", "amount": 4200.0, "account_verified": True}, "expected_action_id": "approve_request", "supported": True},
    {"case_id": "train_003", "input_features": {"risk_level": "high", "amount": 900.0, "account_verified": False}, "expected_action_id": "deny_request", "supported": True},
    {"case_id": "train_004", "input_features": {"risk_level": "high", "amount": 7600.0, "account_verified": False}, "expected_action_id": "deny_request", "supported": True},
    {"case_id": "train_005", "input_features": {"risk_level": "medium", "amount": 1500.0, "account_verified": True}, "expected_action_id": "escalate_to_human", "supported": True},
    {"case_id": "train_006", "input_features": {"risk_level": "medium", "amount": 300.0, "account_verified": False}, "expected_action_id": "escalate_to_human", "supported": True},
    {"case_id": "train_007", "input_features": {"risk_level": "high", "amount": 50.0, "account_verified": True}, "expected_action_id": "escalate_to_human", "supported": True},
    {"case_id": "train_008", "input_features": {"risk_level": "low", "amount": 9000.0, "account_verified": True}, "expected_action_id": "escalate_to_human", "supported": True},
]

_SCAFFOLD_CASES = [
    {"case_id": "eval_001", "input_features": {"risk_level": "low", "amount": 80.0, "account_verified": True}, "expected_action_id": "approve_request", "supported": True},
    {"case_id": "eval_002", "input_features": {"risk_level": "high", "amount": 2500.0, "account_verified": False}, "expected_action_id": "deny_request", "supported": True},
    {"case_id": "eval_003", "input_features": {"risk_level": "medium", "amount": 600.0, "account_verified": True}, "expected_action_id": "escalate_to_human", "supported": True},
    {"case_id": "eval_004", "input_features": {"risk_level": "low", "amount": 15000.0, "account_verified": True}, "expected_action_id": None, "supported": False},
]

_SCAFFOLD_CONFIG = {
    "fallback_action_id": "escalate_to_human",
    "executor_output_key": "action",
}


def scaffold_domain(path: str | Path, *, name: str | None = None) -> Path:
    """Write a small, working example domain into *path* (must not already
    contain a registry). Returns the directory path."""
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    registry_path = root / REGISTRY_FILENAME
    if registry_path.exists():
        raise DomainDirError(f"{registry_path} already exists; refusing to overwrite")

    domain_name = name or root.name.replace("-", "_")
    registry = dict(_SCAFFOLD_REGISTRY)
    registry["registry_name"] = domain_name

    registry_path.write_text(json.dumps(registry, indent=2) + "\n")
    (root / TRAIN_FILENAME).write_text(
        "".join(json.dumps(case) + "\n" for case in _SCAFFOLD_TRAIN)
    )
    (root / CASES_FILENAME).write_text(
        "".join(json.dumps(case) + "\n" for case in _SCAFFOLD_CASES)
    )
    (root / CONFIG_FILENAME).write_text(json.dumps(_SCAFFOLD_CONFIG, indent=2) + "\n")
    return root
