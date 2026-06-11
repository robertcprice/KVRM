"""
Traditional rule-based rate limiters for comparison.

These implement common rate limiting algorithms to serve as baselines
for comparing against the KVRM approach.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

from .schemas import (
    RateLimitInput,
    RateLimitOutput,
    Action,
    WarningCode,
    LogLevel,
    UserTier,
    TIER_QUOTAS,
)


@dataclass
class RateLimitState:
    """State for tracking a user's rate limit."""
    tokens: float = 0.0
    last_update: float = 0.0
    request_count: int = 0
    window_start: float = 0.0


class BaselineRateLimiter(ABC):
    """Abstract base class for baseline rate limiters."""

    def __init__(self):
        self.state: dict[str, RateLimitState] = defaultdict(RateLimitState)

    @abstractmethod
    def check(self, input_data: RateLimitInput) -> RateLimitOutput:
        """Check if request should be rate limited."""
        pass

    def reset(self):
        """Reset all state."""
        self.state.clear()


class TokenBucketLimiter(BaselineRateLimiter):
    """
    Token Bucket rate limiter.

    Tokens are added at a fixed rate, consumed by requests.
    Allows bursts up to bucket capacity.
    """

    def __init__(
        self,
        default_capacity: int = 100,
        default_refill_rate: float = 10.0,  # tokens per second
    ):
        super().__init__()
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate

        # Tier-specific settings
        self.tier_settings = {
            UserTier.FREE: {"capacity": 20, "rate": 2.0},
            UserTier.BASIC: {"capacity": 50, "rate": 5.0},
            UserTier.PROFESSIONAL: {"capacity": 200, "rate": 20.0},
            UserTier.ENTERPRISE: {"capacity": 1000, "rate": 100.0},
        }

    def check(self, input_data: RateLimitInput) -> RateLimitOutput:
        user_id = input_data.user.user_id
        tier = input_data.user.tier
        now = time.time()

        # Get tier settings
        settings = self.tier_settings.get(tier, {
            "capacity": self.default_capacity,
            "rate": self.default_refill_rate
        })
        capacity = settings["capacity"]
        rate = settings["rate"]

        # Get or create state
        state = self.state[user_id]

        # Initialize if new
        if state.last_update == 0:
            state.tokens = capacity
            state.last_update = now

        # Refill tokens
        elapsed = now - state.last_update
        state.tokens = min(capacity, state.tokens + elapsed * rate)
        state.last_update = now

        # Check if request can proceed
        cost = input_data.request.estimated_cost

        if state.tokens >= cost:
            # Allow request
            state.tokens -= cost
            remaining = int(state.tokens)

            # Warning if running low
            if state.tokens < capacity * 0.2:
                return RateLimitOutput(
                    action=Action.WARN,
                    remaining_quota=remaining,
                    warning_code=WarningCode.BURST_LIMIT_APPROACHING,
                    log_level=LogLevel.INFO,
                )

            return RateLimitOutput(
                action=Action.ALLOW,
                remaining_quota=remaining,
                warning_code=WarningCode.NONE,
                log_level=LogLevel.DEBUG,
            )
        else:
            # Rate limited - calculate wait time
            tokens_needed = cost - state.tokens
            wait_seconds = tokens_needed / rate
            delay_ms = int(wait_seconds * 1000)

            return RateLimitOutput(
                action=Action.THROTTLE_HARD if delay_ms > 1000 else Action.THROTTLE_SOFT,
                delay_ms=min(delay_ms, 5000),
                remaining_quota=0,
                quota_reset_seconds=int(wait_seconds) + 1,
                warning_code=WarningCode.QUOTA_EXHAUSTED,
                log_level=LogLevel.WARN,
            )


class SlidingWindowLimiter(BaselineRateLimiter):
    """
    Sliding Window Counter rate limiter.

    Approximates a sliding window using current and previous window counts.
    More accurate than fixed windows, less memory than sliding logs.
    """

    def __init__(self, window_seconds: int = 60):
        super().__init__()
        self.window_seconds = window_seconds
        self.window_counts: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    def check(self, input_data: RateLimitInput) -> RateLimitOutput:
        user_id = input_data.user.user_id
        tier = input_data.user.tier
        now = time.time()

        # Get quota for tier
        quota = TIER_QUOTAS[tier]["per_minute"]

        # Current window
        current_window = int(now / self.window_seconds)
        window_position = (now % self.window_seconds) / self.window_seconds

        # Get counts
        counts = self.window_counts[user_id]
        current_count = counts.get(current_window, 0)
        prev_count = counts.get(current_window - 1, 0)

        # Weighted count (sliding window approximation)
        weighted_count = current_count + prev_count * (1 - window_position)

        if weighted_count < quota:
            # Allow and increment
            counts[current_window] = current_count + 1

            # Cleanup old windows
            old_windows = [w for w in counts if w < current_window - 1]
            for w in old_windows:
                del counts[w]

            remaining = int(quota - weighted_count - 1)

            if remaining < quota * 0.2:
                return RateLimitOutput(
                    action=Action.WARN,
                    remaining_quota=remaining,
                    quota_reset_seconds=int(self.window_seconds * (1 - window_position)),
                    warning_code=WarningCode.BURST_LIMIT_APPROACHING,
                    log_level=LogLevel.INFO,
                )

            return RateLimitOutput(
                action=Action.ALLOW,
                remaining_quota=remaining,
                quota_reset_seconds=int(self.window_seconds * (1 - window_position)),
                warning_code=WarningCode.NONE,
                log_level=LogLevel.DEBUG,
            )
        else:
            # Rate limited
            reset_seconds = int(self.window_seconds * (1 - window_position)) + 1

            return RateLimitOutput(
                action=Action.BLOCK_TEMPORARY,
                remaining_quota=0,
                quota_reset_seconds=reset_seconds,
                warning_code=WarningCode.QUOTA_EXHAUSTED,
                log_level=LogLevel.WARN,
            )


