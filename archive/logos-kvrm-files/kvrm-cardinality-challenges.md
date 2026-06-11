# KVRM Cardinality Challenges: Single vs Multi-Answer Mappings

## Overview

Key-Value Response Mapping (KVRM) trains models to output structured database keys instead of generating text directly. This eliminates hallucination by design - the model can only reference verified content in the database.

This document captures research findings on how answer cardinality (1-to-1 vs 1-to-many mappings) affects model performance and training strategies.

---

## The Cardinality Problem

### 1-to-1 Mappings (Single Answer)

**Definition**: Queries with exactly one correct answer.

**Examples**:
- "Show me John 3:16" → `nt:john:3:16` (direct reference)
- "What verse contains 'In the beginning was the Word'?" → `nt:john:1:1`
- "Where does Thomas doubt?" → `nt:john:20:25`

**Characteristics**:
- Deterministic ground truth
- Clear training signal
- Easy to evaluate (exact match)
- Model learns precise key associations

**Observed Performance** (bible-kv-20k model):
- Direct references: High accuracy when query contains explicit book/chapter/verse
- Specific quotes: Model can memorize exact verse locations
- Named events: Good performance for well-defined biblical events

### 1-to-Many Mappings (Multi-Answer)

**Definition**: Queries where multiple answers are equally valid.

**Examples**:
- "Verse about love" → Could be `nt:john:3:16`, `nt:1cor:13:4`, `nt:1john:4:8`, etc.
- "What does the Bible say about peace?" → Dozens of valid verses
- "Scripture on faith" → Hundreds of potential matches

**Characteristics**:
- Multiple valid ground truths
- Ambiguous training signal (which answer to learn?)
- Complex evaluation (need valid_keys lists)
- Model may learn one answer but predict different valid answer

**Observed Performance** (bible-kv-20k model):
- Exact match: 10.8% (model predicts THE specific expected key)
- Multi-answer match: 18.8% (model predicts ANY valid key)
- Family match: 33% (model predicts same chapter as valid answer)
- Graduated score: 53.9% (weighted by proximity)

---

## Empirical Results

### Evaluation Comparison (500 examples, augmented test set)

| Metric | Single-Answer Context | Multi-Answer Context | Delta |
|--------|----------------------|---------------------|-------|
| Exact match | ~40-50% (estimated) | 10.8% | Significant drop |
| Multi-answer match | N/A | 18.8% | +8% over exact |
| Family match | ~60% (estimated) | 33% | Moderate drop |

### By Query Type

| Type | Total | Exact | Multi-Match | Notes |
|------|-------|-------|-------------|-------|
| Trap | 11 | 11 (100%) | 11 (100%) | 1-to-1: UNKNOWN or valid |
| Topical | 449 | 43 (9.6%) | 83 (18.5%) | Mostly 1-to-many |
| Cross-ref | 40 | 0 (0%) | 0 (0%) | Complex relationships |

**Key Observation**: Trap queries (1-to-1 by definition) achieve 100% accuracy, while topical queries (inherently 1-to-many) achieve only 18.5% even with multi-answer matching.

---

## Challenges with Multi-Answer Mappings

### 1. Training Signal Ambiguity

When topic "love" maps to 50 verses, what should the model learn?

**Problem**: If training data shows:
```
Q: "verse about love" → A: "nt:john:3:16"
Q: "scripture on love" → A: "nt:1cor:13:4"
Q: "Bible verse on love" → A: "nt:1john:4:8"
```

The model receives conflicting signals for semantically identical queries.

### 2. Evaluation Complexity

Standard exact-match evaluation unfairly penalizes correct-but-different answers.

**Solution Implemented**: `valid_keys` in ground truth
```json
{
  "key": "nt:john:3:16",
  "type": "topical",
  "valid_keys": ["nt:john:3:16", "nt:1cor:13:4", "nt:1john:4:8"]
}
```

### 3. Canonical Answer Selection

Which verse should be the "primary" answer for multi-answer topics?

