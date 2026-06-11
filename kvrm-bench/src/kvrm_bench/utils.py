"""Shared utilities for kvrm-bench modules."""
from __future__ import annotations

from typing import Any


def value_token(value: Any) -> str:
    """Convert a feature value to a safe case-ID token string."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".").replace("-", "m").replace(".", "p")
    return str(value)
