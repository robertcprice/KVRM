from __future__ import annotations

import json
from pathlib import Path

from .types import AuditRecord, DecisionResult


def audit_record_to_dict(record: AuditRecord) -> dict:
    return record.model_dump()


def decision_result_to_case_result(result: DecisionResult, expected_action_id: str | None, supported: bool, ood: bool) -> dict:
    selected_evidence = result.audit_record.selected_evidence or {}
    support_gate = selected_evidence.get("support_gate")
    support_gate_filtered_count = int(selected_evidence.get("support_gate_filtered_count") or 0)
    support_gate_rescued = support_gate_filtered_count > 0 and result.final_status.value == "executed"
    return {
        "case_id": result.case_id,
        "supported": supported,
        "ood": ood,
        "expected_action_id": expected_action_id,
        "selected_action_id": result.selected_action_id,
        "final_status": result.final_status.value,
        "confidence": result.confidence,
        "abstained": result.abstained,
        "fallback_used": result.fallback_used,
        "valid": result.valid,
        "correct": result.correct,
        "latency_ms": result.latency_ms,
        "validation_reason": result.validation_reason,
        "execution_status": result.execution_result.status.value if result.execution_result else None,
        "support_gate": support_gate,
        "support_gate_filtered_count": support_gate_filtered_count,
        "support_gate_rescued": support_gate_rescued,
    }


def write_audit_jsonl(path: str | Path, records: list[AuditRecord]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record.model_dump(), sort_keys=True) + "\n")
