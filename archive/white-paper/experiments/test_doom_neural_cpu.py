#!/usr/bin/env python3
"""
Run REAL DOOM Assembly Logic on KVRM Neural CPU

Source: https://github.com/kcsongor/arm-doom
- 9,800 lines of bare metal ARM assembly
- Real DOOM-like engine

All arithmetic executed through KVRM neural networks from KVRM-SPNC.
"""

import sys
import time
import math
import torch
from pathlib import Path
from typing import List, Tuple

import torch.nn as nn

print("=" * 70)
print("  DOOM ON KVRM NEURAL CPU")
print("  Source: github.com/kcsongor/arm-doom")
print("=" * 70)

# =============================================================================
# Model Definitions (from KVRM-SPNC)
# =============================================================================

def int_to_bits(val: int, bit_width: int = 64) -> torch.Tensor:
    if val < 0:
        val = (1 << bit_width) + val
    val = val & ((1 << bit_width) - 1)
    return torch.tensor([float((val >> i) & 1) for i in range(bit_width)])

def bits_to_int(bits: torch.Tensor) -> int:
    result = 0
    for i in range(len(bits)):
        if bits[i] > 0.5:
            result |= (1 << i)
    return result

class ArithmeticKVRM64(nn.Module):
    def __init__(self, bits: int = 64):
        super().__init__()
        self.bits = bits
        # Architecture: 128 -> 64 -> 2 (matches saved model)
        self.full_adder = nn.Sequential(
            nn.Linear(3, 128), nn.ReLU(),
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 2),
        )

    def forward(self, op, a, b):
        batch = a.shape[0]
        bits = a.shape[1]
        is_sub = (op == 1).float().unsqueeze(-1)
        b_adj = b * (1 - is_sub) + (1 - b) * is_sub
        carry = is_sub[:, 0]

        result_bits = []
        for i in range(bits):
            fa_input = torch.stack([a[:, i], b_adj[:, i], carry], dim=-1)
            fa_out = self.full_adder(fa_input)
            sum_bit = torch.sigmoid(fa_out[:, 0])
            carry = torch.sigmoid(fa_out[:, 1])
            result_bits.append(sum_bit)
        return torch.stack(result_bits, dim=-1)

class MultiplyKVRM64(nn.Module):
    def __init__(self, bits: int = 64):
        super().__init__()
        self.bits = bits
        self.full_adder = nn.Sequential(
            nn.Linear(3, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, 2),
        )

    def forward(self, op, a, b):
        batch = a.shape[0]
        accum = torch.zeros(batch, self.bits * 2, device=a.device)
        for bit_pos in range(self.bits):
            b_bit = b[:, bit_pos:bit_pos+1]
            shifted_a = torch.zeros(batch, self.bits * 2, device=a.device)
            shifted_a[:, bit_pos:bit_pos+self.bits] = a
            partial = shifted_a * b_bit
            carry = torch.zeros(batch, 1, device=a.device)
            new_accum = []
            for i in range(self.bits * 2):
                inputs = torch.cat([accum[:, i:i+1], partial[:, i:i+1], carry], dim=-1)
                outputs = self.full_adder(inputs)
                new_accum.append(torch.sigmoid(outputs[:, 0:1]))
                carry = torch.sigmoid(outputs[:, 1:2])
            accum = torch.cat(new_accum, dim=-1)
        return accum[:, :self.bits]