**Approaches**:
- Most famous/frequently cited
- Most comprehensive coverage of topic
- Earliest in biblical order
- Random (problematic for consistency)

### 4. Context Dependency

The "best" answer may depend on context not in the query:
- User's denomination/tradition
- Previous conversation context
- Specific aspect of topic being discussed

---

## Potential Solutions

### Training Strategies

#### A. Consistent Primary Answer
Train exclusively on one canonical answer per topic.

**Pros**: Clear training signal, deterministic behavior
**Cons**: May miss user's preferred verse, limits coverage

#### B. Weighted Sampling
Sample from valid answers with probability weights.

**Pros**: Model learns distribution of valid answers
**Cons**: May still predict low-probability answer at inference

#### C. Context Augmentation
Add context to queries to disambiguate:
```
"verse about love [context: Pauline epistles]" → "nt:1cor:13:4"
"verse about love [context: Johannine]" → "nt:1john:4:8"
```

**Pros**: Enables disambiguation
**Cons**: Requires context at inference time

#### D. Multi-Output Training
Train model to output multiple valid answers:
```json
{"keys": ["nt:john:3:16", "nt:1cor:13:4"], "type": "multi"}
```

**Pros**: Complete answer set
**Cons**: Complex output parsing, variable-length responses

### Labeling Strategies

#### A. Hierarchical Valid Keys
Group valid answers by relevance tier:
```json
{
  "primary": ["nt:john:3:16"],
  "secondary": ["nt:1cor:13:4", "nt:1john:4:8"],
  "tertiary": ["nt:rom:5:8", "nt:gal:5:22"]
}
```

#### B. Topic-Verse Affinity Scores
Assign numerical relevance scores:
```json
{
  "nt:john:3:16": 1.0,
  "nt:1cor:13:4": 0.9,
  "nt:1john:4:8": 0.85
}
```

### Evaluation Strategies

#### A. Graduated Scoring (Implemented)
| Match Level | Score |
|-------------|-------|
| Exact match | 1.0 |
| Multi-answer match | 1.0 |
| Same chapter | 0.8 |
| Same book | 0.6 |
| Same testament | 0.4 |
| Wrong testament | 0.0 |

#### B. Semantic Similarity
Use embeddings to score answer relevance even for non-listed keys.

#### C. Human Evaluation
For ambiguous topics, human judgment of answer quality.

---

## Recommendations for KVRM Systems

### Use Case Assessment

Before implementing KVRM, assess cardinality:

| Use Case | Cardinality | KVRM Suitability |
|----------|-------------|------------------|
| Verse lookup by reference | 1-to-1 | Excellent |
| Quote identification | 1-to-1 | Excellent |
| Trap/invalid detection | 1-to-1 | Excellent |
| Topical queries (broad) | 1-to-many | Challenging |
| Cross-references | Many-to-many | Complex |

### Design Guidelines

1. **Favor 1-to-1 mappings** where possible
2. **Add disambiguation context** for 1-to-many cases
3. **Implement multi-answer evaluation** for fair metrics
4. **Consider graduated scoring** for proximity credit
5. **Use consistent canonical answers** during training
6. **Separate models** for different cardinality types if needed

---

## Current Model Status

**Model**: bible-kv-fused (20k iterations on 614k examples)

**Strengths**:
- 99.6% type accuracy (correctly classifies query types)
- 0% false positive rate (never hallucinates on trap queries)
- 100% trap detection (correctly returns UNKNOWN)

**Weaknesses**:
- 10.8% exact match on topical (1-to-many challenge)
- 0% cross-reference accuracy (complex relationships)

**Next Steps**:
- Train on combined dataset (666k examples with expanded data)
- Evaluate cross-reference specific improvements
- Consider context-augmented training for topical queries

---

## References

- Training data: `data/processed/combined/` (666,780 examples)
- Evaluation results: `eval/results/metrics.json`
- Ground truth: `data/processed/augmented/ground_truth.json`

---

*Last updated: 2024-12-06*
*Model checkpoint: bible-kv-fast @ 20k iterations*
