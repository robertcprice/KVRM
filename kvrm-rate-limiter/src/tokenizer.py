"""Tokenizer for Rate Limiter KVRM input/output encoding."""

import torch
import torch.nn as nn
from typing import Optional
import math

from .schemas import (
    RateLimitInput,
    RateLimitOutput,
    Action,
    WarningCode,
    LogLevel,
    UserTier,
    AuthType,
    HttpMethod,
)


class RateLimiterTokenizer:
    """
    Encodes rate limiting context into tensor format for the KVRM model.

    Unlike traditional tokenizers, this encodes structured KV data into
    a fixed-size tensor representation optimized for the decision task.
    """

    # Vocabulary mappings
    TIER_TO_IDX = {tier: i for i, tier in enumerate(UserTier)}
    AUTH_TO_IDX = {auth: i for i, auth in enumerate(AuthType)}
    METHOD_TO_IDX = {method: i for i, method in enumerate(HttpMethod)}
    ACTION_TO_IDX = {action: i for i, action in enumerate(Action)}
    WARNING_TO_IDX = {warning: i for i, warning in enumerate(WarningCode)}
    LOGLEVEL_TO_IDX = {level: i for i, level in enumerate(LogLevel)}

    # Endpoint categories
    ENDPOINT_CATEGORIES = [
        "general", "search", "auth", "data", "admin", "upload",
        "download", "webhook", "streaming", "graphql"
    ]
    CATEGORY_TO_IDX = {cat: i for i, cat in enumerate(ENDPOINT_CATEGORIES)}

    # Feature dimensions
    NUM_CATEGORICAL_FEATURES = 4  # tier, auth, method, endpoint_category
    NUM_NUMERICAL_FEATURES = 18   # Various counters and metrics

    def __init__(self, max_delay_ms: int = 5000, max_quota: int = 10000):
        """
        Initialize the tokenizer.

        Args:
            max_delay_ms: Maximum delay in milliseconds (for normalization)
            max_quota: Maximum quota value (for normalization)
        """
        self.max_delay_ms = max_delay_ms
        self.max_quota = max_quota

        # Output dimensions
        self.num_actions = len(Action)
        self.num_warnings = len(WarningCode)
        self.num_loglevels = len(LogLevel)

    def encode_input(self, input_data: RateLimitInput) -> dict[str, torch.Tensor]:
        """
        Encode rate limit input into tensors.

        Returns:
            Dictionary with:
            - categorical: [4] tensor of category indices
            - numerical: [18] tensor of normalized numerical features
            - pattern_flags: [7] tensor of boolean flags
        """
        # Categorical features
        categorical = torch.tensor([
            self.TIER_TO_IDX.get(input_data.user.tier, 0),
            self.AUTH_TO_IDX.get(input_data.request.auth_type, 0),
            self.METHOD_TO_IDX.get(input_data.request.method, 0),
            self.CATEGORY_TO_IDX.get(input_data.request.endpoint_category, 0),
        ], dtype=torch.long)

        # Numerical features (normalized to roughly 0-1 range)
        numerical = torch.tensor([
            # Request context
            min(input_data.request.payload_size_bytes / 1_000_000, 10.0),  # MB, capped at 10
            input_data.request.estimated_cost / 10.0,  # Normalized cost

            # User request history (log-scaled)
            math.log1p(input_data.user.requests_last_minute) / 5.0,
            math.log1p(input_data.user.requests_last_hour) / 8.0,
            math.log1p(input_data.user.requests_last_day) / 12.0,

            # User metadata
            min(input_data.user.account_age_days / 365.0, 10.0),  # Years, capped at 10
            min(input_data.user.previous_throttles / 10.0, 5.0),
            min(input_data.user.previous_blocks / 5.0, 5.0),
            1.0 if input_data.user.payment_current else 0.0,
            input_data.user.avg_requests_per_minute / 100.0,
            min(input_data.user.request_variance / 50.0, 5.0),

            # System context
            input_data.system.current_load,  # Already 0-1
            math.log1p(input_data.system.endpoint_queue_depth) / 5.0,
            math.log1p(input_data.system.similar_requests_last_minute) / 8.0,
            input_data.system.error_rate_last_minute,  # Already 0-1
            input_data.system.available_capacity_percent / 100.0,

            # Pattern scores
            input_data.patterns.ip_reputation_score,  # Already 0-1

            # Derived features
            self._compute_urgency_score(input_data),
        ], dtype=torch.float32)

        # Pattern flags (boolean)
        pattern_flags = torch.tensor([
            input_data.patterns.burst_detected,
            input_data.patterns.unusual_time,
            input_data.patterns.new_ip,
            input_data.patterns.scripted_behavior,
            input_data.patterns.credential_stuffing_pattern,
            input_data.patterns.scraping_pattern,
            input_data.user.tier == UserTier.ENTERPRISE,  # Is premium?
        ], dtype=torch.float32)

        return {
            "categorical": categorical,
            "numerical": numerical,
            "pattern_flags": pattern_flags,
        }

    def _compute_urgency_score(self, input_data: RateLimitInput) -> float:
        """Compute a derived urgency score from multiple factors."""
        urgency = 0.0

        # High load increases urgency
        urgency += input_data.system.current_load * 0.3

        # Abuse patterns increase urgency
        if input_data.patterns.credential_stuffing_pattern:
            urgency += 0.4
        if input_data.patterns.scraping_pattern:
            urgency += 0.3
        if input_data.patterns.scripted_behavior:
            urgency += 0.1

        # Burst detection
        if input_data.patterns.burst_detected:
            urgency += 0.2

        # Poor IP reputation
        urgency += (1.0 - input_data.patterns.ip_reputation_score) * 0.3

        return min(urgency, 1.0)

    def encode_output(self, output: RateLimitOutput) -> dict[str, torch.Tensor]:
        """
        Encode rate limit output into tensors for training.

        Returns:
            Dictionary with:
            - action: scalar tensor (class index)
            - delay_ms: scalar tensor (normalized 0-1)
            - remaining_quota: scalar tensor (normalized 0-1)
            - quota_reset_seconds: scalar tensor (normalized 0-1)
            - warning_code: scalar tensor (class index)
            - log_level: scalar tensor (class index)
        """
        return {
            "action": torch.tensor(self.ACTION_TO_IDX[output.action], dtype=torch.long),
            "delay_ms": torch.tensor(
                min(output.delay_ms / self.max_delay_ms, 1.0), dtype=torch.float32
            ),
            "remaining_quota": torch.tensor(
                min(max(output.remaining_quota, 0) / self.max_quota, 1.0)
                if output.remaining_quota >= 0 else 1.0,
                dtype=torch.float32
            ),
            "quota_reset_seconds": torch.tensor(
                min(output.quota_reset_seconds / 3600.0, 1.0),  # Normalize to 1 hour
                dtype=torch.float32
            ),
            "warning_code": torch.tensor(
                self.WARNING_TO_IDX[output.warning_code], dtype=torch.long
            ),
            "log_level": torch.tensor(
                self.LOGLEVEL_TO_IDX[output.log_level], dtype=torch.long
            ),
        }

    def decode_output(self, predictions: dict[str, torch.Tensor]) -> RateLimitOutput:
        """
        Decode model predictions back to RateLimitOutput.

        Args:
            predictions: Dictionary with model outputs (logits or indices)

        Returns:
            Decoded RateLimitOutput object
        """
        # Get action (argmax if logits, direct if index)
        action_pred = predictions["action"]
        if action_pred.dim() > 0 and action_pred.shape[-1] > 1:
            action_idx = action_pred.argmax(dim=-1).item()
            action_confidence = torch.softmax(action_pred, dim=-1).max().item()
        else:
            action_idx = action_pred.item()
            action_confidence = 1.0

        # Get warning code
        warning_pred = predictions["warning_code"]
        if warning_pred.dim() > 0 and warning_pred.shape[-1] > 1:
            warning_idx = warning_pred.argmax(dim=-1).item()
        else:
            warning_idx = warning_pred.item()

        # Get log level
        loglevel_pred = predictions["log_level"]
        if loglevel_pred.dim() > 0 and loglevel_pred.shape[-1] > 1:
            loglevel_idx = loglevel_pred.argmax(dim=-1).item()
        else:
            loglevel_idx = loglevel_pred.item()

        # Decode numerical values
        delay_ms = int(predictions["delay_ms"].item() * self.max_delay_ms)
        remaining_quota = int(predictions["remaining_quota"].item() * self.max_quota)
        quota_reset_seconds = int(predictions["quota_reset_seconds"].item() * 3600)

        return RateLimitOutput(
            action=list(Action)[action_idx],
            delay_ms=delay_ms,
            remaining_quota=remaining_quota,
            quota_reset_seconds=quota_reset_seconds,
            warning_code=list(WarningCode)[warning_idx],
            log_level=list(LogLevel)[loglevel_idx],
            confidence=action_confidence,
        )

    @property
    def input_dim(self) -> int:
        """Total input dimension after encoding."""
        return (
            len(UserTier) +  # Tier embedding
            len(AuthType) +  # Auth embedding
            len(HttpMethod) +  # Method embedding
            len(self.ENDPOINT_CATEGORIES) +  # Category embedding
            self.NUM_NUMERICAL_FEATURES +
            7  # Pattern flags
        )

    @property
    def embedding_dims(self) -> dict[str, tuple[int, int]]:
        """Embedding dimensions for categorical features."""
        return {
            "tier": (len(UserTier), 8),
            "auth": (len(AuthType), 8),
            "method": (len(HttpMethod), 8),
            "category": (len(self.ENDPOINT_CATEGORIES), 8),
        }
