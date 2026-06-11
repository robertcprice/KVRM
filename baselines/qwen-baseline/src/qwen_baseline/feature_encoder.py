"""Encode heterogeneous case features into numeric vectors.

Shared by all live demo domains. Each domain defines a FEATURE_SCHEMA
that maps feature names to either:
  - 'numeric' (pass through as float)
  - list[object] of categorical values (one-hot encode, with 'unknown' bin)
"""
from __future__ import annotations

import numpy as np


def encode_features(
    features: dict,
    schema: dict[str, str | list[object]],
    feature_order: list[str],
) -> np.ndarray:
    """Encode a single case's features into a flat float vector."""
    parts: list[float] = []
    for fname in feature_order:
        spec = schema[fname]
        val = features.get(fname)
        if spec == "numeric":
            try:
                parts.append(float(val))
            except (TypeError, ValueError):
                parts.append(0.0)  # missing -> 0
        elif isinstance(spec, list):
            # one-hot with unknown bin
            one_hot = [0.0] * (len(spec) + 1)
            if val in spec:
                one_hot[spec.index(val)] = 1.0
            else:
                one_hot[-1] = 1.0  # unknown bin
            parts.extend(one_hot)
        else:
            parts.append(0.0)
    return np.array(parts, dtype=np.float64)


def encode_batch(
    cases: list[dict],
    schema: dict[str, str | list[object]],
    feature_order: list[str],
) -> np.ndarray:
    """Encode a batch of cases into a 2D feature matrix."""
    return np.array([
        encode_features(c["input_features"], schema, feature_order)
        for c in cases
    ])
