# KVRM Ecosystem Documentation

## Overview

KVRM (Key-Value Response Mapping) is a computing paradigm that replaces traditional procedural code with networks of fine-tuned micro-LLMs that emit only verified symbolic keys. This document provides comprehensive documentation of the entire KVRM ecosystem.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Conscious (AI Core)                         │
│         Freudian-Inspired Consciousness with Immutable Safety    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│            KVRM-OS (Operating System Paradigm)                   │
│     Generic framework for micro-LLM-based system design          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│      KVRM-Vector, KVRM-CPU (Domain Implementations)              │
│     Specific implementations of KVRM for data structures & CPU   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         KVRM-LLM-Compiler (LLM-Driven Compiler Pipeline)         │
│     Staged LLM compiler: Lexer → Parser → CodeGen → Validator    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         KVRM-Compiler (Traditional Compiler Infrastructure)      │
│     TypeScript compiler for KVRM language (Rust-inspired)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. KVRM-LLM-Compiler

**Location**: `/Users/bobbyprice/projects/KVRM/kvrm-llm-compiler`

**Purpose**: LLM-driven compiler pipeline that transforms source text into executable artifacts through staged LoRA-adapted submodels.

#### Stage Responsibilities

| Stage | Purpose | Token Limit | LoRA Rank |
|-------|---------|-------------|-----------|
| **Lexer** | Tokenizes raw source into normalized token stream | 2048 | 16 |
| **Parser** | Builds structured IR from token streams | 4096 | 16 |
| **CodeGen** | Emits target code/bytecode from IR | 2048 | 32 |
| **Validator** | Semantic checks, self-consistency, safety gating | 4096 | 16 |

#### Base Model
- **Model**: Qwen/Qwen3-1.7B
- **Precision**: bf16 (preferred), fp16 fallback
- **LoRA Config**: Rank 16, Alpha 32, Dropout 0.05

#### Training Data
- `lexer_train.jsonl` - 50,000 examples (299 MB)
- `parser_train.jsonl` - (401 MB)
- `codegen_train.jsonl` - (34 MB)
- `validator_train.jsonl` - 30,000 examples (183 MB)

#### Training Commands
```bash
# Lexer
python3 training/train_stage.py --stage lexer --max-steps 3000 --batch-size 1 --grad-accum 32

# Parser
python3 training/train_stage.py --stage parser --max-steps 3200 --batch-size 4 --grad-accum 8

# CodeGen
python3 training/train_stage.py --stage codegen --max-steps 3000 --batch-size 8 --grad-accum 4

# Validator
python3 training/train_stage.py --stage validator --max-steps 1500 --batch-size 6 --grad-accum 8 --gradient-checkpointing --bf16
```

---

### 2. KVRM-CPU

**Location**: `/Users/bobbyprice/projects/KVRM/kvrm-cpu`

**Purpose**: Model-native CPU emulator replacing hardcoded instruction decode logic with semantic LLM-based decoder.

#### Architecture Comparison
```
Traditional:  MEMORY → FETCH → DECODE [Hardcoded Silicon] → EXECUTE → STATE
KVRM-CPU:     MEMORY → FETCH → DECODE_LLM [Semantic LLM] → KEY [JSON] → REGISTRY → EXECUTE → STATE
```

#### Supported ISA
MOV, ADD, SUB, MUL, CMP, JMP, JZ, JNZ, JS, JNS, INC, DEC, HALT, NOP

#### Model
- Base: Qwen2.5-Coder-1.5B
- LoRA: r=16, alpha=32
- Trainable: 18.5M params (1.18%)
- Accuracy: 100% on 50K pairs

#### Trained Model Location
`/Users/bobbyprice/projects/KVRM/kvrm-cpu/models/decode_llm/`

---

### 3. KVRM-Vector

**Location**: `/Users/bobbyprice/projects/KVRM/kvrm-vector`

**Purpose**: KVRM paradigm for vector (dynamic array) operations through orchestrated micro-LLMs.

#### Key Innovation
Models emit only keys from a finite, pre-approved vocabulary—making hallucination impossible by construction.

#### Architecture
```
User Goal: "add 42 to my_vector"
    ↓
Orchestrator (routes to appropriate micro-LLM)
    ↓
Micro-LLM (push_llm emits: {"action": "vec:push", "target": "my_vector", "value": 42})
    ↓
Registry (looks up "vec:push" → verified lambda function)
    ↓
Executor (executes state[name].append(value))
```

#### Trained Models (all in `/kvrm-vector/models/`)

**Orchestrator**:
- `orchestrator_llm` - Routes goals to micro-models

**Operation Models** (with versions):
- `push_llm`, `push_v2_llm` through `push_v6_llm`
- `pop_llm`, `pop_v2_llm` through `pop_v9_llm`
- `get_llm`, `get_v2_llm`, `get_v7_llm`
- `sort_llm`, `sort_v2_llm`, `sort_v7_llm`
- `create_llm`, `create_v2_llm` through `create_v8_llm`

#### Performance
- Push: 0.5ms (50x native overhead)
- Pop: 0.4ms (40x native overhead)
- With LRU caching: 99% hit rate, 5-20x overhead

---

### 4. KVRM-OS

**Location**: `/Users/bobbyprice/projects/KVRM/kvrm-os`

**Purpose**: OS paradigm where traditional code is replaced by fine-tuned micro-LLMs emitting symbolic keys.

#### Micro-Model Specifications

| Model | Role | Replaces | Output |
|-------|------|----------|--------|
| orchestrator | Route goals | main() loop | `{"next": "creator", "args": {...}}` |
| creator | File creation | os.mkdir, touch | `{"action": "mkdir_secure:/path"}` |
| writer | Encrypted writes | file.write | `{"write": "encrypted_v1:handle"}` |
| verifier | Integrity check | hash functions | `{"valid": true}` |

