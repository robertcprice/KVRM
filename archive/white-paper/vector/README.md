# KVRM-Vector

**Key-Value Response Mapping for Semantic Programming**

KVRM-Vector is a proof-of-concept implementation of the KVRM-OS paradigm: a vector data structure where every operation is handled by fine-tuned micro-language models that emit verified keys instead of traditional code.

## Overview

Traditional code:
```python
my_list = []
my_list.append(42)
print(my_list[0])
```

KVRM semantic programming:
```python
vec = KVRMVector("my_list")
vec.push(42)           # orchestrator → push_llm → {"action": "vec:push", "value": 42}
print(vec.get(0))      # orchestrator → get_llm → {"action": "vec:get", "index": 0}
```

The key insight: **models emit only keys from a finite vocabulary, making hallucination impossible by construction**.

## Quick Start

```bash
# Clone and setup
cd kvrm-vector
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run tests (mock mode - no trained models needed)
pytest tests/ -v

# Run demo
python demo/gradio_app.py
# Open http://localhost:7860

# Run benchmarks
python benchmarks/benchmark_vs_native.py
```

## Project Structure

```
kvrm-vector/
├── README.md                 # This file
├── requirements.txt          # Dependencies
├── docs/
│   └── latex/               # Whitepaper and guide LaTeX sources
├── src/
│   ├── __init__.py
│   ├── registry.py          # Immutable key→action registry
│   ├── micro_llm.py         # MicroLLM wrapper with caching
│   ├── executor.py          # Verified action execution
│   ├── orchestrator.py      # Goal→key orchestration
│   ├── kvrm_vector.py       # Main vector API
│   └── data_generator.py    # Training data generation
├── training/
│   ├── train_micro.py       # Training script
│   └── configs/             # Model configurations
├── tests/
│   ├── test_registry.py
│   ├── test_micro_llm.py
│   └── test_kvrm_vector.py
├── benchmarks/
│   └── benchmark_vs_native.py
├── demo/
│   └── gradio_app.py        # Interactive web demo
├── data/                    # Generated training data
└── models/                  # Trained micro-LLMs
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Goal                                │
│                    "add 42 to my_vector"                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Orchestrator                               │
│   Routes goals to appropriate micro-LLM based on intent         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Micro-LLM                                 │
│   push_llm emits: {"action": "vec:push", "target": "my_vector", │
│                    "value": 42}                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Registry                                 │
│   Looks up "vec:push" → verified lambda function                │
│   (immutable, integrity-checked)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Executor                                 │
│   Executes: state[name].append(value)                           │
│   Returns: updated state                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### Zero Hallucination by Construction
- Models emit **only** keys from a finite, pre-approved vocabulary
- Invalid keys are rejected at the registry level
- Cannot generate arbitrary or dangerous code

### Verified Execution
- All actions go through immutable registry
- Registry integrity verified via Merkle hash
- Full execution trace for auditing

### Semantic Programming
- Natural language goals → verified operations
- No traditional procedural code for operations
- Self-documenting through intent preservation

### Caching for Performance
- LRU cache on (context → key) mappings
- 99%+ hit rate in typical workloads
- Reduces overhead from 500x to 5-20x

## Usage Examples

### Basic Operations

```python
from src.kvrm_vector import KVRMVector

# Create vector
vec = KVRMVector("numbers", mock_mode=True)

# Push elements
vec.push(42)
vec.push(17)
vec.push(99)

# Access elements
print(vec.get(0))   # 42
print(vec[-1])      # 99
print(len(vec))     # 3

# Sort
vec.sort()
print(list(vec))    # [17, 42, 99]

# Pop
val = vec.pop()     # 99
```

### From Python List

```python
vec = KVRMVector.from_list([3, 1, 4, 1, 5], name="pi_digits")
vec.sort()
print(vec)  # KVRMVector(pi_digits, [1, 1, 3, 4, 5])
```

### With Shared Orchestrator

```python
from src.orchestrator import KVRMOrchestrator

# Share orchestrator across vectors
orch = KVRMOrchestrator(mock_mode=True)
vec1 = KVRMVector("a", orchestrator=orch)
vec2 = KVRMVector("b", orchestrator=orch)

vec1.push(1)
vec2.push(2)

# Both vectors share state
print(orch.get_state())  # {'a': [1], 'b': [2]}
```

## Training Your Own Models

### 1. Generate Training Data

```bash
python src/data_generator.py --all --output-dir data/
```

This generates ~29,000 training examples:
- orchestrator: 10,000 examples (goal → operation routing)
- create: 3,000 examples
- push: 4,000 examples
- pop: 3,000 examples
- get: 3,000 examples
- sort: 3,000 examples
- verify: 3,000 examples

### 2. Train Models

```bash
# Generate default configs
python training/train_micro.py --generate-configs

# Train all models
python training/train_micro.py --all

# Train specific model
python training/train_micro.py --model push
```

### 3. Use Trained Models

```python
vec = KVRMVector("test", mock_mode=False)  # Uses real models
```

## Benchmarks

Run benchmarks:

```bash
python benchmarks/benchmark_vs_native.py --n 500 --iterations 5
```

Expected results (mock mode):

| Operation | Native | KVRM | Overhead |
|-----------|--------|------|----------|
| Push      | 0.01ms | 0.5ms | 50x |
| Pop       | 0.01ms | 0.4ms | 40x |
| Access    | 0.001ms | 0.3ms | 300x |
| Sort      | 0.1ms | 0.2ms | 2x |

With real models and caching:
- First inference: ~50ms (model forward pass)
- Cached inference: ~0.5ms (cache lookup)
- With distillation: ~0.1ms (decision tree)

## Documentation

- **Whitepaper**: `docs/latex/kvrm-os-whitepaper-v0.2.tex`
- **Implementation Guide**: `docs/latex/kvrm-os-implementation-guide-v0.2.tex`

Compile to PDF:
```bash
cd docs/latex
pdflatex kvrm-os-whitepaper-v0.2.tex
pdflatex kvrm-os-implementation-guide-v0.2.tex
```

## Roadmap

- **Q4 2025**: KVRM-Vector prototype (this repo)
- **Q1 2026**: KVRM-Core (full data structure suite)
- **Q2 2026**: KVRM-Threads (concurrency primitives)
- **Q3 2026**: Self-improvement mechanism
- **Q4 2026**: KVRM-OS v0.1 (bare-metal boot)

## Contributing

This is a research prototype. Contributions welcome for:
- Additional data structure implementations
- Training optimizations
- Benchmark improvements
- Documentation

## License

MIT License - see LICENSE file.

## Citation

```bibtex
@misc{kvrm2025,
  title={KVRM-OS: Key-Value Response Mapping for Model-Native Computing},
  author={Price, Bobby},
  year={2025},
  publisher={blackWeb Research}
}
```

## Contact

- Email: contact@blackweb.dev
- GitHub: [kvrm-vector](https://github.com/blackweb/kvrm-vector)
