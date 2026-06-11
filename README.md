# KVRM — Registry-Constrained Decision Architecture

**Fail-closed finite-action routing for safety-critical domains.**

KVRM is a decision architecture that routes among finite, audited actions under uncertainty. Instead of treating model output as directly executable free-form text, KVRM restricts decision-making to a versioned action registry and places deterministic validation and execution boundaries between prediction and effect.

## Key Properties

| Property | Guarantee |
|---|---|
| **Structural validity** | Every decision output is a valid registered action or an explicit abstention — never a hallucinated action |
| **Fail-closed** | Unsupported inputs are rejected, not guessed at — `false_accept_rate = 0.0` across all 9 domains |
| **Auditable** | Versioned registries with SHA-256 digests, full candidate scores, and validation reasons logged per decision |
| **Domain-agnostic** | One shared 2,296-LOC substrate powers 9 domains across infrastructure, enterprise, and trust-and-safety verticals |

## Architecture

```
Input Features → [Selector Ensemble] → [Support Gate] → [Validator] → [Executor]
                      ↓                      ↓               ↓            ↓
                 6 selectors            reject if         check action   execute or
                 fused via             unsupported         exists in     safe handoff
                 evidence                                 registry
                 calibration
```

**Selector Ensemble** — Six selector types (rule, retrieval, prototype, semantic, learned, hybrid) fused via `EvidenceFusionHybridSelector` with source bonus, agreement bonus, margin bonus, specificity bonus, and calibrated fallback/ambiguity penalties.

**Support Gate** — Boolean expression trees (`all`, `any`, `not` combinators with leaf operators like `eq`, `in`, `gt`, `lte`) that define the valid input envelope for each action. Inputs outside all envelopes are explicitly rejected.

**Validator** — Deterministic check that the selected action exists in the versioned registry and its parameters match the schema. No action executes without passing validation.

**Executor** — Domain-specific execution logic that runs only after validation succeeds.

## Domains

| Domain | Vertical | Actions | Eval Cases | Description |
|---|---|---|---|---|
| **SRE** | Infrastructure | 8 | 140 | Remediation policy routing for incident response |
| **SOC** | Infrastructure | 8 | 126 | Security operations playbook routing |
| **Drone** | Infrastructure | 8 | 146 | Mission-policy routing for autonomous drones |
| **Grid** | Infrastructure | 8 | 24 | Power grid operations routing |
| **Finance** | Enterprise | 8 | 24 | Risk workflow routing |
| **Medical** | Enterprise | 8 | 24 | Clinical workflow routing |
| **IAM** | Enterprise | 7 | 24 | Identity access management routing |
| **Customer Support** | Enterprise | 7 | 48 | Support ticket routing |
| **Content Moderation** | Trust & Safety | 7 | 54 | Content moderation routing |
| **Legal/Compliance** | Enterprise | 7 | 24 | Contract review and compliance routing |
| **CI/CD Pipeline** | Infrastructure | 7 | 24 | Merge, deploy, and rollback decisions |
| **Insurance Claims** | Enterprise | 7 | 24 | Claims processing and fraud escalation |

**Total: 12 domains, 90 actions, 682 eval cases, 596 training cases.**

## Benchmark Results

### Canonical Suite (All 9 Domains)

| Metric | Result |
|---|---|
| Semantic Correctness | **1.0000** (428/428 supported cases correct) |
| False Accept Rate | **0.0000** (0/182 unsupported cases leaked) |
| Unsupported Case Rejection | **1.0000** (182/182 rejected or fallback) |
| Invalid Output Rate | **0.0000** |

### Robustness Families

| Family | Win/Tie/Loss vs Best Non-Hybrid | Description |
|---|---|---|
| Counterfactual Boundary | 2/5/0 | Schema-valid boundary perturbations |
| Temporal Transition | 3/4/0 | Short-horizon state transitions |
| Coordination Chain | 3/4/0 | Multi-step coordination (up to 5-step) |
| Incident Replay | 3/4/0 | Timestamped incident log replay |
| **Total** | **11/17/0** | **Zero losses across all families** |

### Architecture Stress Tests

| Test | Result |
|---|---|
| Support Gate Stress | Gated hybrid: SC=1.0; ungated baseline: SC≈0.11-0.23 |
| Fallback Feasibility | Strict: unsafe_execution=0.0; legacy bypass: 1.0 |
| Adversarial Near-Boundary | Systematic mutation testing across 9 domains |
| Scale (1000+ cases) | Throughput and latency profiling per domain |