class RuleBasedLimiter(BaselineRateLimiter):
    """
    Rule-based rate limiter that attempts to capture nuanced decisions.

    This demonstrates the complexity of trying to encode all the edge cases
    that KVRM learns automatically.
    """

    def __init__(self):
        super().__init__()
        self.token_limiter = TokenBucketLimiter()
        self.window_limiter = SlidingWindowLimiter()

    def check(self, input_data: RateLimitInput) -> RateLimitOutput:
        """
        Complex rule-based checking.

        This shows how many conditions are needed to approximate
        what KVRM learns - and it still misses edge cases.
        """

        # Rule 1: Immediate block for credential stuffing
        if input_data.patterns.credential_stuffing_pattern:
            if input_data.patterns.ip_reputation_score < 0.5:
                return RateLimitOutput(
                    action=Action.BLOCK_EXTENDED,
                    warning_code=WarningCode.ABUSE_SUSPECTED,
                    log_level=LogLevel.CRITICAL,
                )
            else:
                return RateLimitOutput(
                    action=Action.CAPTCHA,
                    warning_code=WarningCode.ABUSE_SUSPECTED,
                    log_level=LogLevel.ERROR,
                )

        # Rule 2: Scraping detection
        if input_data.patterns.scraping_pattern:
            if input_data.user.tier in [UserTier.FREE, UserTier.BASIC]:
                if input_data.user.previous_throttles > 2:
                    return RateLimitOutput(
                        action=Action.BLOCK_TEMPORARY,
                        warning_code=WarningCode.ABUSE_SUSPECTED,
                        log_level=LogLevel.WARN,
                    )
                else:
                    return RateLimitOutput(
                        action=Action.THROTTLE_HARD,
                        delay_ms=2000,
                        warning_code=WarningCode.UNUSUAL_PATTERN_DETECTED,
                        log_level=LogLevel.WARN,
                    )

        # Rule 3: System overload protection
        if input_data.system.current_load > 0.9:
            if input_data.user.tier != UserTier.ENTERPRISE:
                delay = int((input_data.system.current_load - 0.8) * 2500)
                return RateLimitOutput(
                    action=Action.THROTTLE_SOFT,
                    delay_ms=delay,
                    warning_code=WarningCode.HIGH_SYSTEM_LOAD,
                    log_level=LogLevel.INFO,
                )

        # Rule 4: New account with high activity
        if input_data.user.account_age_days < 7:
            if input_data.user.requests_last_minute > 20:
                if input_data.patterns.ip_reputation_score < 0.7:
                    return RateLimitOutput(
                        action=Action.THROTTLE_HARD,
                        delay_ms=1000,
                        warning_code=WarningCode.UNUSUAL_PATTERN_DETECTED,
                        log_level=LogLevel.INFO,
                    )

        # Rule 5: Bot-like behavior (low variance)
        if input_data.user.request_variance < 0.3:
            if input_data.user.requests_last_minute > 30:
                if input_data.patterns.scripted_behavior:
                    return RateLimitOutput(
                        action=Action.THROTTLE_SOFT,
                        delay_ms=500,
                        warning_code=WarningCode.UNUSUAL_PATTERN_DETECTED,
                        log_level=LogLevel.INFO,
                    )

        # Rule 6: Premium user leniency
        if input_data.user.tier == UserTier.ENTERPRISE:
            if input_data.patterns.burst_detected:
                # Trust enterprise users with bursts
                return RateLimitOutput(
                    action=Action.ALLOW,
                    warning_code=WarningCode.NONE,
                    log_level=LogLevel.INFO,
                )

        # Rule 7: Established user leniency
        if input_data.user.account_age_days > 180:
            if input_data.user.previous_throttles == 0:
                if input_data.patterns.burst_detected:
                    # Trust established users
                    return RateLimitOutput(
                        action=Action.WARN,
                        warning_code=WarningCode.BURST_LIMIT_APPROACHING,
                        log_level=LogLevel.INFO,
                    )

        # Rule 8: IP reputation factor
        if input_data.patterns.ip_reputation_score < 0.3:
            if input_data.patterns.new_ip:
                return RateLimitOutput(
                    action=Action.THROTTLE_SOFT,
                    delay_ms=300,
                    warning_code=WarningCode.UNUSUAL_PATTERN_DETECTED,
                    log_level=LogLevel.INFO,
                )

        # Fallback: Use token bucket for basic rate limiting
        return self.token_limiter.check(input_data)


def compare_limiters(input_data: RateLimitInput) -> dict[str, RateLimitOutput]:
    """Compare different rate limiters on the same input."""
    limiters = {
        "token_bucket": TokenBucketLimiter(),
        "sliding_window": SlidingWindowLimiter(),
        "rule_based": RuleBasedLimiter(),
    }

    results = {}
    for name, limiter in limiters.items():
        results[name] = limiter.check(input_data)

    return results


# Count lines of code in rule-based limiter
def count_rule_complexity():
    """Demonstrate the complexity of rule-based approaches."""
    import inspect

    source = inspect.getsource(RuleBasedLimiter.check)
    lines = [l for l in source.split('\n') if l.strip() and not l.strip().startswith('#')]

    print(f"Rule-based limiter: {len(lines)} lines of logic")
    print("And it still misses many edge cases that KVRM can learn!")

    # Count conditions
    conditions = source.count('if ') + source.count('elif ')
    print(f"Number of conditional branches: {conditions}")


if __name__ == "__main__":
    count_rule_complexity()
