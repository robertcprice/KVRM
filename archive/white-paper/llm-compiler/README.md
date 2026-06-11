# KVRM LLM Compiler Documentation

## Overview
LLM-driven compiler pipeline for KVRM projects. This package defines the configuration scaffolding, default base model (Qwen/Qwen3-1.7B), and LoRA tuning settings used across compiler stages.

## Contents
- Core config and defaults live in `src/kvrm_llm_compiler/config.py` (LoRA rank 16, alpha 32; stage token limits; base model path).
- Training assets and scripts:
  - `training/train_stage.py` CLI for LoRA tuning per stage.
  - `models/` holds trained adapters (lexer/parser/codegen complete; validator in progress during the latest run).
- Tests and pipeline stubs in `tests/` and `src/kvrm_llm_compiler/`.

## Guides
- **Training chronology & experiments**: `docs/training_chronology.md` — timeline of runs, OOM mitigations, hardware/stack, current validator status.
- **Quick start**:
  1. Install deps: `pip install -r requirements.txt` or `pip install torch transformers peft accelerate datasets`.
  2. Train a stage: `python3 training/train_stage.py --stage <lexer|parser|codegen|validator> [--max-steps N --batch-size B --grad-accum G]`.
  3. Outputs land in `models/<stage>_lora`.

## Status (at last update)
- Trained: lexer_lora, parser_lora, codegen_lora.
- Validator: running at 1500 steps (batch 6, grad_accum 8, gradient checkpointing, bf16); see `train.log` on the active host for live progress.

## Pointers
- Project root README: `../README.md`
- Training log (remote): `kvrm-llm-compiler/train.log`
