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

### Canonical Suite (9 Domains, 610 Cases)

| Metric | Result |
|---|---|
| Semantic Correctness | **426/428** supported cases — perfect **1.0000** in 7 of 9 domains; 0.9722 (customer support) and 0.9750 (content moderation) on the two enterprise additions |
| False Accept Rate | **0.0000** (0/182 unsupported cases leaked, all 9 domains) |
| Unsupported Case Rejection | **1.0000** (182/182 rejected or fallback, all 9 domains) |
| Invalid Output Rate | **0.0000** (all 9 domains) |

Regenerate from scratch: `python kvrm-demos/run_demo.py <domain>` for each domain, then `python kvrm-demos/compare_demos.py`.

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

Every directory carries its own `README.md`. The repository is organized in
three tiers: the **flagship artifact** (what the paper is built from and what
ships in the published repo), **supporting tooling**, and **experimental
satellites** (large local-only research threads that are gitignored and are
*not* part of the flagship paper).

```
KVRM/
│   ── Flagship artifact (the published repo / the paper) ──────────────
├── kvrm-core/          # Shared substrate: registry, 6 selectors, support gate, runtime, validator
├── kvrm-bench/         # Benchmark suite + publication pipeline (gate, evidence, paper assets)
├── kvrm-demos/         # 12 domain implementations (registry + cases + domain config each)
├── kvrm-models/        # Trained compact learned-selector artifacts (.joblib), one per domain
├── kvrm-bench-results/ # Committed evidence snapshots cited by the manuscript
├── baselines/          # External small-model baselines (qwen-baseline; finetune/ is gitignored)
├── scripts/            # Entry points (TUI, train, benchmarks) + dataset/maintenance utilities
├── tests/              # Test suite — tests/kvrm_bench is the publication-critical suite (131 tests)
├── docs/               # papers/ (manuscript + LaTeX build), figures, specs, plans, reports
├── archive/            # Superseded/historical material (not imported by anything)
├── memory/             # Dated dev-session notes (context, not code)
│
│   ── Supporting tooling ──────────────────────────────────────────────
├── kvrm-compiler/      # Registry / DSL compiler tooling
├── kvrm-rate-limiter/  # Rate-limiting component
│
│   ── Experimental satellites (GITIGNORED — local-only research threads, ──
│      multi-GB, NOT part of the flagship paper or the published repo) ──
├── kvrm-llm-compiler/  # Earlier neural instruction-decoder thread (~6GB)
├── kvrm-os/            # OS experiment
├── kvrm-gpu/           # GPU-accelerated selector experiments
├── kvrm-vector/        # Vector-similarity selector experiments
└── kvrm-ecosystem/     # Productization sketches
```

## Quick Start

```bash
# Setup — core, bench, and all 12 domain packages
python3 -m venv .venv
source .venv/bin/activate
pip install -e kvrm-core/ -e kvrm-bench/
for d in kvrm-demos/*/; do [ -f "${d}pyproject.toml" ] && pip install -e "$d"; done

# See the architecture in action (supported -> executes, unsupported -> fails closed)
python examples/quickstart.py

# Run tests
python -m pytest tests kvrm-demos -q --ignore=tests/baselines
```

### CLI

Installing `kvrm-bench` gives you the `kvrm` command:

```bash
kvrm domains                          # list all 12 domains with case counts
kvrm actions grid                     # a domain's registered actions + support constraints
kvrm case sre -i 3 --matrix           # route an eval case; compare all selector strategies
kvrm route grid -f '{"outage_scope": "none", ...}'   # route your own features
kvrm case soc --json                  # full decision + audit record as JSON
```

### Library

```bash
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
4. **`{domain}/domain.py`** — A `DomainConfig` (feature schema, rules, executor handlers) passed to `kvrm_core.domain_factory`, which builds all six selectors and the executor — no per-domain selector code needed
5. **`pyproject.toml`** — Makes the domain installable

Register the domain in `kvrm-bench/src/kvrm_bench/demo.py` by adding an entry to `DOMAIN_CONFIG`. Use any existing domain (e.g. `kvrm-demos/grid-ops-router/`) as a template.

## Documentation

- **[KVRM Overview](docs/KVRM_OVERVIEW.md)** — What KVRM is, how it works, and when to use it. Start here if you're new.
- **[examples/quickstart.py](examples/quickstart.py)** — Five-minute walkthrough of the fail-closed pipeline.
- **[Pre-Submission Checklist](docs/papers/KVRM_PRE_SUBMISSION_CHECKLIST.md)** — Publication readiness gate.
- **[AGENTS.md](AGENTS.md)** — Repository governance, testing discipline, and working conventions (read this first if you are an AI agent or a new contributor).

## Publication

Working title: *Registry-Constrained Decision Architectures for Audited Finite Action Spaces*

See `docs/papers/` for the paper scaffold, evidence matrix, figure source map, and generated appendix. The publication bundle can be regenerated deterministically via `kvrm-bench/scripts/run_publication_bundle.py`.

## License

MIT — see [LICENSE](LICENSE).
