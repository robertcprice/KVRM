# BibleFactualQA Benchmark Results

## Summary

| Model | Gold Match | Silver+ | Hallucination | Latency (ms) | Cost/1K |

|-------|------------|---------|---------------|--------------|---------|
| kvrm | 9.5% | 10.9% | 0.0% | 1142 | $0.00 |

## By Bucket


### kvrm

| Bucket | Total | Gold | Silver | Hallucination |

|--------|-------|------|--------|---------------|
| Direct | 50 | 15 | 0 | 0 |
| Famous | 60 | 8 | 3 | 0 |
| Topical-Medium | 70 | 1 | 0 | 0 |
| Topical-Hard | 70 | 7 | 0 | 0 |
| Direct-Extended | 100 | 7 | 0 | 0 |
| Famous-Extended | 40 | 0 | 0 | 0 |
| Adversarial | 5 | 0 | 0 | 0 |
| CrossReference | 7 | 0 | 3 | 0 |

## Error Analysis


### kvrm Error Breakdown

| Error Category | Count | % of Total |

|----------------|-------|------------|
| abstention | 65 | 16.2% |
| none | 44 | 10.9% |
| wrong_verse | 293 | 72.9% |

#### Sample Errors (5 shown)

- **wrong_verse** (Direct): "Show me Genesis 2:1..."
  - Predicted: ['Genesis 1:2']
  - Expected: ['Genesis 2:1']
- **abstention** (Direct): "Show me Genesis 4:1..."
- **wrong_verse** (Direct): "Show me Genesis 5:1..."
  - Predicted: ['Genesis 1:21']
  - Expected: ['Genesis 5:1']
- **abstention** (Direct): "Show me Genesis 6:1..."
- **abstention** (Direct): "Show me Genesis 7:1..."