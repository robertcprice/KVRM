from __future__ import annotations

import json
from typing import Any


def normalize_features(features: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(features, sort_keys=True))


def feature_key(features: dict[str, Any]) -> str:
    normalized = normalize_features(features)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))