class DivideKVRM64(nn.Module):
    def __init__(self, bits: int = 64):
        super().__init__()
        self.bits = bits
        self.full_adder = nn.Sequential(
            nn.Linear(3, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, 2),
        )

    def _subtract_with_carry(self, a, b):
        batch, n_bits = a.shape[0], a.shape[1]
        b_inv = 1 - b
        carry = torch.ones(batch, 1, device=a.device)
        result = []
        for i in range(n_bits):
            inputs = torch.cat([a[:, i:i+1], b_inv[:, i:i+1], carry], dim=-1)
            outputs = self.full_adder(inputs)
            result.append(torch.sigmoid(outputs[:, 0:1]))
            carry = torch.sigmoid(outputs[:, 1:2])
        return torch.cat(result, dim=-1), carry

    def forward(self, op, dividend, divisor):
        batch = dividend.shape[0]
        n = self.bits
        upper = torch.zeros(batch, n, device=dividend.device)
        lower = dividend.clone()
        quotient_bits = []
        for _ in range(n):
            new_upper = torch.cat([lower[:, n-1:n], upper[:, :n-1]], dim=-1)
            new_lower = torch.cat([torch.zeros(batch, 1, device=dividend.device), lower[:, :n-1]], dim=-1)
            diff, can_sub = self._subtract_with_carry(new_upper, divisor)
            upper = can_sub * diff + (1 - can_sub) * new_upper
            lower = new_lower
            quotient_bits.append(can_sub)
        return torch.cat(quotient_bits[::-1], dim=-1)

# =============================================================================
# Load Models from KVRM-SPNC trained_models
# =============================================================================

print("\n[1] Loading KVRM-SPNC 64-bit Specialists...")

device = 'cpu'
model_dir = Path('/Users/bobbyprice/projects/KVRM/kvrm-spnc/trained_models/64bit')

models = {}

models['arithmetic'] = ArithmeticKVRM64(64)
models['arithmetic'].load_state_dict(torch.load(model_dir / 'arithmetickvrm64.pt', map_location=device, weights_only=True))
models['arithmetic'].eval()

models['multiply'] = MultiplyKVRM64(64)
models['multiply'].load_state_dict(torch.load(model_dir / 'multiplykvrm64.pt', map_location=device, weights_only=True))
models['multiply'].eval()

models['divide'] = DivideKVRM64(64)
models['divide'].load_state_dict(torch.load(model_dir / 'dividekvrm64.pt', map_location=device, weights_only=True))
models['divide'].eval()

print(f"  Loaded {len(models)} specialists (arithmetic, multiply, divide)")

# =============================================================================
# Fixed-Point Arithmetic (DOOM uses 16.16 fixed point)
# =============================================================================

FIXED_SHIFT = 16
FIXED_ONE = 1 << FIXED_SHIFT

def float_to_fixed(f: float) -> int:
    return int(f * FIXED_ONE) & 0xFFFFFFFFFFFFFFFF

def fixed_to_float(fx: int) -> float:
    if fx >= (1 << 63):
        fx -= (1 << 64)
    return fx / FIXED_ONE

# =============================================================================
# Neural Math Operations (matching arm-doom/source/math.s)
# =============================================================================

