# kvrm-core

kvrm-core is the Phase 1 KVRM substrate for bounded decisions over finite audited action spaces.

What it is:
- registry-constrained decision runtime
- abstention and fallback aware
- deterministic validation and execution
- JSON-serializable audit logs
- reusable core for future demos

What it is not:
- a domain demo
- an end-to-end LLM system
- a claim of formal verification
- a replacement for domain-specific safety engineering

Core runtime order:
1. load registry
2. normalize input features
3. generate selector candidates
4. calibrate confidence
5. abstain if below threshold
6. validate chosen action
7. execute deterministic action or safe fallback
8. emit audit record

Key modules:
- `registry.py` - registry loading, validation, digesting
- `selectors.py` - baseline selectors
- `calibration.py` - thresholding and rejection primitives
- `validation.py` - deterministic validation checks
- `execution.py` - deterministic execution interface
- `runtime.py` - orchestration
- `logging.py` - audit serialization
- `artifacts.py` - standard run artifacts

Quickstart:
```bash
# From the KVRM repo root:
pip install -e kvrm-core/ -e kvrm-bench/
python -m pytest tests/kvrm_core -q
```

Toy assets:
- `examples/toy_registry.json`
- `examples/toy_cases.jsonl`

These exist only to validate the foundation, not to serve as a flagship demo.
