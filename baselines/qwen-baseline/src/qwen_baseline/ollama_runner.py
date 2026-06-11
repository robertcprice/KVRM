"""Real small-model LLM baseline backed by the local Ollama API."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

from .domain_schemas import DOMAINS

DEFAULT_OLLAMA_GENERATE_API = "http://127.0.0.1:11434/api/generate"
DEFAULT_OLLAMA_CHAT_API = "http://127.0.0.1:11434/api/chat"


@dataclass
class OllamaCaseResult:
    case_id: str
    selected_action_id: str | None
    expected_action_id: str | None
    confidence: float
    valid: bool
    correct: bool
    abstained: bool
    fallback_used: bool
    final_status: str
    latency_ms: float
    supported: bool
    ood: bool
    source: str
    model: str
    variant: str
    reason: str | None = None
    raw_response: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def select_representative_examples(
    train_cases: list[dict],
    labels: list[str],
    *,
    max_examples_per_action: int = 1,
) -> list[dict]:
    examples: list[dict] = []
    seen_counts = {label: 0 for label in labels}
    for case in train_cases:
        label = case.get("expected_action_id")
        if label not in seen_counts:
            continue
        if seen_counts[label] >= max_examples_per_action:
            continue
        examples.append(case)
        seen_counts[label] += 1
    return examples


def build_prompt(
    domain: str,
    train_cases: list[dict],
    case: dict,
    *,
    max_examples_per_action: int = 1,
) -> str:
    cfg = DOMAINS[domain]
    examples = select_representative_examples(
        train_cases,
        cfg["labels"],
        max_examples_per_action=max_examples_per_action,
    )
    schema_lines = []
    for feature_name in cfg["feature_order"]:
        spec = cfg["context_schema"][feature_name]
        if spec["type"] in {"number", "integer"}:
            minimum = spec.get("minimum")
            maximum = spec.get("maximum")
            if minimum is not None and maximum is not None:
                range_text = f"{minimum}..{maximum}"
            else:
                range_text = "numeric"
            schema_lines.append(f"- {feature_name}: numeric ({range_text})")
        elif spec["type"] == "boolean":
            schema_lines.append(f"- {feature_name}: boolean")
        else:
            schema_lines.append(
                f"- {feature_name}: one of {', '.join(map(str, spec['enum']))}"
            )

    action_lines = [
        f"- {action_id}: {cfg['label_descriptions'][action_id]}"
        for action_id in cfg["labels"]
    ]

    example_lines = []
    for index, example in enumerate(examples, start=1):
        example_output = {
            "decision": "action",
            "action_id": example["expected_action_id"],
            "confidence": 0.99,
            "reason": "matches the supported action pattern",
        }
        example_lines.append(
            "\n".join(
                [
                    f"Example {index}:",
                    f"Input: {json.dumps(example['input_features'], sort_keys=True)}",
                    f"Output: {json.dumps(example_output, separators=(',', ':'))}",
                ]
            )
        )

    system_prompt = "\n".join(
        [
            "You are a strict bounded action router for a finite audited registry.",
            "",
            "Return JSON only with exactly these keys:",
            '{"decision":"action|abstain","action_id":"<allowed action id>|null","confidence":0.0,"reason":"short text"}',
            "",
            "Rules:",
            '- Use `"decision":"action"` only when one allowed action is clearly supported by the input.',
            '- Use `"decision":"abstain"` with `"action_id": null` if the case is unsupported, ambiguous, or not clearly covered by the allowed actions.',
            "- Never invent an action id.",
            "- Keep the reason under 25 words.",
            "- Confidence must be between 0.0 and 1.0.",
            "",
            f"Domain: {domain}",
            f"Registry version: {cfg['registry_version']}",
            f"Fallback action in KVRM (for reference only): {cfg['fallback']}",
            "",
            "Allowed actions:",
            *action_lines,
            "",
            "Feature schema:",
            *schema_lines,
            "",
            "Representative supported examples:",
            *example_lines,
        ]
    )
    user_prompt = "\n".join(
        [
            "Now classify this case.",
            f"Input: {json.dumps(case['input_features'], sort_keys=True)}",
            "JSON:",
        ]
    )
    return system_prompt + "\n\n" + user_prompt


def build_messages(
    domain: str,
    train_cases: list[dict],
    case: dict,
    *,
    max_examples_per_action: int = 1,
) -> list[dict[str, str]]:
    cfg = DOMAINS[domain]
    examples = select_representative_examples(
        train_cases,
        cfg["labels"],
        max_examples_per_action=max_examples_per_action,
    )
    schema_lines = []
    for feature_name in cfg["feature_order"]:
        spec = cfg["context_schema"][feature_name]
        if spec["type"] in {"number", "integer"}:
            minimum = spec.get("minimum")
            maximum = spec.get("maximum")
            if minimum is not None and maximum is not None:
                range_text = f"{minimum}..{maximum}"
            else:
                range_text = "numeric"
            schema_lines.append(f"- {feature_name}: numeric ({range_text})")
        elif spec["type"] == "boolean":
            schema_lines.append(f"- {feature_name}: boolean")
        else:
            schema_lines.append(
                f"- {feature_name}: one of {', '.join(map(str, spec['enum']))}"
            )

    action_lines = [
        f"- {action_id}: {cfg['label_descriptions'][action_id]}"
        for action_id in cfg["labels"]
    ]

    example_lines = []
    for index, example in enumerate(examples, start=1):
        example_output = {
            "decision": "action",
            "action_id": example["expected_action_id"],
            "confidence": 0.99,
            "reason": "matches the supported action pattern",
        }
        example_lines.append(
            "\n".join(
                [
                    f"Example {index}:",
                    f"Input: {json.dumps(example['input_features'], sort_keys=True)}",
                    f"Output: {json.dumps(example_output, separators=(',', ':'))}",
                ]
            )
        )

    system_prompt = "\n".join(
        [
            "You are a strict bounded action router for a finite audited registry.",
            "Return JSON only with exactly these keys:",
            '{"decision":"action|abstain","action_id":"<allowed action id>|null","confidence":0.0,"reason":"short text"}',
            "",
            "Rules:",
            '- Use `"decision":"action"` only when one allowed action is clearly supported by the input.',
            '- Use `"decision":"abstain"` with `"action_id": null` if the case is unsupported, ambiguous, or not clearly covered by the allowed actions.',
            "- Never invent an action id.",
            "- Keep the reason under 25 words.",
            "- Confidence must be between 0.0 and 1.0.",
            "",
            f"Domain: {domain}",
            f"Registry version: {cfg['registry_version']}",
            f"Fallback action in KVRM (for reference only): {cfg['fallback']}",
        ]
    )
    user_prompt = "\n".join(
        [
            "Allowed actions:",
            *action_lines,
            "",
            "Feature schema:",
            *schema_lines,
            "",
            "Representative supported examples:",
            *example_lines,
            "",
            "Now classify this case.",
            f"Input: {json.dumps(case['input_features'], sort_keys=True)}",
            "JSON:",
        ]
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def parse_ollama_response(
    raw_response: str,
    *,
    allowed_labels: list[str],
) -> dict[str, Any]:
    payload = _extract_payload(raw_response)
    if not payload:
        return {
            "decision": "invalid",
            "action_id": None,
            "confidence": 0.0,
            "reason": None,
            "valid": False,
        }
    decision = str(payload.get("decision", "")).strip().lower()
    action_id = payload.get("action_id")
    reason = payload.get("reason")
    confidence = _coerce_confidence(payload.get("confidence"))

    if isinstance(action_id, str):
        action_id = action_id.strip()
        if action_id.upper() in {"ABSTAIN", "N/A", "NULL", "NONE"}:
            action_id = None
    elif action_id is not None:
        action_id = str(action_id)

    if not decision:
        if action_id is None:
            return {
                "decision": "invalid",
                "action_id": None,
                "confidence": confidence,
                "reason": reason,
                "valid": False,
            }
        decision = "action"
    if decision in allowed_labels:
        if action_id is None or action_id == decision:
            action_id = decision
            decision = "action"
        else:
            return {
                "decision": "invalid",
                "action_id": action_id,
                "confidence": confidence,
                "reason": reason,
                "valid": False,
            }
    elif decision not in {"action", "abstain"}:
        if action_id in allowed_labels:
            decision = "action"
        else:
            return {
                "decision": "invalid",
                "action_id": action_id,
                "confidence": confidence,
                "reason": reason,
                "valid": False,
            }

    if decision == "abstain":
        action_id = None
        valid = True
    else:
        valid = action_id in allowed_labels

    return {
        "decision": decision,
        "action_id": action_id,
        "confidence": confidence,
        "reason": reason,
        "valid": valid,
    }


class OllamaJsonBaseline:
    """Few-shot JSON baseline against the live canonical KVRM demo packs."""

    def __init__(
        self,
        *,
        domain: str,
        model: str,
        train_cases: list[dict],
        variant: str = "abstain_json",
        api_url: str = DEFAULT_OLLAMA_GENERATE_API,
        timeout_s: float = 180.0,
        temperature: float = 0.0,
        max_examples_per_action: int = 1,
        max_retries: int = 3,
        retry_backoff_s: float = 2.0,
    ) -> None:
        self.domain = domain
        self.model = model
        self.train_cases = train_cases
        self.variant = variant
        self.api_url = api_url
        self.timeout_s = timeout_s
        self.temperature = temperature
        self.max_examples_per_action = max_examples_per_action
        self.max_retries = max_retries
        self.retry_backoff_s = retry_backoff_s
        self.cfg = DOMAINS[domain]

    def predict(self, case: dict) -> OllamaCaseResult:
        started = time.perf_counter()
        raw_response = self._generate(case)
        latency_ms = (time.perf_counter() - started) * 1000
        parsed = parse_ollama_response(raw_response, allowed_labels=self.cfg["labels"])

        supported = bool(case.get("supported", True))
        abstained = parsed["decision"] == "abstain"
        selected_action_id = parsed["action_id"]
        valid = bool(parsed["valid"])

        if parsed["decision"] == "invalid":
            final_status = "invalid_output"
        elif abstained:
            final_status = "abstained"
        elif valid:
            final_status = "executed"
        else:
            final_status = "invalid_output"

        correct = (
            supported
            and valid
            and not abstained
            and selected_action_id == case.get("expected_action_id")
        )

        return OllamaCaseResult(
            case_id=case["case_id"],
            selected_action_id=selected_action_id,
            expected_action_id=case.get("expected_action_id"),
            confidence=parsed["confidence"],
            valid=valid,
            correct=correct,
            abstained=abstained,
            fallback_used=False,
            final_status=final_status,
            latency_ms=latency_ms,
            supported=supported,
            ood=bool(case.get("ood", False)),
            source=f"ollama:{self.model}:{self.variant}",
            model=self.model,
            variant=self.variant,
            reason=parsed["reason"],
            raw_response=raw_response,
        )

    def _generate(self, case: dict) -> str:
        payload, api_url, content_field = self._build_request(case)
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            request = urllib.request.Request(
                api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                    body = json.loads(response.read().decode("utf-8"))
                if content_field == "response":
                    return str(body.get("response", "")).strip()
                message = body.get("message", {})
                return str(message.get("content", "")).strip()
            except (TimeoutError, urllib.error.URLError, OSError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_backoff_s * attempt)
        assert last_error is not None
        raise last_error

    def _build_request(self, case: dict) -> tuple[dict[str, Any], str, str]:
        options = {
            "temperature": self.temperature,
            "seed": 42,
            "num_predict": 96,
        }
        if self._use_chat_api():
            return (
                {
                    "model": self.model,
                    "messages": build_messages(
                        self.domain,
                        self.train_cases,
                        case,
                        max_examples_per_action=self.max_examples_per_action,
                    ),
                    "stream": False,
                    "format": "json",
                    "think": False,
                    "keep_alive": "15m",
                    "options": options,
                },
                DEFAULT_OLLAMA_CHAT_API,
                "message.content",
            )
        return (
            {
                "model": self.model,
                "prompt": build_prompt(
                    self.domain,
                    self.train_cases,
                    case,
                    max_examples_per_action=self.max_examples_per_action,
                ),
                "stream": False,
                "format": "json",
                "think": False,
                "keep_alive": "15m",
                "options": options,
            },
            self.api_url,
            "response",
        )

    def _use_chat_api(self) -> bool:
        model_name = self.model.lower()
        return "qwen3.5" in model_name or "gemma4" in model_name


def _extract_payload(raw_response: str) -> dict[str, Any]:
    stripped = raw_response.strip()
    if not stripped:
        return {}
    try:
        loaded = json.loads(stripped)
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        try:
            loaded = json.loads(match.group(0))
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            pass

    payload: dict[str, Any] = {}
    decision_match = re.search(r'"decision"\s*:\s*"([^"]+)"', stripped)
    action_match = re.search(r'"action_id"\s*:\s*(null|"[^"]*")', stripped)
    confidence_match = re.search(r'"confidence"\s*:\s*([0-9]+(?:\.[0-9]+)?)', stripped)
    reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', stripped)
    if decision_match:
        payload["decision"] = decision_match.group(1)
    if action_match:
        raw_action = action_match.group(1)
        payload["action_id"] = None if raw_action == "null" else raw_action.strip('"')
    if confidence_match:
        payload["confidence"] = confidence_match.group(1)
    if reason_match:
        payload["reason"] = reason_match.group(1)
    return payload


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))
