from __future__ import annotations

from qwen_baseline.data_loader import DOMAIN_ORDER
from qwen_baseline.domain_schemas import DOMAINS
from qwen_baseline.ollama_runner import parse_ollama_response


def test_live_domain_configs_cover_all_canonical_demos() -> None:
    assert DOMAIN_ORDER == ["soc", "sre", "drone", "grid", "finance", "medical", "customer_support", "content_moderation"]
    assert sorted(DOMAINS) == sorted(DOMAIN_ORDER)
    assert DOMAINS["sre"]["feature_order"][0] == "latency"
    assert DOMAINS["sre"]["feature_order"][-1] == "telemetry_confidence"
    assert DOMAINS["drone"]["fallback"] == "manual_handoff"
    assert DOMAINS["grid"]["labels"][2] == "transfer_load"


def test_parse_ollama_response_normalizes_abstain_marker() -> None:
    raw = '{"decision":"abstain","action_id":"ABSTAIN","confidence":0.72,"reason":"unsupported"}'
    parsed = parse_ollama_response(raw, allowed_labels=["restart_service", "page_human_operator"])
    assert parsed["decision"] == "abstain"
    assert parsed["action_id"] is None
    assert parsed["valid"] is True
    assert parsed["confidence"] == 0.72


def test_parse_ollama_response_rejects_empty_object() -> None:
    parsed = parse_ollama_response("{}", allowed_labels=["restart_service"])
    assert parsed["decision"] == "invalid"
    assert parsed["valid"] is False


def test_parse_ollama_response_accepts_label_in_decision_field() -> None:
    raw = '{"decision":"approve_low_risk","action_id":"approve_low_risk","confidence":1.0,"reason":"ok"}'
    parsed = parse_ollama_response(raw, allowed_labels=["approve_low_risk", "manual_review"])
    assert parsed["decision"] == "action"
    assert parsed["action_id"] == "approve_low_risk"
    assert parsed["valid"] is True
