"""
Fast inference engine for Rate Limiter KVRM.

Optimized for production deployment with:
- Model compilation (torch.compile)
- Batched inference
- Caching for repeated contexts
- Latency monitoring
"""

import torch
import time
from typing import Optional
from pathlib import Path

from .model import RateLimiterKVRM, RateLimiterKVRMLite
from .tokenizer import RateLimiterTokenizer
from .schemas import RateLimitInput, RateLimitOutput


class RateLimiterInference:
    """
    Production-ready inference engine for the Rate Limiter KVRM.

    Features:
    - Automatic device selection (CUDA/MPS/CPU)
    - Optional model compilation for faster inference
    - Latency tracking
    - Batch inference support
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model: Optional[RateLimiterKVRM] = None,
        device: Optional[str] = None,
        compile_model: bool = False,
        use_lite: bool = False,
    ):
        """
        Initialize the inference engine.

        Args:
            model_path: Path to saved model checkpoint
            model: Pre-loaded model (alternative to model_path)
            device: Device to run on ('cuda', 'mps', 'cpu', or None for auto)
            compile_model: Whether to use torch.compile for optimization
            use_lite: Use lightweight model variant
        """
        # Select device
        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)

        # Initialize tokenizer
        self.tokenizer = RateLimiterTokenizer()

        # Load or create model
        if model is not None:
            self.model = model
        elif model_path is not None:
            self.model = self._load_model(model_path, use_lite)
        else:
            # Create default model
            ModelClass = RateLimiterKVRMLite if use_lite else RateLimiterKVRM
            self.model = ModelClass()

        self.model = self.model.to(self.device)
        self.model.eval()

        # Optionally compile model
        if compile_model and hasattr(torch, "compile"):
            self.model = torch.compile(self.model)

        # Latency tracking
        self.latency_history: list[float] = []
        self.max_history = 1000

    def _load_model(self, path: str, use_lite: bool) -> RateLimiterKVRM:
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location="cpu")

        ModelClass = RateLimiterKVRMLite if use_lite else RateLimiterKVRM

        if "model_config" in checkpoint:
            model = ModelClass(**checkpoint["model_config"])
        else:
            model = ModelClass()

        if "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)

        return model

    @torch.no_grad()
    def predict(self, input_data: RateLimitInput) -> RateLimitOutput:
        """
        Make a single prediction.

        Args:
            input_data: Rate limit input context

        Returns:
            Rate limiting decision
        """
        start_time = time.perf_counter()

        # Encode input
        encoded = self.tokenizer.encode_input(input_data)

        # Move to device and add batch dimension
        categorical = encoded["categorical"].unsqueeze(0).to(self.device)
        numerical = encoded["numerical"].unsqueeze(0).to(self.device)
        pattern_flags = encoded["pattern_flags"].unsqueeze(0).to(self.device)

        # Run inference
        predictions = self.model(categorical, numerical, pattern_flags)

        # Remove batch dimension
        predictions = {k: v.squeeze(0) for k, v in predictions.items()}

        # Decode output
        output = self.tokenizer.decode_output(predictions)

        # Track latency
        latency = (time.perf_counter() - start_time) * 1000  # ms
        self._track_latency(latency)

        return output

    @torch.no_grad()
    def predict_batch(
        self, inputs: list[RateLimitInput]
    ) -> list[RateLimitOutput]:
        """
        Make predictions for a batch of inputs.

        Args:
            inputs: List of rate limit input contexts

        Returns:
            List of rate limiting decisions
        """
        if not inputs:
            return []

        start_time = time.perf_counter()

        # Encode all inputs
        encoded_list = [self.tokenizer.encode_input(inp) for inp in inputs]

        # Stack into batches
        categorical = torch.stack([e["categorical"] for e in encoded_list]).to(self.device)
        numerical = torch.stack([e["numerical"] for e in encoded_list]).to(self.device)
        pattern_flags = torch.stack([e["pattern_flags"] for e in encoded_list]).to(self.device)

        # Run inference
        predictions = self.model(categorical, numerical, pattern_flags)

        # Decode each output
        outputs = []
        batch_size = len(inputs)
        for i in range(batch_size):
            single_pred = {k: v[i] for k, v in predictions.items()}
            outputs.append(self.tokenizer.decode_output(single_pred))

        # Track latency (per item)
        latency = (time.perf_counter() - start_time) * 1000 / batch_size
        self._track_latency(latency)

        return outputs

    def _track_latency(self, latency_ms: float):
        """Track latency for monitoring."""
        self.latency_history.append(latency_ms)
        if len(self.latency_history) > self.max_history:
            self.latency_history.pop(0)

    def get_latency_stats(self) -> dict[str, float]:
        """Get latency statistics."""
        if not self.latency_history:
            return {"mean": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0}

        sorted_latencies = sorted(self.latency_history)
        n = len(sorted_latencies)

        return {
            "mean": sum(sorted_latencies) / n,
            "p50": sorted_latencies[n // 2],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)],
            "max": sorted_latencies[-1],
        }

    def warmup(self, n_iterations: int = 10):
        """
        Warm up the model with dummy inputs.

        This helps with JIT compilation and memory allocation.
        """
        from .schemas import RequestContext, UserContext, SystemContext, PatternFlags, HttpMethod, UserTier

        dummy_input = RateLimitInput(
            request=RequestContext(
                endpoint="/api/test",
                method=HttpMethod.GET,
            ),
            user=UserContext(
                user_id="warmup",
                tier=UserTier.FREE,
            ),
            system=SystemContext(),
            patterns=PatternFlags(),
        )

        for _ in range(n_iterations):
            self.predict(dummy_input)

        # Clear warmup latencies
        self.latency_history.clear()

    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "device": str(self.device),
            "parameters": self.model.count_parameters(),
            "size_mb": self.model.get_model_size_mb(),
            "compiled": hasattr(self.model, "_orig_mod"),
        }


# Convenience function for quick testing
def quick_test():
    """Quick test of the inference engine."""
    from .schemas import (
        RequestContext, UserContext, SystemContext, PatternFlags,
        HttpMethod, UserTier, AuthType
    )

    print("Initializing inference engine...")
    engine = RateLimiterInference(use_lite=True)

    print(f"Model info: {engine.get_model_info()}")

    print("\nWarming up...")
    engine.warmup(10)

    # Test scenario: Normal user
    normal_user = RateLimitInput(
        request=RequestContext(
            endpoint="/api/v1/search",
            method=HttpMethod.GET,
            payload_size_bytes=256,
            auth_type=AuthType.API_KEY,
            endpoint_category="search",
        ),
        user=UserContext(
            user_id="u_12345",
            tier=UserTier.PROFESSIONAL,
            requests_last_minute=15,
            requests_last_hour=200,
            account_age_days=365,
        ),
        system=SystemContext(
            current_load=0.5,
        ),
        patterns=PatternFlags(),
    )

    print("\n--- Test: Normal User ---")
    result = engine.predict(normal_user)
    print(f"Action: {result.action.value}")
    print(f"Delay: {result.delay_ms}ms")
    print(f"Warning: {result.warning_code.value}")

    # Test scenario: Suspected scraper
    scraper = RateLimitInput(
        request=RequestContext(
            endpoint="/api/v1/data/export",
            method=HttpMethod.GET,
            payload_size_bytes=100,
            auth_type=AuthType.NONE,
            endpoint_category="download",
        ),
        user=UserContext(
            user_id="u_99999",
            tier=UserTier.FREE,
            requests_last_minute=100,
            requests_last_hour=2000,
            account_age_days=5,
            previous_throttles=3,
            request_variance=0.2,  # Very consistent = bot-like
        ),
        system=SystemContext(
            current_load=0.7,
        ),
        patterns=PatternFlags(
            burst_detected=True,
            scripted_behavior=True,
            scraping_pattern=True,
            ip_reputation_score=0.3,
        ),
    )

    print("\n--- Test: Suspected Scraper ---")
    result = engine.predict(scraper)
    print(f"Action: {result.action.value}")
    print(f"Delay: {result.delay_ms}ms")
    print(f"Warning: {result.warning_code.value}")

    # Latency stats
    print(f"\nLatency stats: {engine.get_latency_stats()}")


if __name__ == "__main__":
    quick_test()
