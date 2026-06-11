"""
KVRM Rate Limiter Model

A neural network that learns nuanced rate limiting decisions from context.
Unlike rule-based systems, this model can capture complex interactions between
user history, system state, and behavioral patterns.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional
import math

from .schemas import Action, WarningCode, LogLevel


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding for transformer."""

    def __init__(self, d_model: int, max_len: int = 64):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]


class RateLimiterKVRM(nn.Module):
    """
    Key-Value Response Model for Rate Limiting.

    Architecture:
    1. Categorical embeddings for tier, auth, method, endpoint category
    2. Numerical feature projection
    3. Transformer encoder for feature interaction
    4. Multi-head output for different decision components

    Input: Encoded rate limit context (categorical + numerical + flags)
    Output: Action, delay, quota, warning, log level
    """

    def __init__(
        self,
        hidden_size: int = 128,
        num_layers: int = 3,
        num_heads: int = 4,
        dropout: float = 0.1,
        num_tiers: int = 4,
        num_auth_types: int = 5,
        num_methods: int = 7,
        num_categories: int = 10,
        num_numerical: int = 18,
        num_pattern_flags: int = 7,
    ):
        super().__init__()

        self.hidden_size = hidden_size

        # Categorical embeddings
        embed_dim = 16
        self.tier_embedding = nn.Embedding(num_tiers, embed_dim)
        self.auth_embedding = nn.Embedding(num_auth_types, embed_dim)
        self.method_embedding = nn.Embedding(num_methods, embed_dim)
        self.category_embedding = nn.Embedding(num_categories, embed_dim)

        # Numerical feature projection
        self.numerical_proj = nn.Sequential(
            nn.Linear(num_numerical, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        # Pattern flags projection
        self.pattern_proj = nn.Sequential(
            nn.Linear(num_pattern_flags, hidden_size // 2),
            nn.LayerNorm(hidden_size // 2),
            nn.GELU(),
        )

        # Combined embedding projection
        total_embed_dim = embed_dim * 4 + hidden_size + hidden_size // 2
        self.input_proj = nn.Linear(total_embed_dim, hidden_size)

        # Positional encoding
        self.pos_encoding = PositionalEncoding(hidden_size)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=num_heads,
            dim_feedforward=hidden_size * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Output heads
        self.action_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, len(Action)),
        )

        self.delay_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.GELU(),
            nn.Linear(hidden_size // 2, 1),
            nn.Sigmoid(),  # Output 0-1, scaled to max_delay_ms
        )

        self.quota_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.GELU(),
            nn.Linear(hidden_size // 2, 1),
            nn.Sigmoid(),  # Output 0-1, scaled to max_quota
        )

        self.reset_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.GELU(),
            nn.Linear(hidden_size // 2, 1),
            nn.Sigmoid(),  # Output 0-1, scaled to max time
        )

        self.warning_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.GELU(),
            nn.Linear(hidden_size // 2, len(WarningCode)),
        )

        self.loglevel_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 4),
            nn.GELU(),
            nn.Linear(hidden_size // 4, len(LogLevel)),
        )

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize weights with Xavier/Kaiming initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, std=0.02)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(
        self,
        categorical: torch.Tensor,
        numerical: torch.Tensor,
        pattern_flags: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """
        Forward pass.

        Args:
            categorical: [batch, 4] tensor of category indices
            numerical: [batch, num_numerical] tensor of normalized features
            pattern_flags: [batch, num_flags] tensor of boolean flags

        Returns:
            Dictionary with predictions for each output component
        """
        batch_size = categorical.size(0)

        # Embed categorical features
        tier_emb = self.tier_embedding(categorical[:, 0])      # [B, embed_dim]
        auth_emb = self.auth_embedding(categorical[:, 1])      # [B, embed_dim]
        method_emb = self.method_embedding(categorical[:, 2])  # [B, embed_dim]
        cat_emb = self.category_embedding(categorical[:, 3])   # [B, embed_dim]

        # Project numerical features
        num_proj = self.numerical_proj(numerical)  # [B, hidden]

        # Project pattern flags
        pattern_proj = self.pattern_proj(pattern_flags)  # [B, hidden//2]

        # Concatenate all features
        combined = torch.cat([
            tier_emb, auth_emb, method_emb, cat_emb,
            num_proj, pattern_proj
        ], dim=-1)  # [B, total_embed_dim]

        # Project to hidden size
        x = self.input_proj(combined)  # [B, hidden]

        # Add sequence dimension for transformer
        x = x.unsqueeze(1)  # [B, 1, hidden]

        # Apply positional encoding (even for single token, helps with learned patterns)
        x = self.pos_encoding(x)

        # Transformer encoding
        x = self.transformer(x)  # [B, 1, hidden]

        # Pool (take first/only token)
        x = x[:, 0]  # [B, hidden]

        # Generate outputs
        return {
            "action": self.action_head(x),           # [B, num_actions]
            "delay_ms": self.delay_head(x).squeeze(-1),  # [B]
            "remaining_quota": self.quota_head(x).squeeze(-1),  # [B]
            "quota_reset_seconds": self.reset_head(x).squeeze(-1),  # [B]
            "warning_code": self.warning_head(x),    # [B, num_warnings]
            "log_level": self.loglevel_head(x),      # [B, num_loglevels]
        }

    def compute_loss(
        self,
        predictions: dict[str, torch.Tensor],
        targets: dict[str, torch.Tensor],
        action_weight: float = 2.0,
    ) -> tuple[torch.Tensor, dict[str, float]]:
        """
        Compute combined loss for all output components.

        Args:
            predictions: Model predictions
            targets: Ground truth targets
            action_weight: Weight for action loss (most important)

        Returns:
            Tuple of (total_loss, loss_breakdown_dict)
        """
        losses = {}

        # Action loss (cross-entropy, weighted higher)
        losses["action"] = F.cross_entropy(
            predictions["action"], targets["action"]
        ) * action_weight

        # Delay loss (MSE)
        losses["delay_ms"] = F.mse_loss(
            predictions["delay_ms"], targets["delay_ms"]
        )

        # Quota loss (MSE)
        losses["remaining_quota"] = F.mse_loss(
            predictions["remaining_quota"], targets["remaining_quota"]
        )

        # Reset time loss (MSE)
        losses["quota_reset_seconds"] = F.mse_loss(
            predictions["quota_reset_seconds"], targets["quota_reset_seconds"]
        )

        # Warning code loss (cross-entropy)
        losses["warning_code"] = F.cross_entropy(
            predictions["warning_code"], targets["warning_code"]
        )

        # Log level loss (cross-entropy)
        losses["log_level"] = F.cross_entropy(
            predictions["log_level"], targets["log_level"]
        )

        # Total loss
        total_loss = sum(losses.values())

        # Convert to Python floats for logging
        loss_breakdown = {k: v.item() for k, v in losses.items()}
        loss_breakdown["total"] = total_loss.item()

        return total_loss, loss_breakdown

    def count_parameters(self) -> int:
        """Count trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_model_size_mb(self) -> float:
        """Estimate model size in megabytes."""
        param_size = sum(p.numel() * p.element_size() for p in self.parameters())
        buffer_size = sum(b.numel() * b.element_size() for b in self.buffers())
        return (param_size + buffer_size) / (1024 * 1024)


class RateLimiterKVRMLite(RateLimiterKVRM):
    """
    Lightweight version for ultra-fast inference (<50μs target).

    Reduces hidden size and layers for production deployment.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("hidden_size", 64)
        kwargs.setdefault("num_layers", 2)
        kwargs.setdefault("num_heads", 2)
        super().__init__(**kwargs)