## Project Structure

```
KVRM/
├── kvrm-core/           # Shared substrate (2,296 LOC)
│   └── src/kvrm_core/
│       ├── registry.py       # Versioned action registry with SHA-256 digests
│       ├── selectors.py      # 6 selector types + evidence fusion
│       ├── context.py        # Feature key computation
│       ├── context_schema.py # Support spec evaluation
│       ├── learned.py        # Compact selector (RandomForest) training/inference
│       ├── runtime.py        # Decision runtime (selector → validator → executor)
│       └── validation.py     # Deterministic output validation
├── kvrm-bench/          # Benchmark suite
│   └── src/kvrm_bench/
│       ├── demo.py               # Domain discovery and case evaluation
│       ├── metrics.py            # Metric computation (SC, CC, ECE, regret)
│       ├── stress.py             # Support gate stress testing
│       ├── counterfactual.py     # Boundary perturbation benchmarks
│       ├── coordination.py       # Multi-step coordination chains (3+5 step)
│       ├── adversarial_stress.py # Near-boundary adversarial mutations
│       ├── scale_test.py         # Feature-space enumeration at scale
│       ├── interpretability.py   # Feature importance analysis
│       └── publication_*.py      # Publication artifact generation
├── kvrm-demos/          # 9 domain implementations
│   ├── sre-policy-router/
│   ├── soc-playbook-router/
│   ├── drone-mission-router/
│   ├── grid-ops-router/
│   ├── finance-risk-router/
│   ├── medical-workflow-router/
│   ├── iam-access-router/
│   ├── customer-support-router/
│   └── content-moderation-router/
├── kvrm-models/         # 9 trained compact selector models (.joblib)
├── kvrm-compiler/       # Registry compiler tooling
├── kvrm-gpu/            # GPU-accelerated selector inference
├── kvrm-llm-compiler/   # LLM-based registry compilation
├── kvrm-vector/         # Vector similarity selectors
├── tests/               # 228 tests
└── docs/                # Papers, figures, reports, specs
```

## Quick Start

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e kvrm-core/ -e kvrm-bench/

# Run tests
python -m pytest tests/ -q

# Run a single domain evaluation
python -c "
from kvrm_bench.demo import run_demo_case
result = run_demo_case(repo_root='.', domain='sre', eval_filename='cases.jsonl', case_index=0)
print(result['decision'])
"

# Train a compact selector
python -c "
from kvrm_core.learned import train_compact_model, save_compact_model_artifact
from kvrm_core.registry import load_registry
import json
from pathlib import Path

cases = [json.loads(l) for l in open('kvrm-demos/sre-policy-router/data/train_cases.jsonl') if l.strip()]
registry = load_registry('kvrm-demos/sre-policy-router/data/registry.json')
artifact = train_compact_model(train_cases=cases, registry=registry)
save_compact_model_artifact('kvrm-models/sre_compact_selector_v1.joblib', artifact)
print(f'Accuracy: {artifact[\"metadata\"][\"train_accuracy\"]:.4f}')
"

# Regenerate publication bundle
python kvrm-bench/scripts/run_publication_bundle.py
```

## Adding a New Domain

Each domain is a self-contained package under `kvrm-demos/` with:

1. **`data/registry.json`** — Action definitions with support_specs (boolean expression trees defining valid input envelopes)
2. **`data/train_cases.jsonl`** — Training cases with expected actions and feature vectors
3. **`data/cases.jsonl`** — Evaluation cases (supported + unsupported)
4. **`src/{domain}/selectors.py`** — Domain-specific selector builders (rules, prototypes, feature distance functions)
5. **`src/{domain}/executor.py`** — Domain-specific execution logic

Register the domain in `kvrm-bench/src/kvrm_bench/demo.py` by adding an entry to `DOMAIN_CONFIG`.

## Documentation

- **[KVRM Overview](docs/KVRM_OVERVIEW.md)** — What KVRM is, how it works, and when to use it. Start here if you're new.
- **[Pre-Submission Checklist](docs/papers/KVRM_PRE_SUBMISSION_CHECKLIST.md)** — Publication readiness gate.

## Publication

Working title: *Registry-Constrained Decision Architectures for Audited Finite Action Spaces*

See `docs/papers/` for the paper scaffold, evidence matrix, figure source map, and generated appendix. The publication bundle can be regenerated deterministically via `kvrm-bench/scripts/run_publication_bundle.py`.

## License

Internal research artifact. See `docs/` for publication and release plans.
