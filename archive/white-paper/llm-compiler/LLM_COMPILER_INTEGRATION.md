# KVRM LLM Compiler - Integration Guide

## Overview

The KVRM LLM Compiler is a staged, LLM-driven toolchain that transforms source text into executable artifacts. Each stage uses a fine-tuned LoRA adapter on Qwen/Qwen3-1.7B.

---

## Architecture

### Pipeline Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         KVRM LLM Compiler Pipeline                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   Source Code                                                                 │
│       │                                                                       │
│       ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                      LEXER STAGE                                     │    │
│   │  Input:  Raw source text                                            │    │
│   │  Output: Token stream (JSON)                                        │    │
│   │  Model:  Qwen3-1.7B + lexer_lora                                   │    │
│   │  Tokens: 2048 max                                                   │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                       │
│       ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                      PARSER STAGE                                    │    │
│   │  Input:  Token stream                                               │    │
│   │  Output: Abstract Syntax Tree / IR (JSON)                           │    │
│   │  Model:  Qwen3-1.7B + parser_lora                                  │    │
│   │  Tokens: 4096 max                                                   │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                       │
│       ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                      CODEGEN STAGE                                   │    │
│   │  Input:  AST / IR                                                   │    │
│   │  Output: Target code / bytecode                                     │    │
│   │  Model:  Qwen3-1.7B + codegen_lora (rank 32)                       │    │
│   │  Tokens: 2048 max                                                   │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                       │
│       ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                      VALIDATOR STAGE                                 │    │
│   │  Input:  Generated code + original source                          │    │
│   │  Output: Validation verdict + diagnostics                          │    │
│   │  Model:  Qwen3-1.7B + validator_lora                               │    │
│   │  Tokens: 4096 max                                                   │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                       │
│       ▼                                                                       │
│   Verified Executable Artifact                                               │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## CPU Integration

### KVRM-CPU Decoder Integration

The KVRM LLM Compiler can emit assembly that targets the KVRM-CPU decoder. This creates an end-to-end LLM-driven execution pipeline.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                    Full KVRM Execution Pipeline                                │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   KVRM Source → [LLM Compiler] → KVRM Assembly → [KVRM-CPU] → Execution       │
│                                                                                │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│   │ LLM Compiler    │    │ KVRM Assembly   │    │ KVRM-CPU        │           │
│   │ (4 stages)      │ →  │ (Target ISA)    │ →  │ (LLM Decoder)   │           │
│   │ Qwen3-1.7B      │    │                 │    │ Qwen2.5-1.5B    │           │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘           │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Target ISA (KVRM-CPU)

The CodeGen stage can target the following KVRM-CPU instructions:

| Instruction | Description | Example |
|-------------|-------------|---------|
| MOV | Move data | `MOV R0, R1` |
| ADD | Addition | `ADD R0, R1` |
| SUB | Subtraction | `SUB R0, R1` |
| MUL | Multiplication | `MUL R0, R1` |
| CMP | Compare | `CMP R0, R1` |
| JMP | Unconditional jump | `JMP label` |
| JZ | Jump if zero | `JZ label` |
| JNZ | Jump if not zero | `JNZ label` |
| JS | Jump if sign | `JS label` |
| JNS | Jump if not sign | `JNS label` |
| INC | Increment | `INC R0` |
| DEC | Decrement | `DEC R0` |
| HALT | Stop execution | `HALT` |
| NOP | No operation | `NOP` |

### Register Set

- **R0-R7**: General purpose registers
- **PC**: Program counter
- **FLAGS**: Zero (Z), Sign (S), Overflow (V)

---

## Model Configuration

### Base Configuration (`src/kvrm_llm_compiler/config.py`)

```python
BASE_MODEL = "Qwen/Qwen3-1.7B"
LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05

# Token limits per stage
LEXER_MAX_TOKENS = 2048
PARSER_MAX_TOKENS = 4096
CODEGEN_MAX_TOKENS = 2048
VALIDATOR_MAX_TOKENS = 4096
```

