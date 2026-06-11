# KVRM LLM Compiler: Research Issues and Solutions

**Document Version**: 1.0.0
**Last Updated**: 2024-12-14
**Author**: Bobby Price (blackWeb Research)

---

## Executive Summary

This document catalogues the technical challenges encountered during the development of the KVRM LLM Compiler and the solutions implemented. These findings are critical for understanding the behavior of small LLMs in structured output generation tasks and provide guidance for future KVRM system development.

---

## Table of Contents

1. [Issue #1: Prompt Format Mismatch](#issue-1-prompt-format-mismatch)
2. [Issue #2: Missing Chat Template](#issue-2-missing-chat-template)
3. [Issue #3: JSON Truncation Error](#issue-3-json-truncation-error)
4. [Issue #4: Control Character Corruption](#issue-4-control-character-corruption)
5. [Issue #5: Training Data Loss](#issue-5-training-data-loss)
6. [Issue #6: Memory Constraints](#issue-6-memory-constraints)
7. [Lessons Learned](#lessons-learned)

---

## Issue #1: Prompt Format Mismatch

### Problem Statement

After training LoRA adapters on vast.ai and loading them locally for inference, the models produced **random training examples** instead of processing the input data.

### Symptoms

```
Input: "let x = 5\nprint x"
Expected: {"tokens": [{"type": "LET", ...}, ...]}
Actual: (Random training data from the dataset)
```

The model appeared to be "reciting" memorized training examples rather than generalizing.

### Root Cause

The inference prompt format did not match the training data format:

**Training format**:
```
Tokenize the following KVRM program:
let x = 5
print x
```

**Inference format (incorrect)**:
```
Please tokenize this KVRM code and return JSON: let x = 5...
```

### Solution

Updated all stage prompts to match training data exactly:

| Stage | Correct Prompt Format |
|-------|----------------------|
| Lexer | `Tokenize the following KVRM program:\n{source}` |
| Parser | `Parse the following KVRM tokens into an AST:\n{json_tokens}` |
| CodeGen | `Generate KVRM assembly for this AST:\n{json_ast}` |

### Files Modified

- `stages/lexer_llm.py:45`
- `stages/parser_llm.py:46`
- `stages/codegen_llm.py:46`

---

## Issue #2: Missing Chat Template

### Problem Statement

Even with correct prompt format, models still produced incorrect outputs. Investigation revealed that Qwen3 models were trained with a specific chat format that wasn't being applied during inference.

### Symptoms

Model outputs contained `<think></think>` tags (Qwen3's reasoning format) but the response extraction wasn't handling them properly.

### Root Cause

Training data used Hugging Face's chat format:
```json
{
  "messages": [
    {"role": "user", "content": "Tokenize the following KVRM program:\n..."},
    {"role": "assistant", "content": "{\"tokens\": [...]}"}
  ]
}
```

Inference was passing raw prompts without the chat template wrapper.

### Solution

Applied `apply_chat_template` in the `_generate` method:

```python
def _generate(self, prompt: str) -> str:
    # Use chat format to match training data
    messages = [{"role": "user", "content": prompt}]
    formatted_prompt = self._tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    outputs = self._pipeline(formatted_prompt, **self.generation_kwargs)
    # ... extract assistant response
```

### Files Modified

- `stages/base_stage.py:83-97`

---

## Issue #3: JSON Truncation Error

### Problem Statement

Complex programs caused `JSONDecodeError: Expecting ',' delimiter: line 1 column N` where N equaled the exact JSON length.

### Symptoms

```
Error: JSONDecodeError: Expecting ',' delimiter: line 1 column 1705 (char 1704)
JSON length: 1705 characters
```

The error position matching the JSON length indicated truncation, not malformation.

### Root Cause

The `max_new_tokens` limit caused generation to stop mid-JSON. For complex programs producing ~2000 tokens of JSON output, the model would emit:

```json
{"tokens": [...], {"type": "EOF", "value": null, "line": 8, "column": 1}]
```

Missing the final `}` to close the outer object.

### Solution

Added truncation recovery to `_parse_json`:

```python
# If we get here, the JSON might be truncated (depth > 0)
# This happens when max_new_tokens limit cuts off generation mid-JSON.
# Error: "Expecting ',' delimiter" at the exact JSON length position.
# Fix: Add the missing closing braces to complete the structure.
if depth > 0:
    json_portion = text[start:]
    json_portion += "}" * depth  # Add missing closing braces
    try:
        return json.loads(json_portion)
    except json.JSONDecodeError:
        pass
```

### Prevention

- Increase `max_new_tokens` for complex programs (2048 → 4096)
- Consider training with shorter output sequences
- Add early stopping detection for complete JSON

### Files Modified

- `stages/base_stage.py:164-186` (documented in docstring at line 99-111)

---

## Issue #4: Control Character Corruption

### Problem Statement

Models outputting NEWLINE token values with literal newline characters instead of escaped `\n` sequences caused JSON parsing failures.

### Symptoms

```python
# Model output (problematic)
{"type": "NEWLINE", "value": "
"}

# Expected
{"type": "NEWLINE", "value": "\n"}
```

### Root Cause

The base Qwen3 model, when not sufficiently fine-tuned, would sometimes output literal control characters inside JSON string values. This is invalid JSON.

### Solution

Added `escape_control_chars` function to pre-process JSON before parsing:

```python
def escape_control_chars(s: str) -> str:
    """Escape literal control characters that appear inside JSON strings."""
    result = []
    in_string = False
    for char in s:
        if char == '"' and (i == 0 or s[i-1] != '\\'):
            in_string = not in_string
        elif in_string and char == '\n':
            result.append('\\n')
        # ... handle \r, \t similarly
    return ''.join(result)
```

### Note

After sufficient training (1500+ steps), the models learned to output properly escaped JSON. This fix remains for robustness.

### Files Modified

- `stages/base_stage.py:104-123`

---

## Issue #5: Training Data Loss

### Problem Statement

Previously trained `parser_lora` and `codegen_lora` models were lost when a vast.ai instance was terminated.

### Impact

- Parser: 3200 steps of training (~18 GPU hours) lost
- CodeGen: 3000 steps of training (~10 GPU hours) lost

### Root Cause

1. No automatic backup after training completion
2. Reliance on cloud instance storage without redundancy
3. Instance terminated before manual download

### Solution

Implemented automatic model sync:

```bash
# sync_models.sh - Runs after each training stage
scp -r -P $PORT root@$HOST:/root/kvrm-llm-compiler/models/* ./models/

# Also added to training script
checkpoint_callback = CheckpointCallback(save_steps=250)  # Frequent saves
```

### Prevention Measures

1. Checkpoint every 250 steps (vs 500 previously)
2. Automatic sync to local after each checkpoint
3. Backup to secondary storage (S3/GCS) for production

---

## Issue #6: Memory Constraints

### Problem Statement

Validator stage caused OOM (Out of Memory) errors on H200 140GB GPU.

### Symptoms

```
CUDA out of memory: 125 GB allocated
Killed at step 0
```

### Root Cause

Validator training data produces longer output sequences than other stages, requiring more memory for gradient computation.

### Solution

Validator-specific configuration:
- Reduced batch size: 8 → 6
- Enabled gradient checkpointing
- Reduced gradient accumulation: 8 → 6

```bash
python train_stage.py \
    --stage validator \
    --batch-size 6 \
    --grad-accum 6 \
    --gradient-checkpointing \
    --bf16
```

### Hardware Utilization Guidelines

| Stage | Max Batch | Grad Accum | Est. VRAM | Notes |
|-------|-----------|------------|-----------|-------|
| Lexer | 24 | 3 | ~60GB | Shortest outputs |
| Parser | 24 | 3 | ~70GB | Medium outputs |
| CodeGen | 20 | 4 | ~80GB | Variable outputs |
| Validator | 6 | 6 | ~100GB | Longest outputs |

---

## Lessons Learned

### 1. Prompt Engineering is Critical

Small LLMs are extremely sensitive to prompt format. Even minor deviations from training format cause complete failures. **Always use identical prompts for training and inference.**

### 2. Chat Templates Matter

Models trained with chat-formatted data must use `apply_chat_template()` during inference. This is easy to overlook but essential for Qwen, LLaMA, and similar models.

### 3. Robust JSON Parsing is Essential

LLM JSON output is inherently unreliable. Implement:
- Control character escaping
- Truncation recovery
- Balanced brace extraction
- Multiple fallback strategies

### 4. Backup Early and Often

Cloud GPU instances are ephemeral. Implement automatic backup to prevent training loss.

### 5. Memory Varies by Task

Different stages of the same pipeline can have dramatically different memory requirements. Profile before committing to batch sizes.

### 6. Test with Complex Inputs

Simple test cases pass easily. Always test with:
- Maximum expected input length
- Nested structures (if/else, while loops)
- Edge cases (empty inputs, special characters)

---

## Appendix: Error Message Reference

| Error | Likely Cause | Solution |
|-------|-------------|----------|
| "Expecting ',' delimiter at column N = length" | JSON truncated | Increase max_new_tokens, add missing braces |
| "Invalid control character at position N" | Literal newlines in JSON | Apply escape_control_chars |
| "Model outputs random training data" | Prompt format mismatch | Match training prompt exactly |
| "CUDA out of memory" | Batch too large | Reduce batch, enable gradient checkpointing |
| "Model ignores input" | Missing chat template | Apply apply_chat_template |

---

## References

- `base_stage.py` - Core implementation with all fixes
- `training_chronology.md` - Training timeline and configurations
- `KVRM_MASTER_PAPER.md` - Main KVRM research document

---

*Document generated as part of KVRM Research - blackWeb Research*
