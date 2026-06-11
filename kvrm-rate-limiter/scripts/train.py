#!/usr/bin/env python3
"""
Training script for Rate Limiter KVRM.

Usage:
    python scripts/train.py --data data/train.jsonl --epochs 50
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model import RateLimiterKVRM, RateLimiterKVRMLite
from src.tokenizer import RateLimiterTokenizer
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
)


class RateLimitDataset(Dataset):
    """Dataset for rate limiter training data."""

    def __init__(self, data_path: str, tokenizer: RateLimiterTokenizer):
        self.tokenizer = tokenizer
        self.samples = []

        print(f"Loading data from {data_path}...")
        with open(data_path, "r") as f:
            for line in tqdm(f, desc="Loading"):
                record = json.loads(line)
                self.samples.append(record)

        print(f"Loaded {len(self.samples)} samples")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict:
        record = self.samples[idx]

        # Parse input
        inp = record["input"]
        input_data = RateLimitInput(
            request=RequestContext(
                endpoint=inp["request"]["endpoint"],
                method=HttpMethod(inp["request"]["method"]),
                payload_size_bytes=inp["request"]["payload_size_bytes"],
                auth_type=AuthType(inp["request"]["auth_type"]),
                endpoint_category=inp["request"]["endpoint_category"],
                estimated_cost=inp["request"]["estimated_cost"],
            ),
            user=UserContext(
                user_id=inp["user"]["user_id"],
                tier=UserTier(inp["user"]["tier"]),
                requests_last_minute=inp["user"]["requests_last_minute"],
                requests_last_hour=inp["user"]["requests_last_hour"],
                requests_last_day=inp["user"]["requests_last_day"],
                account_age_days=inp["user"]["account_age_days"],
                previous_throttles=inp["user"]["previous_throttles"],
                previous_blocks=inp["user"]["previous_blocks"],
                payment_current=inp["user"]["payment_current"],
                avg_requests_per_minute=inp["user"]["avg_requests_per_minute"],
                request_variance=inp["user"]["request_variance"],
            ),
            system=SystemContext(
                current_load=inp["system"]["current_load"],
                endpoint_queue_depth=inp["system"]["endpoint_queue_depth"],
                similar_requests_last_minute=inp["system"]["similar_requests_last_minute"],
                error_rate_last_minute=inp["system"]["error_rate_last_minute"],
                available_capacity_percent=inp["system"]["available_capacity_percent"],
            ),
            patterns=PatternFlags(
                burst_detected=inp["patterns"]["burst_detected"],
                unusual_time=inp["patterns"]["unusual_time"],
                new_ip=inp["patterns"]["new_ip"],
                ip_reputation_score=inp["patterns"]["ip_reputation_score"],
                scripted_behavior=inp["patterns"]["scripted_behavior"],
                credential_stuffing_pattern=inp["patterns"]["credential_stuffing_pattern"],
                scraping_pattern=inp["patterns"]["scraping_pattern"],
            ),
        )

        # Parse output
        out = record["output"]
        output_data = RateLimitOutput(
            action=Action(out["action"]),
            delay_ms=out["delay_ms"],
            remaining_quota=out["remaining_quota"],
            quota_reset_seconds=out["quota_reset_seconds"],
            warning_code=WarningCode(out["warning_code"]),
            log_level=LogLevel(out["log_level"]),
        )

        # Encode
        encoded_input = self.tokenizer.encode_input(input_data)
        encoded_output = self.tokenizer.encode_output(output_data)

        return {
            "categorical": encoded_input["categorical"],
            "numerical": encoded_input["numerical"],
            "pattern_flags": encoded_input["pattern_flags"],
            **encoded_output,
        }


def train_epoch(
    model: RateLimiterKVRM,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> dict[str, float]:
    """Train for one epoch."""
    model.train()
    total_losses = {
        "total": 0.0,
        "action": 0.0,
        "delay_ms": 0.0,
        "remaining_quota": 0.0,
        "quota_reset_seconds": 0.0,
        "warning_code": 0.0,
        "log_level": 0.0,
    }
    n_batches = 0

    pbar = tqdm(dataloader, desc="Training")
    for batch in pbar:
        # Move to device
        categorical = batch["categorical"].to(device)
        numerical = batch["numerical"].to(device)
        pattern_flags = batch["pattern_flags"].to(device)

        targets = {
            "action": batch["action"].to(device),
            "delay_ms": batch["delay_ms"].to(device),
            "remaining_quota": batch["remaining_quota"].to(device),
            "quota_reset_seconds": batch["quota_reset_seconds"].to(device),
            "warning_code": batch["warning_code"].to(device),
            "log_level": batch["log_level"].to(device),
        }

        # Forward pass
        optimizer.zero_grad()
        predictions = model(categorical, numerical, pattern_flags)

        # Compute loss
        loss, loss_breakdown = model.compute_loss(predictions, targets)

        # Backward pass
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        # Accumulate losses
        for k, v in loss_breakdown.items():
            total_losses[k] += v
        n_batches += 1

        # Update progress bar
        pbar.set_postfix({
            "loss": f"{loss_breakdown['total']:.4f}",
            "action": f"{loss_breakdown['action']:.4f}",
        })

    # Average losses
    return {k: v / n_batches for k, v in total_losses.items()}


@torch.no_grad()
def evaluate(
    model: RateLimiterKVRM,
    dataloader: DataLoader,
    device: torch.device,
) -> dict[str, float]:
    """Evaluate the model."""
    model.eval()

    total_losses = {
        "total": 0.0,
        "action": 0.0,
        "delay_ms": 0.0,
        "remaining_quota": 0.0,
        "quota_reset_seconds": 0.0,
        "warning_code": 0.0,
        "log_level": 0.0,
    }
    n_batches = 0

    # Accuracy tracking
    action_correct = 0
    warning_correct = 0
    total_samples = 0

    for batch in tqdm(dataloader, desc="Evaluating"):
        categorical = batch["categorical"].to(device)
        numerical = batch["numerical"].to(device)
        pattern_flags = batch["pattern_flags"].to(device)

        targets = {
            "action": batch["action"].to(device),
            "delay_ms": batch["delay_ms"].to(device),
            "remaining_quota": batch["remaining_quota"].to(device),
            "quota_reset_seconds": batch["quota_reset_seconds"].to(device),
            "warning_code": batch["warning_code"].to(device),
            "log_level": batch["log_level"].to(device),
        }

        # Forward pass
        predictions = model(categorical, numerical, pattern_flags)

        # Compute loss
        _, loss_breakdown = model.compute_loss(predictions, targets)

        # Accumulate losses
        for k, v in loss_breakdown.items():
            total_losses[k] += v
        n_batches += 1

        # Compute accuracies
        action_pred = predictions["action"].argmax(dim=-1)
        action_correct += (action_pred == targets["action"]).sum().item()

        warning_pred = predictions["warning_code"].argmax(dim=-1)
        warning_correct += (warning_pred == targets["warning_code"]).sum().item()

        total_samples += categorical.size(0)

    # Average losses and compute accuracies
    metrics = {k: v / n_batches for k, v in total_losses.items()}
    metrics["action_acc"] = action_correct / total_samples
    metrics["warning_acc"] = warning_correct / total_samples

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Train Rate Limiter KVRM")
    parser.add_argument("--data", required=True, help="Path to training data")
    parser.add_argument("--val_data", help="Path to validation data")
    parser.add_argument("--output", default="models", help="Output directory")
    parser.add_argument("--epochs", type=int, default=50, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=128, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--hidden_size", type=int, default=128, help="Model hidden size")
    parser.add_argument("--num_layers", type=int, default=3, help="Number of transformer layers")
    parser.add_argument("--lite", action="store_true", help="Use lightweight model")
    parser.add_argument("--device", help="Device (cuda/mps/cpu)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    # Set seed
    torch.manual_seed(args.seed)

    # Select device
    if args.device:
        device = torch.device(args.device)
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    print(f"Using device: {device}")

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Initialize tokenizer
    tokenizer = RateLimiterTokenizer()

    # Load data
    train_dataset = RateLimitDataset(args.data, tokenizer)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=True if device.type == "cuda" else False,
    )

    val_loader = None
    if args.val_data:
        val_dataset = RateLimitDataset(args.val_data, tokenizer)
        val_loader = DataLoader(
            val_dataset,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=0,
        )

    # Create model
    ModelClass = RateLimiterKVRMLite if args.lite else RateLimiterKVRM
    model_config = {
        "hidden_size": args.hidden_size,
        "num_layers": args.num_layers,
    }
    model = ModelClass(**model_config).to(device)

    print(f"Model parameters: {model.count_parameters():,}")
    print(f"Model size: {model.get_model_size_mb():.2f} MB")

    # Optimizer and scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=args.lr * 0.01
    )

    # Training loop
    best_val_loss = float("inf")
    best_action_acc = 0.0

    for epoch in range(1, args.epochs + 1):
        print(f"\n{'='*60}")
        print(f"Epoch {epoch}/{args.epochs}")
        print(f"{'='*60}")

        # Train
        train_metrics = train_epoch(model, train_loader, optimizer, device)
        print(f"\nTrain Loss: {train_metrics['total']:.4f}")
        print(f"  Action Loss: {train_metrics['action']:.4f}")

        # Validate
        if val_loader:
            val_metrics = evaluate(model, val_loader, device)
            print(f"\nVal Loss: {val_metrics['total']:.4f}")
            print(f"  Action Acc: {val_metrics['action_acc']*100:.1f}%")
            print(f"  Warning Acc: {val_metrics['warning_acc']*100:.1f}%")

            # Save best model
            if val_metrics["action_acc"] > best_action_acc:
                best_action_acc = val_metrics["action_acc"]
                best_val_loss = val_metrics["total"]

                checkpoint = {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "model_config": model_config,
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_metrics": val_metrics,
                }
                torch.save(checkpoint, os.path.join(args.output, "best.pt"))
                print(f"  >> Saved best model (Action Acc: {best_action_acc*100:.1f}%)")

        # Step scheduler
        scheduler.step()

        # Periodic save
        if epoch % 10 == 0:
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "model_config": model_config,
                "optimizer_state_dict": optimizer.state_dict(),
            }
            torch.save(checkpoint, os.path.join(args.output, f"checkpoint_epoch{epoch}.pt"))

    # Final save
    checkpoint = {
        "epoch": args.epochs,
        "model_state_dict": model.state_dict(),
        "model_config": model_config,
        "final": True,
    }
    torch.save(checkpoint, os.path.join(args.output, "final.pt"))
    print(f"\nTraining complete!")
    print(f"Best Action Accuracy: {best_action_acc*100:.1f}%")


if __name__ == "__main__":
    main()
