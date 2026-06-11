"""Input/Output schemas for the Rate Limiter KVRM."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class UserTier(Enum):
    """User subscription tiers."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class AuthType(Enum):
    """Authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    JWT = "jwt"
    SESSION = "session"


class HttpMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class Action(Enum):
    """Rate limiting actions."""
    ALLOW = "allow"
    THROTTLE_SOFT = "throttle_soft"      # Add delay, allow request
    THROTTLE_HARD = "throttle_hard"      # Add longer delay, allow request
    WARN = "warn"                         # Allow but warn user
    BLOCK_TEMPORARY = "block_temporary"   # Block for short period
    BLOCK_EXTENDED = "block_extended"     # Block for longer period
    CAPTCHA = "captcha"                   # Require human verification


class WarningCode(Enum):
    """Warning codes for rate limiting responses."""
    NONE = "none"
    BURST_LIMIT_APPROACHING = "burst_limit_approaching"
    HOURLY_LIMIT_APPROACHING = "hourly_limit_approaching"
    DAILY_LIMIT_APPROACHING = "daily_limit_approaching"
    UNUSUAL_PATTERN_DETECTED = "unusual_pattern_detected"
    HIGH_SYSTEM_LOAD = "high_system_load"
    QUOTA_EXHAUSTED = "quota_exhausted"
    ABUSE_SUSPECTED = "abuse_suspected"


class LogLevel(Enum):
    """Log levels for rate limiting events."""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RequestContext:
    """Information about the incoming request."""
    endpoint: str
    method: HttpMethod
    payload_size_bytes: int = 0
    auth_type: AuthType = AuthType.NONE

    # Endpoint classification (for learned patterns)
    endpoint_category: str = "general"  # search, auth, data, admin, etc.
    estimated_cost: float = 1.0  # Relative computational cost


@dataclass
class UserContext:
    """Information about the user making the request."""
    user_id: str
    tier: UserTier

    # Request history
    requests_last_minute: int = 0
    requests_last_hour: int = 0
    requests_last_day: int = 0

    # Account metadata
    account_age_days: int = 0
    previous_throttles: int = 0
    previous_blocks: int = 0
    payment_current: bool = True

    # Behavioral signals
    avg_requests_per_minute: float = 0.0
    request_variance: float = 0.0  # How consistent is their usage


@dataclass
class SystemContext:
    """Information about current system state."""
    current_load: float = 0.0  # 0.0 - 1.0
    endpoint_queue_depth: int = 0
    similar_requests_last_minute: int = 0
    error_rate_last_minute: float = 0.0

    # Capacity info
    available_capacity_percent: float = 100.0


@dataclass
class PatternFlags:
    """Behavioral pattern detection flags."""
    burst_detected: bool = False
    unusual_time: bool = False  # Request at unusual hour for this user
    new_ip: bool = False
    ip_reputation_score: float = 1.0  # 0.0 = bad, 1.0 = good
    scripted_behavior: bool = False  # Patterns suggesting automation
    credential_stuffing_pattern: bool = False
    scraping_pattern: bool = False


@dataclass
class RateLimitInput:
    """Complete input to the rate limiter."""
    request: RequestContext
    user: UserContext
    system: SystemContext
    patterns: PatternFlags

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "request": {
                "endpoint": self.request.endpoint,
                "method": self.request.method.value,
                "payload_size_bytes": self.request.payload_size_bytes,
                "auth_type": self.request.auth_type.value,
                "endpoint_category": self.request.endpoint_category,
                "estimated_cost": self.request.estimated_cost,
            },
            "user": {
                "user_id": self.user.user_id,
                "tier": self.user.tier.value,
                "requests_last_minute": self.user.requests_last_minute,
                "requests_last_hour": self.user.requests_last_hour,
                "requests_last_day": self.user.requests_last_day,
                "account_age_days": self.user.account_age_days,
                "previous_throttles": self.user.previous_throttles,
                "previous_blocks": self.user.previous_blocks,
                "payment_current": self.user.payment_current,
                "avg_requests_per_minute": self.user.avg_requests_per_minute,
                "request_variance": self.user.request_variance,
            },
            "system": {
                "current_load": self.system.current_load,
                "endpoint_queue_depth": self.system.endpoint_queue_depth,
                "similar_requests_last_minute": self.system.similar_requests_last_minute,
                "error_rate_last_minute": self.system.error_rate_last_minute,
                "available_capacity_percent": self.system.available_capacity_percent,
            },
            "patterns": {
                "burst_detected": self.patterns.burst_detected,
                "unusual_time": self.patterns.unusual_time,
                "new_ip": self.patterns.new_ip,
                "ip_reputation_score": self.patterns.ip_reputation_score,
                "scripted_behavior": self.patterns.scripted_behavior,
                "credential_stuffing_pattern": self.patterns.credential_stuffing_pattern,
                "scraping_pattern": self.patterns.scraping_pattern,
            },
        }


@dataclass
class RateLimitOutput:
    """Output from the rate limiter."""
    action: Action
    delay_ms: int = 0
    remaining_quota: int = -1  # -1 means unlimited
    quota_reset_seconds: int = 0
    warning_code: WarningCode = WarningCode.NONE
    log_level: LogLevel = LogLevel.INFO
    confidence: float = 1.0

    # For explainability
    reason_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action.value,
            "delay_ms": self.delay_ms,
            "remaining_quota": self.remaining_quota,
            "quota_reset_seconds": self.quota_reset_seconds,
            "warning_code": self.warning_code.value,
            "log_level": self.log_level.value,
            "confidence": self.confidence,
            "reason_flags": self.reason_flags,
        }


# Tier-based default quotas (for reference, not hard-coded in model)
TIER_QUOTAS = {
    UserTier.FREE: {"per_minute": 10, "per_hour": 100, "per_day": 500},
    UserTier.BASIC: {"per_minute": 30, "per_hour": 500, "per_day": 5000},
    UserTier.PROFESSIONAL: {"per_minute": 100, "per_hour": 2000, "per_day": 20000},
    UserTier.ENTERPRISE: {"per_minute": 500, "per_hour": 10000, "per_day": 100000},
}
