from __future__ import annotations

import json
from pathlib import Path

from kvrm_core.types import DecisionInput


def load_cases(path: str | Path) -> list[DecisionInput]:
    rows = []
    with Path(path).open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            rows.append(DecisionInput(
                case_id=payload['case_id'],
                features=payload['input_features'],
                expected_action_id=payload.get('expected_action_id'),
                supported=payload.get('supported', True),
                ood=payload.get('ood', False),
            ))
    rows.sort(key=lambda row: row.case_id)
    return rows
