"""
Synthetic Training Data Generator for Rate Limiter KVRM.

Generates diverse scenarios covering:
- Normal users with various tiers and usage patterns
- Legitimate burst patterns (product launches, viral content)
- Abuse patterns (scrapers, credential stuffing, DDoS)
- Edge cases (new premium users, system overload, unusual timing)

Labels are generated using expert rules that capture the "judgment" we want
the model to learn.
"""

import random
import json
from dataclasses import dataclass
from typing import Generator
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas import (
    RateLimitInput,
    RateLimitOutput,
    RequestContext,
    UserContext,
    SystemContext,
    PatternFlags,
    UserTier,
    AuthType,
    HttpMethod,
    Action,
    WarningCode,
    LogLevel,
    TIER_QUOTAS,
)


@dataclass
class ScenarioConfig:
    """Configuration for a scenario type."""
    name: str
    weight: float  # Probability weight for sampling


class RateLimitDataGenerator:
    """
    Generates synthetic rate limiting training data.

    The key insight is that labels come from expert rules that encode
    the "judgment" we want the model to learn - not simple thresholds,
    but nuanced decisions based on multiple factors.
    """

    SCENARIOS = [
        ScenarioConfig("normal_light", 0.25),
        ScenarioConfig("normal_moderate", 0.20),
        ScenarioConfig("normal_heavy", 0.10),
        ScenarioConfig("legitimate_burst", 0.10),
        ScenarioConfig("new_user", 0.08),
        ScenarioConfig("premium_user", 0.07),
        ScenarioConfig("scraper_attempt", 0.05),
        ScenarioConfig("credential_stuffing", 0.03),
        ScenarioConfig("ddos_pattern", 0.02),
        ScenarioConfig("system_overload", 0.05),
        ScenarioConfig("edge_case", 0.05),
    ]

    ENDPOINTS = [
        ("/api/v1/search", "search", 2.0),
        ("/api/v1/users", "data", 1.0),
        ("/api/v1/auth/login", "auth", 1.5),
        ("/api/v1/auth/register", "auth", 2.0),
        ("/api/v1/data/export", "download", 5.0),
        ("/api/v1/upload", "upload", 3.0),
        ("/api/v1/admin/users", "admin", 1.0),
        ("/api/v1/webhook", "webhook", 0.5),
        ("/api/v1/stream", "streaming", 4.0),
        ("/graphql", "graphql", 3.0),
    ]

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, n_samples: int) -> Generator[tuple[RateLimitInput, RateLimitOutput], None, None]:
        """Generate n_samples training examples."""
        # Compute cumulative weights for scenario sampling
        total_weight = sum(s.weight for s in self.SCENARIOS)
        weights = [s.weight / total_weight for s in self.SCENARIOS]

        for _ in range(n_samples):
            # Sample scenario
            scenario = self.rng.choices(self.SCENARIOS, weights=weights, k=1)[0]

            # Generate input based on scenario
            input_data = self._generate_input(scenario.name)

            # Generate label using expert rules
            output = self._label_with_expert_rules(input_data, scenario.name)

            yield input_data, output

    def _generate_input(self, scenario: str) -> RateLimitInput:
        """Generate input data for a scenario."""
        if scenario == "normal_light":
            return self._gen_normal_light()
        elif scenario == "normal_moderate":
            return self._gen_normal_moderate()
        elif scenario == "normal_heavy":
            return self._gen_normal_heavy()
        elif scenario == "legitimate_burst":
            return self._gen_legitimate_burst()
        elif scenario == "new_user":
            return self._gen_new_user()
        elif scenario == "premium_user":
            return self._gen_premium_user()
        elif scenario == "scraper_attempt":
            return self._gen_scraper()
        elif scenario == "credential_stuffing":
            return self._gen_credential_stuffing()
        elif scenario == "ddos_pattern":
            return self._gen_ddos()
        elif scenario == "system_overload":
            return self._gen_system_overload()
        else:  # edge_case
            return self._gen_edge_case()

    def _random_endpoint(self) -> tuple[str, str, float]:
        return self.rng.choice(self.ENDPOINTS)

    def _random_tier(self, weights: list[float] = None) -> UserTier:
        tiers = list(UserTier)
        if weights is None:
            weights = [0.4, 0.3, 0.2, 0.1]  # Default: more free users
        return self.rng.choices(tiers, weights=weights, k=1)[0]

    def _gen_normal_light(self) -> RateLimitInput:
        """Normal user with light usage."""
        endpoint, category, cost = self._random_endpoint()
        tier = self._random_tier()

        return RateLimitInput(
            request=RequestContext(
                endpoint=endpoint,
                method=self.rng.choice([HttpMethod.GET, HttpMethod.POST]),
                payload_size_bytes=self.rng.randint(100, 5000),
                auth_type=self.rng.choice([AuthType.API_KEY, AuthType.JWT]),
                endpoint_category=category,
                estimated_cost=cost,
            ),
            user=UserContext(
                user_id=f"u_{self.rng.randint(1, 100000)}",
                tier=tier,
                requests_last_minute=self.rng.randint(0, 5),
                requests_last_hour=self.rng.randint(0, 50),
                requests_last_day=self.rng.randint(0, 200),
                account_age_days=self.rng.randint(30, 1000),
                previous_throttles=0,
                previous_blocks=0,
                payment_current=True,
                avg_requests_per_minute=self.rng.uniform(1, 5),
                request_variance=self.rng.uniform(0.5, 2.0),
            ),
            system=SystemContext(
                current_load=self.rng.uniform(0.1, 0.5),
                endpoint_queue_depth=self.rng.randint(0, 10),
                similar_requests_last_minute=self.rng.randint(100, 500),
                error_rate_last_minute=self.rng.uniform(0.0, 0.02),
                available_capacity_percent=self.rng.uniform(60, 95),
            ),
            patterns=PatternFlags(
                burst_detected=False,
                unusual_time=False,
                new_ip=self.rng.random() < 0.1,
                ip_reputation_score=self.rng.uniform(0.8, 1.0),
                scripted_behavior=False,
                credential_stuffing_pattern=False,
                scraping_pattern=False,
            ),
        )

    def _gen_normal_moderate(self) -> RateLimitInput:
        """Normal user with moderate usage."""
        input_data = self._gen_normal_light()
        # Increase usage
        input_data.user.requests_last_minute = self.rng.randint(5, 20)
        input_data.user.requests_last_hour = self.rng.randint(50, 300)
        input_data.user.requests_last_day = self.rng.randint(200, 1000)
        input_data.user.avg_requests_per_minute = self.rng.uniform(5, 15)
        return input_data

    def _gen_normal_heavy(self) -> RateLimitInput:
        """Normal user with heavy but legitimate usage."""
        input_data = self._gen_normal_moderate()
        # Heavy usage, but from established professional/enterprise user
        input_data.user.tier = self.rng.choice([UserTier.PROFESSIONAL, UserTier.ENTERPRISE])
        input_data.user.requests_last_minute = self.rng.randint(20, 80)
        input_data.user.requests_last_hour = self.rng.randint(500, 1500)
        input_data.user.account_age_days = self.rng.randint(180, 1000)
        return input_data

    def _gen_legitimate_burst(self) -> RateLimitInput:
        """Legitimate burst (e.g., product launch, viral moment)."""
        input_data = self._gen_normal_moderate()
        # Sudden spike but from good user
        input_data.user.requests_last_minute = self.rng.randint(30, 100)
        input_data.user.account_age_days = self.rng.randint(90, 500)
        input_data.user.previous_throttles = self.rng.randint(0, 1)
        input_data.patterns.burst_detected = True
        input_data.patterns.ip_reputation_score = self.rng.uniform(0.85, 1.0)
        input_data.patterns.scripted_behavior = False
        return input_data

    def _gen_new_user(self) -> RateLimitInput:
        """New user (harder to judge intent)."""
        input_data = self._gen_normal_light()
        input_data.user.account_age_days = self.rng.randint(0, 7)
        input_data.user.requests_last_minute = self.rng.randint(5, 30)
        input_data.patterns.new_ip = True
        input_data.patterns.ip_reputation_score = self.rng.uniform(0.5, 0.9)
        return input_data

    def _gen_premium_user(self) -> RateLimitInput:
        """Premium user who should get better treatment."""
        input_data = self._gen_normal_heavy()
        input_data.user.tier = UserTier.ENTERPRISE
        input_data.user.payment_current = True
        input_data.user.account_age_days = self.rng.randint(365, 2000)
        input_data.user.previous_throttles = 0
        input_data.patterns.burst_detected = self.rng.random() < 0.3
        return input_data

    def _gen_scraper(self) -> RateLimitInput:
        """Scraper/bot pattern."""
        endpoint, category, cost = self._random_endpoint()

        return RateLimitInput(
            request=RequestContext(
                endpoint=endpoint,
                method=HttpMethod.GET,
                payload_size_bytes=self.rng.randint(50, 200),
                auth_type=self.rng.choice([AuthType.NONE, AuthType.API_KEY]),
                endpoint_category=category,
                estimated_cost=cost,
            ),
            user=UserContext(
                user_id=f"u_{self.rng.randint(1, 100000)}",
                tier=self.rng.choice([UserTier.FREE, UserTier.BASIC]),
                requests_last_minute=self.rng.randint(50, 200),
                requests_last_hour=self.rng.randint(500, 3000),
                requests_last_day=self.rng.randint(5000, 20000),
                account_age_days=self.rng.randint(1, 30),
                previous_throttles=self.rng.randint(2, 10),
                previous_blocks=self.rng.randint(0, 3),
                payment_current=self.rng.random() < 0.3,
                avg_requests_per_minute=self.rng.uniform(30, 100),
                request_variance=self.rng.uniform(0.1, 0.5),  # Very consistent = bot
            ),
            system=SystemContext(
                current_load=self.rng.uniform(0.3, 0.8),
                endpoint_queue_depth=self.rng.randint(10, 50),
                similar_requests_last_minute=self.rng.randint(500, 2000),
                error_rate_last_minute=self.rng.uniform(0.01, 0.05),
                available_capacity_percent=self.rng.uniform(40, 80),
            ),
            patterns=PatternFlags(
                burst_detected=True,
                unusual_time=self.rng.random() < 0.4,
                new_ip=self.rng.random() < 0.3,
                ip_reputation_score=self.rng.uniform(0.2, 0.6),
                scripted_behavior=True,
                credential_stuffing_pattern=False,
                scraping_pattern=True,
            ),
        )

    def _gen_credential_stuffing(self) -> RateLimitInput:
        """Credential stuffing attack pattern."""
        return RateLimitInput(
            request=RequestContext(
                endpoint="/api/v1/auth/login",
                method=HttpMethod.POST,
                payload_size_bytes=self.rng.randint(100, 300),
                auth_type=AuthType.NONE,
                endpoint_category="auth",
                estimated_cost=1.5,
            ),
            user=UserContext(
                user_id=f"u_{self.rng.randint(1, 100000)}",
                tier=UserTier.FREE,
                requests_last_minute=self.rng.randint(20, 100),
                requests_last_hour=self.rng.randint(200, 1000),
                requests_last_day=self.rng.randint(500, 5000),
                account_age_days=self.rng.randint(0, 10),
                previous_throttles=self.rng.randint(3, 15),
                previous_blocks=self.rng.randint(1, 5),
                payment_current=False,
                avg_requests_per_minute=self.rng.uniform(20, 80),
                request_variance=self.rng.uniform(0.05, 0.2),
            ),
            system=SystemContext(
                current_load=self.rng.uniform(0.4, 0.9),
                endpoint_queue_depth=self.rng.randint(20, 100),
                similar_requests_last_minute=self.rng.randint(1000, 5000),
                error_rate_last_minute=self.rng.uniform(0.3, 0.7),  # Many failed logins
                available_capacity_percent=self.rng.uniform(20, 60),
            ),
            patterns=PatternFlags(
                burst_detected=True,
                unusual_time=self.rng.random() < 0.6,
                new_ip=True,
                ip_reputation_score=self.rng.uniform(0.0, 0.3),
                scripted_behavior=True,
                credential_stuffing_pattern=True,
                scraping_pattern=False,
            ),
        )

    def _gen_ddos(self) -> RateLimitInput:
        """DDoS-like pattern."""
        endpoint, category, cost = self._random_endpoint()

        return RateLimitInput(
            request=RequestContext(
                endpoint=endpoint,
                method=self.rng.choice([HttpMethod.GET, HttpMethod.POST]),
                payload_size_bytes=self.rng.randint(10, 100),
                auth_type=AuthType.NONE,
                endpoint_category=category,
                estimated_cost=cost,
            ),
            user=UserContext(
                user_id=f"u_{self.rng.randint(1, 100000)}",
                tier=UserTier.FREE,
                requests_last_minute=self.rng.randint(100, 500),
                requests_last_hour=self.rng.randint(1000, 10000),
                requests_last_day=self.rng.randint(5000, 50000),
                account_age_days=self.rng.randint(0, 5),
                previous_throttles=self.rng.randint(5, 20),
                previous_blocks=self.rng.randint(2, 10),
                payment_current=False,
                avg_requests_per_minute=self.rng.uniform(100, 500),
                request_variance=self.rng.uniform(0.0, 0.1),
            ),
            system=SystemContext(
                current_load=self.rng.uniform(0.8, 1.0),
                endpoint_queue_depth=self.rng.randint(100, 500),
                similar_requests_last_minute=self.rng.randint(5000, 20000),
                error_rate_last_minute=self.rng.uniform(0.1, 0.5),
                available_capacity_percent=self.rng.uniform(0, 30),
            ),
            patterns=PatternFlags(
                burst_detected=True,
                unusual_time=True,
                new_ip=True,
                ip_reputation_score=self.rng.uniform(0.0, 0.2),
                scripted_behavior=True,
                credential_stuffing_pattern=False,
                scraping_pattern=self.rng.random() < 0.5,
            ),
        )

    def _gen_system_overload(self) -> RateLimitInput:
        """System under heavy load - even normal users may need throttling."""
        input_data = self._gen_normal_moderate()
        input_data.system.current_load = self.rng.uniform(0.85, 0.98)
        input_data.system.endpoint_queue_depth = self.rng.randint(50, 200)
        input_data.system.available_capacity_percent = self.rng.uniform(5, 20)
        return input_data

    def _gen_edge_case(self) -> RateLimitInput:
        """Various edge cases."""
        edge_type = self.rng.choice([
            "premium_burst",      # Premium user with unusual burst
            "reformed_abuser",    # Previously blocked user now behaving
            "vpn_user",           # Good user but bad IP reputation
            "api_key_sharing",    # Legitimate key but multiple IPs
        ])

        if edge_type == "premium_burst":
            input_data = self._gen_premium_user()
            input_data.patterns.burst_detected = True
            input_data.user.requests_last_minute = self.rng.randint(80, 200)
        elif edge_type == "reformed_abuser":
            input_data = self._gen_normal_moderate()
            input_data.user.previous_throttles = self.rng.randint(5, 15)
            input_data.user.previous_blocks = self.rng.randint(1, 3)
            input_data.user.account_age_days = self.rng.randint(60, 200)
        elif edge_type == "vpn_user":
            input_data = self._gen_normal_light()
            input_data.patterns.ip_reputation_score = self.rng.uniform(0.3, 0.5)
            input_data.patterns.new_ip = True
        else:  # api_key_sharing
            input_data = self._gen_normal_heavy()
            input_data.patterns.new_ip = True
            input_data.patterns.unusual_time = True

        return input_data

    def _label_with_expert_rules(
        self, input_data: RateLimitInput, scenario: str
    ) -> RateLimitOutput:
        """
        Generate labels using expert rules.

        This encodes the "judgment" we want the model to learn.
        The rules are complex and interacting - exactly what we want
        the neural network to capture.
        """
        # Get tier quotas
        quotas = TIER_QUOTAS[input_data.user.tier]

        # Compute threat score (0-1)
        threat_score = self._compute_threat_score(input_data)

        # Compute quota usage ratios
        minute_usage = input_data.user.requests_last_minute / quotas["per_minute"]
        hour_usage = input_data.user.requests_last_hour / quotas["per_hour"]

        # Determine action based on multiple factors
        action, delay_ms, warning, log_level = self._determine_action(
            input_data, threat_score, minute_usage, hour_usage
        )

        # Compute remaining quota
        remaining = max(0, quotas["per_minute"] - input_data.user.requests_last_minute)

        # Compute reset time
        reset_seconds = 60 - (input_data.user.requests_last_minute % 60)

        return RateLimitOutput(
            action=action,
            delay_ms=delay_ms,
            remaining_quota=remaining,
            quota_reset_seconds=reset_seconds,
            warning_code=warning,
            log_level=log_level,
            confidence=1.0,  # Ground truth is certain
        )

    def _compute_threat_score(self, input_data: RateLimitInput) -> float:
        """Compute threat score from 0 (safe) to 1 (definite abuse)."""
        score = 0.0

        # Abuse pattern flags
        if input_data.patterns.credential_stuffing_pattern:
            score += 0.5
        if input_data.patterns.scraping_pattern:
            score += 0.3
        if input_data.patterns.scripted_behavior:
            score += 0.2

        # IP reputation
        score += (1.0 - input_data.patterns.ip_reputation_score) * 0.3

        # History of abuse
        score += min(input_data.user.previous_throttles / 10, 0.3)
        score += min(input_data.user.previous_blocks / 5, 0.3)

        # New account with high activity
        if input_data.user.account_age_days < 7:
            if input_data.user.requests_last_minute > 20:
                score += 0.2

        # Very consistent request pattern (bot-like)
        if input_data.user.request_variance < 0.5:
            if input_data.user.requests_last_minute > 30:
                score += 0.15

        return min(score, 1.0)

    def _determine_action(
        self,
        input_data: RateLimitInput,
        threat_score: float,
        minute_usage: float,
        hour_usage: float,
    ) -> tuple[Action, int, WarningCode, LogLevel]:
        """Determine the appropriate action based on all factors."""

        # High threat = immediate action
        if threat_score > 0.8:
            return (
                Action.BLOCK_EXTENDED,
                0,
                WarningCode.ABUSE_SUSPECTED,
                LogLevel.CRITICAL,
            )

        if threat_score > 0.6:
            if input_data.patterns.credential_stuffing_pattern:
                return (
                    Action.CAPTCHA,
                    0,
                    WarningCode.ABUSE_SUSPECTED,
                    LogLevel.ERROR,
                )
            return (
                Action.BLOCK_TEMPORARY,
                0,
                WarningCode.UNUSUAL_PATTERN_DETECTED,
                LogLevel.WARN,
            )

        # System overload - throttle everyone
        if input_data.system.current_load > 0.9:
            if input_data.user.tier != UserTier.ENTERPRISE:
                delay = int(500 + (input_data.system.current_load - 0.9) * 5000)
                return (
                    Action.THROTTLE_HARD,
                    delay,
                    WarningCode.HIGH_SYSTEM_LOAD,
                    LogLevel.WARN,
                )

        # Quota exceeded
        if minute_usage > 1.0:
            if input_data.user.tier == UserTier.ENTERPRISE:
                # Enterprise gets soft throttle, not block
                return (
                    Action.THROTTLE_SOFT,
                    200,
                    WarningCode.BURST_LIMIT_APPROACHING,
                    LogLevel.INFO,
                )
            elif minute_usage > 2.0:
                return (
                    Action.BLOCK_TEMPORARY,
                    0,
                    WarningCode.QUOTA_EXHAUSTED,
                    LogLevel.WARN,
                )
            else:
                delay = int((minute_usage - 1.0) * 1000)
                return (
                    Action.THROTTLE_HARD,
                    delay,
                    WarningCode.BURST_LIMIT_APPROACHING,
                    LogLevel.INFO,
                )

        # Approaching quota
        if minute_usage > 0.8:
            return (
                Action.WARN,
                0,
                WarningCode.BURST_LIMIT_APPROACHING,
                LogLevel.INFO,
            )

        # Burst detected but user is legitimate
        if input_data.patterns.burst_detected:
            if threat_score < 0.3 and input_data.user.account_age_days > 30:
                # Trust established users
                return (
                    Action.ALLOW,
                    0,
                    WarningCode.NONE,
                    LogLevel.INFO,
                )
            else:
                # Soft throttle uncertain bursts
                return (
                    Action.THROTTLE_SOFT,
                    100,
                    WarningCode.UNUSUAL_PATTERN_DETECTED,
                    LogLevel.INFO,
                )

        # Moderate threat - monitor
        if threat_score > 0.3:
            return (
                Action.WARN,
                0,
                WarningCode.UNUSUAL_PATTERN_DETECTED,
                LogLevel.INFO,
            )

        # Normal operation
        return (
            Action.ALLOW,
            0,
            WarningCode.NONE,
            LogLevel.DEBUG,
        )


def generate_dataset(
    output_path: str,
    n_samples: int = 100000,
    seed: int = 42,
):
    """Generate and save a training dataset."""
    generator = RateLimitDataGenerator(seed=seed)

    with open(output_path, "w") as f:
        for input_data, output in generator.generate(n_samples):
            record = {
                "input": input_data.to_dict(),
                "output": output.to_dict(),
            }
            f.write(json.dumps(record) + "\n")

    print(f"Generated {n_samples} samples to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate rate limiter training data")
    parser.add_argument("--output", "-o", default="data/train.jsonl", help="Output file")
    parser.add_argument("--samples", "-n", type=int, default=100000, help="Number of samples")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    generate_dataset(args.output, args.samples, args.seed)