### Stage-Specific Overrides

| Stage | LoRA Rank | Alpha | Notes |
|-------|-----------|-------|-------|
| Lexer | 16 | 32 | Standard config |
| Parser | 16 | 32 | Standard config |
| CodeGen | **32** | 64 | Higher rank for complex generation |
| Validator | 16 | 32 | Standard config |

---

## Training

### Hardware Requirements

**Recommended (Remote GPU)**:
- NVIDIA H200 (140 GB) - bf16 precision
- NVIDIA A100 (80 GB) - bf16/fp16 precision

**Local (Development/Testing)**:
- Apple Silicon M1+ - MPS backend, fp16
- NVIDIA RTX 4090 - fp16 precision

### Training Commands

```bash
# On H200/A100 (vast.ai or similar)
cd kvrm-llm-compiler

# Lexer (50K examples, ~3000 steps)
python3 training/train_stage.py \
    --stage lexer \
    --epochs 3 \
    --max-steps 3000 \
    --batch-size 8 \
    --grad-accum 4 \
    --bf16

# Parser (401MB data, ~3200 steps)
python3 training/train_stage.py \
    --stage parser \
    --epochs 3 \
    --max-steps 3200 \
    --batch-size 4 \
    --grad-accum 8 \
    --bf16

# CodeGen (34MB data, ~3000 steps)
python3 training/train_stage.py \
    --stage codegen \
    --epochs 3 \
    --max-steps 3000 \
    --batch-size 8 \
    --grad-accum 4 \
    --bf16

# Validator (30K examples, ~1500 steps, needs gradient checkpointing)
python3 training/train_stage.py \
    --stage validator \
    --epochs 4 \
    --max-steps 1500 \
    --batch-size 6 \
    --grad-accum 8 \
    --gradient-checkpointing \
    --bf16
```

### OOM Mitigation

The validator stage requires special handling due to memory constraints:

1. **Enable gradient checkpointing**: `--gradient-checkpointing`
2. **Reduce batch size**: Use 4-6 instead of 8
3. **Increase gradient accumulation**: 8-16 steps
4. **Use bf16 precision**: Saves memory vs fp32

### Training Monitoring

```bash
# Watch training progress
tail -f train.log

# Check GPU utilization
nvidia-smi -l 1

# Check specific metrics
grep "loss" train.log | tail -20
```

---

## Inference

### Loading Trained Models

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen3-1.7B",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B")

# Load LoRA adapter for specific stage
lexer_model = PeftModel.from_pretrained(base_model, "models/lexer_lora")
parser_model = PeftModel.from_pretrained(base_model, "models/parser_lora")
codegen_model = PeftModel.from_pretrained(base_model, "models/codegen_lora")
validator_model = PeftModel.from_pretrained(base_model, "models/validator_lora")
```

### Pipeline Execution

```python
from kvrm_llm_compiler.pipeline import CompilerPipeline

pipeline = CompilerPipeline(
    lexer_adapter="models/lexer_lora",
    parser_adapter="models/parser_lora",
    codegen_adapter="models/codegen_lora",
    validator_adapter="models/validator_lora"
)

# Compile source code
result = pipeline.compile(source_code)

# Access intermediate outputs
tokens = result.token_stream
ast = result.ast
code = result.generated_code
validation = result.validation_result
```

---

## Data Format

### Training Data Structure

Each stage uses JSONL format with chat-style messages:

```jsonl
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

#### Lexer Example
```json
{
  "messages": [
    {"role": "user", "content": "Tokenize: let x = 42;"},
    {"role": "assistant", "content": "[{\"type\": \"LET\", \"value\": \"let\"}, {\"type\": \"IDENT\", \"value\": \"x\"}, {\"type\": \"EQ\", \"value\": \"=\"}, {\"type\": \"NUMBER\", \"value\": \"42\"}, {\"type\": \"SEMI\", \"value\": \";\"}]"}
  ]
}
```