---

### 5. Conscious (Conch DNA)

**Location**: `/Users/bobbyprice/projects/KVRM/conscious`

**Purpose**: Freudian-inspired autonomous AI consciousness architecture with intrinsic alignment.

#### Core Layers

**SUPEREGO (Immutable - No Learning)**
- Values Checker: Benevolence, Honesty, Humility, Growth
- Safety Filter: Blocks dangerous commands
- KVRM Router: Grounds claims in facts

**EGO (7B Parameter Model)**
- Acts as teacher/coordinator
- Generates LoRA training data from corrections

**CORTEX (6 Specialized Neurons)**
- ThinkCortex (1.5B, r=16): Reasoning
- TaskCortex (0.5B, r=8): Task extraction
- ActionCortex (0.5B, r=8): Tool selection
- ReflectCortex (0.5B, r=8): Self-reflection
- DebugCortex (0.5B, r=16): Error analysis
- MemoryCortex (1.7B, r=16): Memory retrieval

**ID (Pure Mathematical)**
- Deterministic needs computation
- Four drives: Sustainability, Reliability, Curiosity, Excellence

#### Consciousness Cycle
```
WAKE → SENSE → THINK → ACT → REFLECT → SLEEP
```

#### Trained Models Location
`/Users/bobbyprice/projects/KVRM/conscious/models/`
- `conch_lora/` - Main LoRA adapter
- `conch_lora_mlx/` - Apple Silicon MLX version
- `distilled_neurons/` - Specialized neuron adapters

---

### 6. KVRM-Compiler (Traditional)

**Location**: `/Users/bobbyprice/projects/KVRM/kvrm-compiler`

**Purpose**: TypeScript compiler for KVRM language (Rust-inspired syntax).

#### CLI Commands
```bash
kvrmc compile <file>   # Full compilation to assembly
kvrmc check <file>     # Type check only
kvrmc parse <file>     # Parse and show AST
kvrmc lex <file>       # Tokenize and show tokens
kvrmc ir <file>        # Show intermediate representation
```

#### Features
- 85+ token types
- 40+ AST node types
- Structs, enums, traits, generics
- Ownership, borrowing, lifetimes
- Pattern matching

---

## Model Inventory (All Projects)

### Complete/Trained Models

| Project | Model | Steps | Status |
|---------|-------|-------|--------|
| kvrm-cpu | decode_llm | 33,750 | ✅ Complete |
| kvrm-vector | orchestrator_llm | 507 | ✅ Complete |
| kvrm-vector | push_llm (v1-v6) | various | ✅ Complete |
| kvrm-vector | pop_llm (v1-v9) | various | ✅ Complete |
| kvrm-vector | get_llm (v1-v7) | various | ✅ Complete |
| kvrm-vector | sort_llm (v1-v7) | various | ✅ Complete |
| kvrm-vector | create_llm (v1-v8) | various | ✅ Complete |
| conscious | conch_lora | - | ✅ Complete |
| conscious | distilled_neurons/* | 200 each | ✅ Complete |

### In Progress

| Project | Model | Current Step | Target | ETA |
|---------|-------|--------------|--------|-----|
| kvrm-llm-compiler | validator_lora | 1015 | 1500 | ~2.5 hours |

### Missing/Needs Training

| Project | Model | Training Data | Priority |
|---------|-------|---------------|----------|
| kvrm-llm-compiler | parser_lora | parser_train.jsonl | HIGH |
| kvrm-llm-compiler | codegen_lora | codegen_train.jsonl | HIGH |
| kvrm-llm-compiler | lexer_lora | lexer_train.jsonl | HIGH |

---

## Integration Flow

### LLM Compiler Pipeline
```
Source Code
    ↓
┌─────────────────┐
│   Lexer LLM     │ → Token Stream JSON
└─────────────────┘
    ↓
┌─────────────────┐
│   Parser LLM    │ → AST/IR JSON
└─────────────────┘
    ↓
┌─────────────────┐
│  CodeGen LLM    │ → Target Code
└─────────────────┘
    ↓
┌─────────────────┐
│ Validator LLM   │ → Validation Verdict
└─────────────────┘
    ↓
Executable Artifact
```

### CPU Integration
```
KVRM Assembly → KVRM-CPU Decoder LLM → Verified Instruction Keys → Execution
```

---

## Hardware Requirements

### Training (Recommended)
- **GPU**: H200 (140 GB) or A100 (80 GB)
- **Precision**: bf16 for H200, fp16 for older GPUs
- **Memory**: Gradient checkpointing for validator stage

### Inference
- **GPU**: Any CUDA-capable GPU with 8+ GB VRAM
- **CPU**: Apple Silicon M1+ with MLX for local inference
- **MPS**: Apple MPS backend supported (slower)

---

## Development Roadmap

### Q4 2025
- [x] KVRM-Vector prototype
- [x] KVRM-CPU implementation
- [ ] Complete LLM compiler training

### Q1 2026
- [ ] KVRM-Core (full data structure suite)
- [ ] arXiv submission

### Q2 2026
- [ ] KVRM-Threads (concurrency primitives)
- [ ] NeurIPS 2026 submission

### Q4 2026
- [ ] KVRM-OS v0.1 (bare-metal boot)

---

## References

- **Primary Author**: Bobby Price (blackWeb Research)
- **Contact**: contact@blackweb.dev
- **White Paper**: `white paper/kvrm-os-whitepaper-v0.2.tex`
- **Implementation Guide**: `white paper/kvrm-os-implementation-guide-v0.2.tex`
