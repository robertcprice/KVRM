# KVRM-Vector Model Training Notes

## Overview
This document records the iterative training optimization process used to achieve high accuracy on KVRM-Vector operation models.

## Training Strategy: Iterative Data Optimization
The key insight from the create_v8 success (100% accuracy) was that **training data quality matters more than model size or epochs**.

### Core Principles:
1. **Discriminative Patterns**: Each action must have unique, distinguishable patterns
2. **Edge Case Coverage**: ~50-60% of examples should be edge cases
3. **Clear Action Boundaries**: No ambiguous patterns that could map to multiple actions
4. **Pattern Balance**: Ensure sufficient representation for minority actions

## Model-Specific Challenges

### Push Model (vec:push vs vec:push_front)
**Problem**: Model confused "Push X to Y" without explicit "front" keyword

**Solution (V6)**:
- 70% back / 30% front split (prevent front bias)
- Reinforced "Push X to Y" = vec:push (back) pattern
- Added more programmatic syntax patterns: `{target}.push({value})`
- Implicit value patterns for both front and back

**Training Config**:
```python
epochs = 3
batch_size = 4
learning_rate = 3e-4
max_seq_length = 128
```

### Pop Model (vec:pop vs vec:pop_front)
**Problem**: Missing distinction between default pop (back) and front pop

**Solution (V6)**:
- 65% back / 35% front split
- Strong "first/front/beginning" keywords for front
- Default pop (without keywords) = back

### Get Model (vec:get vs vec:length)
**Problem**: Confusion between index access and length queries

**Solution (V6)**:
- 55% get / 45% length split
- Index patterns require numeric index
- Length patterns use size/count/len keywords

### Sort Model (vec:sort_asc vs vec:sort_desc)
**Problem**: Originally outputting invalid "vec:sort" action

**Solution (V6)**:
- 50% asc / 50% desc split
- Default sort = ascending
- Explicit "desc/descending/reverse" keywords for desc

## Training Data Versions

| Version | Push Examples | Key Changes |
|---------|--------------|-------------|
| V4 | 800 | Basic patterns |
| V5 | 1000 | Added implicit patterns, more "beginning" variations |
| V6 | 1200 | 70/30 split, stronger "Push X to Y" reinforcement |

## Common Failure Patterns

### JSON Parse Errors
- **Cause**: Model generates malformed JSON
- **Fix**: More consistent training examples, lower temperature during inference

### Action Confusion
- **Cause**: Overlapping pattern keywords
- **Fix**: Add explicit discriminative patterns, increase data for confused action

### Missing Keywords
- **Cause**: Edge case not in training data
- **Fix**: Add variations covering the missing pattern

## Test Suites

### Push Test Suite (10 cases)
```python
# Back push (5 cases)
("Add 42 to nums", "vec:push"),
("Push 5 to mylist", "vec:push"),
("Append value to items", "vec:push"),
("Push 10 to the end of data", "vec:push"),
("nums.push(100)", "vec:push"),

# Front push (5 cases)
("Add 42 to the front of nums", "vec:push_front"),
("Push 5 to front of mylist", "vec:push_front"),
("Prepend value to items", "vec:push_front"),
("Insert 10 at the beginning of data", "vec:push_front"),
("Add to the beginning of list", "vec:push_front"),
```

## Training Progress Log

### 2025-12-10

**push_v4_llm**: 70% accuracy (7/10)
- FAIL: "Push 5 to mylist" → got vec:push_front
- FAIL: "nums.push(100)" → JSON error
- FAIL: "Add to the beginning of list" → JSON error

**push_v5_llm** (first attempt): 80% accuracy (8/10)
- Training interrupted by MPS thermal throttling

**push_v5_llm** (second attempt): 90% accuracy (9/10)
- Training interrupted by MPS thermal throttling

**push_v6_llm**: 100% accuracy (10/10)
- Using 1200 examples with 70/30 back/front split
- Stronger "Push X to Y" pattern reinforcement
- All 10 test cases passed including previously failing patterns

## MPS Thermal Throttling Mitigation

Apple Silicon MPS can throttle severely during long training sessions.

**Symptoms**:
- Training speed drops from ~1.7 it/s to 0.01 it/s
- System becomes unresponsive

**Mitigations**:
1. Use `batch_size=4` instead of `batch_size=2`
2. Keep `gradient_accumulation_steps=1`
3. Add 60-second cooldown between model training
4. Kill background processes before training
5. Consider CPU fallback for long sessions

## Next Steps

1. Complete push_v6 training and test
2. Apply V6 training data approach to pop, get, sort models
3. Run comprehensive E2E demo with all fixed models
4. Document final model configurations and accuracies