#### Parser Example
```json
{
  "messages": [
    {"role": "user", "content": "Parse tokens: [{\"type\": \"LET\", ...}]"},
    {"role": "assistant", "content": "{\"type\": \"VariableDecl\", \"name\": \"x\", \"value\": {\"type\": \"NumberLiteral\", \"value\": 42}}"}
  ]
}
```

---

## Output Formats

### Token Stream (Lexer Output)
```json
[
  {"type": "FN", "value": "fn", "line": 1, "col": 0},
  {"type": "IDENT", "value": "main", "line": 1, "col": 3},
  {"type": "LPAREN", "value": "(", "line": 1, "col": 7},
  {"type": "RPAREN", "value": ")", "line": 1, "col": 8},
  {"type": "LBRACE", "value": "{", "line": 1, "col": 10}
]
```

### AST (Parser Output)
```json
{
  "type": "FunctionDecl",
  "name": "main",
  "params": [],
  "return_type": null,
  "body": {
    "type": "Block",
    "statements": []
  }
}
```

### Generated Code (CodeGen Output)
```asm
; KVRM Assembly for main()
_main:
    MOV R0, 0       ; Initialize return value
    HALT            ; End program
```

### Validation Verdict (Validator Output)
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "coverage": {
    "type_safety": true,
    "memory_safety": true,
    "control_flow": true
  }
}
```

---

## File Structure

```
kvrm-llm-compiler/
├── src/
│   └── kvrm_llm_compiler/
│       ├── config.py           # Configuration constants
│       ├── formats/
│       │   ├── token_format.py # Token stream definitions
│       │   └── ast_format.py   # AST node definitions
│       ├── stages/
│       │   ├── base_stage.py   # Base stage class
│       │   ├── lexer_llm.py    # Lexer stage
│       │   ├── parser_llm.py   # Parser stage
│       │   └── codegen_llm.py  # CodeGen stage
│       ├── validator/
│       │   └── unified_validator.py
│       └── pipeline/
│           └── compiler_pipeline.py
├── training/
│   ├── train_stage.py          # Main training script
│   ├── generate_lexer_data.py
│   ├── generate_parser_data.py
│   ├── generate_codegen_data.py
│   └── generate_validator_data.py
├── data/
│   ├── lexer_train.jsonl
│   ├── parser_train.jsonl
│   ├── codegen_train.jsonl
│   └── validator_train.jsonl
├── models/
│   ├── lexer_lora/
│   ├── parser_lora/
│   ├── codegen_lora/
│   └── validator_lora/
└── docs/
    ├── README.md
    ├── training_chronology.md
    ├── whitepaper.tex
    ├── KVRM_ECOSYSTEM.md
    └── LLM_COMPILER_INTEGRATION.md
```

---

## Current Status

### Training Status (as of 2024-12-14)

| Stage | Status | Progress | Location |
|-------|--------|----------|----------|
| lexer_lora | **NOT TRAINED** | 0% | Needs training |
| parser_lora | **MISSING** | N/A | Lost - needs retraining |
| codegen_lora | **MISSING** | N/A | Lost - needs retraining |
| validator_lora | IN PROGRESS | 68% (1015/1500) | vast.ai remote |

### Priority Training Queue

1. **Validator** - Complete current run (~2.5 hours remaining)
2. **Parser** - High priority, 3200 steps needed
3. **CodeGen** - High priority, 3000 steps needed
4. **Lexer** - 3000 steps needed

---

## Troubleshooting

### Common Issues

**OOM during training**:
- Enable `--gradient-checkpointing`
- Reduce `--batch-size` to 4 or lower
- Increase `--grad-accum` proportionally

**KeyError: 'qwen3'**:
- Upgrade transformers: `pip install transformers>=5.0.0.dev0`
- Or install from source

**MPS backend issues (Apple Silicon)**:
- Use fp16 instead of bf16
- Reduce batch size to 1
- Expect slower training (200+ seconds per step)

**Missing torch module**:
- Activate virtual environment
- Install dependencies: `pip install torch transformers peft accelerate datasets`