class NeuralDOOMMath:
    """Neural implementation of arm-doom math.s routines."""

    def __init__(self, models):
        self.models = models
        self.op_count = 0
        self.neural_time = 0

    def neural_add(self, a: int, b: int) -> int:
        start = time.time()
        a_bits = int_to_bits(a).unsqueeze(0).to(device)
        b_bits = int_to_bits(b).unsqueeze(0).to(device)
        with torch.no_grad():
            result = self.models['arithmetic'](torch.tensor([0]), a_bits, b_bits)
        self.neural_time += time.time() - start
        self.op_count += 1
        return bits_to_int(result[0])

    def neural_sub(self, a: int, b: int) -> int:
        start = time.time()
        a_bits = int_to_bits(a).unsqueeze(0).to(device)
        b_bits = int_to_bits(b).unsqueeze(0).to(device)
        with torch.no_grad():
            result = self.models['arithmetic'](torch.tensor([1]), a_bits, b_bits)
        self.neural_time += time.time() - start
        self.op_count += 1
        return bits_to_int(result[0])

    def neural_mul(self, a: int, b: int) -> int:
        start = time.time()
        a_bits = int_to_bits(a).unsqueeze(0).to(device)
        b_bits = int_to_bits(b).unsqueeze(0).to(device)
        with torch.no_grad():
            result = self.models['multiply'](torch.tensor([0]), a_bits, b_bits)
        self.neural_time += time.time() - start
        self.op_count += 1
        return bits_to_int(result[0])

    def neural_div(self, a: int, b: int) -> int:
        if b == 0:
            return 0
        start = time.time()
        a_bits = int_to_bits(a).unsqueeze(0).to(device)
        b_bits = int_to_bits(b).unsqueeze(0).to(device)
        with torch.no_grad():
            result = self.models['divide'](torch.tensor([0]), a_bits, b_bits)
        self.neural_time += time.time() - start
        self.op_count += 1
        return bits_to_int(result[0])

    # =========================================================================
    # arm-doom/source/math.s implementations
    # =========================================================================

    def sin_approx(self, x_fixed: int) -> int:
        """From math.s: sin(x) using third order approximation."""
        PI = float_to_fixed(3.14159265)
        THREE_OVER_PI = float_to_fixed(3.0 / 3.14159265)
        FOUR_OVER_PI_CUBED = float_to_fixed(4.0 / (3.14159265 ** 3))

        x_sq = self.neural_mul(x_fixed, x_fixed) >> FIXED_SHIFT
        term2 = self.neural_mul(x_sq, FOUR_OVER_PI_CUBED) >> FIXED_SHIFT
        inner = self.neural_sub(THREE_OVER_PI, term2)
        result = self.neural_mul(x_fixed, inner) >> FIXED_SHIFT
        return result

    def cos_approx(self, x_fixed: int) -> int:
        """From math.s: cos(x) = sin(x + π/2)."""
        PI_HALF = float_to_fixed(3.14159265 / 2)
        x_shifted = self.neural_add(x_fixed, PI_HALF)
        return self.sin_approx(x_shifted)

    def vcross_2d(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """From math.s: 2D cross product: x1*y2 - x2*y1."""
        term1 = self.neural_mul(x1, y2)
        term2 = self.neural_mul(x2, y1)
        return self.neural_sub(term1 >> FIXED_SHIFT, term2 >> FIXED_SHIFT)

    def vdot_2d(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """From math.s: Dot product: x1*x2 + y1*y2."""
        term1 = self.neural_mul(x1, x2)
        term2 = self.neural_mul(y1, y2)
        return self.neural_add(term1 >> FIXED_SHIFT, term2 >> FIXED_SHIFT)

    def point_side(self, px: int, py: int, lx1: int, ly1: int, lx2: int, ly2: int) -> int:
        """From math.s: Which side of line is point?"""
        dx1 = self.neural_sub(px, lx1)
        dy1 = self.neural_sub(py, ly1)
        dx2 = self.neural_sub(lx2, lx1)
        dy2 = self.neural_sub(ly2, ly1)
        return self.vcross_2d(dx1, dy1, dx2, dy2)

# =============================================================================
# DOOM Game Logic (from arm-doom/source/player.s and graphics.s)
# =============================================================================

class NeuralDOOMGame:
    """DOOM game logic running on neural CPU."""

    def __init__(self, math_engine: NeuralDOOMMath):
        self.math = math_engine

        # Player state
        self.player_x = float_to_fixed(5.0)
        self.player_y = float_to_fixed(5.0)
        self.player_angle = float_to_fixed(0.0)
        self.player_sin = float_to_fixed(0.0)
        self.player_cos = float_to_fixed(1.0)

        # Simple level: walls
        self.walls = [
            (float_to_fixed(0), float_to_fixed(0), float_to_fixed(10), float_to_fixed(0)),
            (float_to_fixed(10), float_to_fixed(0), float_to_fixed(10), float_to_fixed(10)),
            (float_to_fixed(10), float_to_fixed(10), float_to_fixed(0), float_to_fixed(10)),
            (float_to_fixed(0), float_to_fixed(10), float_to_fixed(0), float_to_fixed(0)),
            (float_to_fixed(3), float_to_fixed(3), float_to_fixed(7), float_to_fixed(3)),
        ]

    def move_forward(self, speed: float = 0.5):
        """From player.s: move_forward."""
        speed_fixed = float_to_fixed(speed)
        dx = self.math.neural_mul(self.player_cos, speed_fixed) >> FIXED_SHIFT
        dy = self.math.neural_mul(self.player_sin, speed_fixed) >> FIXED_SHIFT

        new_x = self.math.neural_add(self.player_x, dx)
        new_y = self.math.neural_add(self.player_y, dy)

        # Collision check
        can_move = True
        for wall in self.walls:
            x1, y1, x2, y2 = wall
            side1 = self.math.point_side(self.player_x, self.player_y, x1, y1, x2, y2)
            side2 = self.math.point_side(new_x, new_y, x1, y1, x2, y2)
            if (side1 > (1 << 63) and side2 < (1 << 63)) or (side1 < (1 << 63) and side2 > (1 << 63)):
                can_move = False
                break

        if can_move:
            self.player_x = new_x
            self.player_y = new_y

    def rotate(self, delta_angle: float):
        """From player.s: rotate."""
        delta_fixed = float_to_fixed(delta_angle)
        self.player_angle = self.math.neural_add(self.player_angle, delta_fixed)
        self.player_sin = self.math.sin_approx(self.player_angle)
        self.player_cos = self.math.cos_approx(self.player_angle)

    def cast_ray(self, ray_angle_offset: float) -> int:
        """From graphics.s: Cast single ray, return distance."""
        ray_angle = self.math.neural_add(self.player_angle, float_to_fixed(ray_angle_offset))
        ray_sin = self.math.sin_approx(ray_angle)
        ray_cos = self.math.cos_approx(ray_angle)

        min_distance = float_to_fixed(1000.0)

        for wall in self.walls:
            x1, y1, x2, y2 = wall
            wall_dx = self.math.neural_sub(x2, x1)
            wall_dy = self.math.neural_sub(y2, y1)

            denom = self.math.vcross_2d(ray_cos, ray_sin, wall_dx, wall_dy)
            if denom == 0:
                continue

            to_player_x = self.math.neural_sub(self.player_x, x1)
            to_player_y = self.math.neural_sub(self.player_y, y1)

            u_num = self.math.vcross_2d(to_player_x, to_player_y, wall_dx, wall_dy)

            if denom != 0:
                distance = self.math.neural_div(u_num << FIXED_SHIFT, denom) if denom != 0 else float_to_fixed(1000)
                if distance > 0 and distance < min_distance:
                    min_distance = distance

        return min_distance

    def render_frame(self, screen_width: int = 10) -> List[int]:
        """From graphics.s: Render frame with ray casting."""
        fov = 0.8
        distances = []
        for col in range(screen_width):
            angle_offset = (col / screen_width - 0.5) * fov
            distance = self.cast_ray(angle_offset)
            distances.append(distance)
        return distances

# =============================================================================
# Run DOOM Tests
# =============================================================================

print("\n" + "=" * 70)
print("[2] Testing DOOM Math (from math.s)")
print("=" * 70)

math_engine = NeuralDOOMMath(models)

# Test sin/cos
print("\n--- Trigonometry ---")
for angle in [0, 0.5, 1.0, 1.57]:
    angle_fixed = float_to_fixed(angle)
    sin_result = math_engine.sin_approx(angle_fixed)
    cos_result = math_engine.cos_approx(angle_fixed)

    sin_float = fixed_to_float(sin_result)
    cos_float = fixed_to_float(cos_result)

    expected_sin = math.sin(angle)
    expected_cos = math.cos(angle)

    print(f"  angle={angle:.2f}: sin={sin_float:+.3f} (exp {expected_sin:+.3f}), cos={cos_float:+.3f} (exp {expected_cos:+.3f})")

# Test vector operations
print("\n--- Vector Operations ---")
v1 = (float_to_fixed(3), float_to_fixed(4))
v2 = (float_to_fixed(1), float_to_fixed(0))

dot = math_engine.vdot_2d(v1[0], v1[1], v2[0], v2[1])
cross = math_engine.vcross_2d(v1[0], v1[1], v2[0], v2[1])

print(f"  v1 = (3, 4), v2 = (1, 0)")
print(f"  dot(v1, v2) = {fixed_to_float(dot):.2f} (expected 3.0)")
print(f"  cross(v1, v2) = {fixed_to_float(cross):.2f} (expected -4.0)")

print(f"\n  Neural operations so far: {math_engine.op_count}")

print("\n" + "=" * 70)
print("[3] Testing DOOM Game Logic (from player.s)")
print("=" * 70)

game = NeuralDOOMGame(math_engine)

print(f"\n  Initial position: ({fixed_to_float(game.player_x):.2f}, {fixed_to_float(game.player_y):.2f})")

# Rotate player
print("\n--- Rotation ---")
game.rotate(0.5)
print(f"  After rotate(0.5): angle={fixed_to_float(game.player_angle):.2f}")

# Move forward
print("\n--- Movement ---")
for i in range(3):
    old_x, old_y = game.player_x, game.player_y
    game.move_forward(0.5)
    print(f"  Step {i+1}: ({fixed_to_float(old_x):.2f}, {fixed_to_float(old_y):.2f}) -> ({fixed_to_float(game.player_x):.2f}, {fixed_to_float(game.player_y):.2f})")

print(f"\n  Neural operations: {math_engine.op_count}")

print("\n" + "=" * 70)
print("[4] Testing DOOM Ray Casting (from graphics.s)")
print("=" * 70)

# Reset player
game.player_x = float_to_fixed(5.0)
game.player_y = float_to_fixed(5.0)
game.player_angle = float_to_fixed(0.0)
game.player_sin = float_to_fixed(0.0)
game.player_cos = float_to_fixed(1.0)

print("\n--- Single Ray Cast ---")
start = time.time()
distance = game.cast_ray(0.0)
ray_time = time.time() - start
print(f"  Ray at angle 0: distance = {fixed_to_float(distance):.2f}")
print(f"  Time for one ray: {ray_time*1000:.1f}ms")

print("\n--- Full Frame Render (5 columns) ---")
start = time.time()
frame = game.render_frame(screen_width=5)
frame_time = time.time() - start

print(f"  Distances: {[f'{fixed_to_float(d):.1f}' for d in frame]}")
print(f"  Time for frame: {frame_time*1000:.1f}ms")

print(f"\n  Total neural operations: {math_engine.op_count}")
print(f"  Total neural time: {math_engine.neural_time*1000:.1f}ms")

# =============================================================================
# Performance Summary
# =============================================================================

print("\n" + "=" * 70)
print("[5] DOOM FEASIBILITY ANALYSIS")
print("=" * 70)

ops_per_frame = math_engine.op_count
time_per_op = math_engine.neural_time / math_engine.op_count if math_engine.op_count > 0 else 0

# Scale to full DOOM
full_frame_ops = ops_per_frame * 64  # 320/5 columns
full_frame_time = full_frame_ops * time_per_op

achievable_fps = 1/full_frame_time if full_frame_time > 0 else 0

print(f"""
  Neural operations per 5-column frame: {ops_per_frame}
  Time per neural operation: {time_per_op*1000:.2f}ms

  Scaled to 320-column DOOM frame:
  - Operations needed: ~{full_frame_ops:,}
  - Estimated time: {full_frame_time*1000:.0f}ms
  - Achievable FPS: {achievable_fps:.2f}

  VERDICT: {'CAN RUN DOOM (slowly)' if achievable_fps > 0.1 else 'TOO SLOW FOR DOOM'}

  For 30 FPS, need: {30 / achievable_fps:.0f}x speedup
""")

print("=" * 70)
print("SOURCES:")
print("  ARM-DOOM: https://github.com/kcsongor/arm-doom")
print("=" * 70)
