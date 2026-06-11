# KVRM — Registry-Constrained Decision Architecture

KVRM is a decision architecture for systems where a model's output triggers a
real action: an incident runbook, a drone maneuver, an account suspension. In
those settings the usual machine-learning question — *which label is most
likely?* — is the wrong question. The right one is: *which registered action,
if any, is both supported by the current input and still valid to execute?*
KVRM is built around that question.

Instead of treating model output as directly executable, KVRM restricts every
decision to a versioned action registry and places deterministic checks between
prediction and effect. The result is a router that can say "none of the above"
and mean it:

- Every output is either a registered action or an explicit abstention. The
  system cannot emit an action that does not exist.
- Inputs that fall outside every action's declared support envelope are
  rejected, not coerced into the nearest label. On the benchmark suite the
  false-accept rate is 0.0 in all nine benchmarked domains.
- Every decision is logged with its candidate scores, support-spec evaluation,
  validation outcome, and the SHA-256 digest of the registry version it ran
  against, so any decision can be audited after the fact.
- One shared substrate (about 2,300 lines of Python) runs all twelve domains.
  A new domain is a directory of data plus one config file, not a fork of the
  codebase.

This matters because a classifier always answers, even when it shouldn't. KVRM
treats unsupported inputs as normal — the open-world case, not an error — and
routes them to rejection or a safe handoff instead of a guess.

## How it works

```
Input Features → [Selector Ensemble] → [Support Gate] → [Validator] → [Executor]
                      ↓                      ↓               ↓            ↓
                 6 selectors            reject if         check action   execute or
                 fused via             unsupported         exists in     safe handoff
                 evidence                                 registry
                 calibration
```

1. **Selector ensemble.** Six selector types (rule, retrieval, prototype,
   semantic, learned, hybrid) score candidate actions. The hybrid selector
   fuses their evidence with calibrated bonuses for source agreement, margin,
   and specificity, and penalties for ambiguity.
2. **Support gate.** Each action declares the input envelope it is valid for,
   as a boolean expression tree (`all`/`any`/`not` over leaf tests like `eq`,
   `in`, `gt`, `lte`). Candidates whose envelope the input does not satisfy are
   filtered *before* calibration. Inputs that satisfy no envelope are rejected
   outright.
3. **Validator.** A deterministic check that the selected action exists in the
   live registry version and its parameters match the schema. Nothing executes
   without passing it — including fallback actions.
4. **Executor.** Domain-specific execution logic, reached only after
   validation succeeds.

The ordering is the point. Removing the support gate collapses correctness
under confident-but-invalid upstream evidence; removing strict validation
guarantees unsafe execution on infeasible handoffs. Both ablations are
measured below.

## Domains

Twelve domains are implemented. Nine form the canonical benchmark suite; the
last three (legal/compliance, CI/CD, insurance) have registries and cases but
are not yet wired into the suite.

| Domain | Vertical | Actions | Eval cases |
|---|---|---|---|
| SRE remediation | Infrastructure | 8 | 140 |
| SOC playbooks | Infrastructure | 8 | 126 |
| Drone missions | Infrastructure | 8 | 146 |
| Grid operations | Infrastructure | 8 | 24 |
| Finance risk | Enterprise | 8 | 24 |
| Medical workflow | Enterprise | 8 | 24 |
| IAM access | Enterprise | 7 | 24 |
| Customer support | Enterprise | 7 | 48 |
| Content moderation | Trust & safety | 7 | 54 |
| Legal/compliance* | Enterprise | 7 | 24 |
| CI/CD pipeline* | Infrastructure | 7 | 24 |
| Insurance claims* | Enterprise | 7 | 24 |

\* implemented, not yet in the canonical suite.

Total: 12 domains, 90 actions, 682 eval cases, 596 training cases.

## Results

All numbers below regenerate from the repo (`python kvrm-demos/run_demo.py
<domain>`, then `python kvrm-demos/compare_demos.py`); the publication bundle
pins them to committed artifacts.

**Canonical suite** (9 domains, 610 cases — 428 supported, 182 unsupported):

| Metric | Result |
|---|---|
| Semantic correctness | 426/428 supported cases. 1.0 in seven domains; 0.9722 (customer support) and 0.9750 (content moderation) in the two newest |
| False accepts | 0/182 unsupported cases executed, all nine domains |
| Unsupported-case rejection | 182/182 rejected or routed to safe fallback |
| Invalid outputs | 0, all nine domains |

**Robustness families**, hybrid KVRM vs. the best non-hybrid baseline:

| Family | Win / tie / loss | What it tests |
|---|---|---|
| Counterfactual boundary | 2 / 5 / 0 | Schema-valid perturbations at decision boundaries |
| Temporal transition | 3 / 4 / 0 | Short-horizon state transitions |
| Coordination chain | 3 / 4 / 0 | Multi-step coordination, up to 5 steps |
| Incident replay | 3 / 4 / 0 | Timestamped incident-log replay |
| Total | 11 / 17 / 0 | No losses in any family |

**Ablations** (why the architecture is shaped this way):

| Removed component | Consequence |
|---|---|
| Support gate | Semantic correctness drops from 1.0 to roughly 0.11–0.23 under injected high-confidence invalid evidence |
| Strict fallback validation | Unsafe-execution rate goes from 0.0 to 1.0 on explicit infeasible-handoff probes |

External baselines: small instruction-tuned models (Qwen3 0.6b/1.7b, Qwen3.5
0.8b, Gemma4 e2b) evaluated under a strict structured-output protocol reach at
best 0.74 semantic correctness with a 0.996 false-accept rate. They route
supported cases tolerably and execute unsupported ones almost every time —
which is the failure mode KVRM exists to close.

## Quick start

```bash
# Setup — core, bench, and the bundled domain packages
python3 -m venv .venv
source .venv/bin/activate
pip install -e kvrm-core/ -e kvrm-bench/
for d in kvrm-demos/*/; do [ -f "${d}pyproject.toml" ] && pip install -e "$d"; done

# Watch the pipeline run: supported input executes, unsupported fails closed
python examples/quickstart.py

# Run the test suite
python -m pytest tests kvrm-demos -q --ignore=tests/baselines
```

### CLI — bring your own domain

Installing `kvrm-core` provides the `kvrm` command. A domain is a plain
directory of data (registry plus cases, no Python required), so you can route
your own action space in minutes:

```bash
kvrm init my-domain                   # scaffold a small working example
kvrm validate my-domain               # check registry, support specs, case schemas
kvrm train my-domain                  # train the compact learned selector
kvrm route my-domain -f '{"risk_level": "low", "amount": 250, "account_verified": true}'
kvrm explain my-domain -f '{...}'     # decision plus support-spec reasoning
kvrm eval my-domain                   # fail-closed metrics over cases.jsonl
```

The bundled research domains are available behind `kvrm demo` (requires a repo
checkout with the demo packages installed):

```bash
kvrm demo domains                     # list all 12 domains with case counts
kvrm demo actions grid                # registered actions + support constraints
kvrm demo case sre -i 3 --matrix      # route one eval case; compare all strategies
kvrm demo route grid -f '{"outage_scope": "none", ...}'
```

### Library

```bash
# Evaluate a single case
python -c "
from kvrm_bench.demo import run_demo_case
result = run_demo_case(repo_root='.', domain='sre', eval_filename='cases.jsonl', case_index=0)
print(result['decision'])
"

# Regenerate the publication bundle
python kvrm-bench/scripts/run_publication_bundle.py
```

## Adding a domain

Each domain under `kvrm-demos/` is a self-contained package:

1. `data/registry.json` — action definitions, each with a `support_spec`
   boolean expression tree defining its valid input envelope
2. `data/train_cases.jsonl` — training cases (features plus expected action)
3. `data/cases.jsonl` — evaluation cases, supported and unsupported
4. `{domain}/domain.py` — a `DomainConfig` (feature schema, rules, executor
   handlers) passed to `kvrm_core.domain_factory`, which builds all six
   selectors and the executor; no per-domain selector code
5. `pyproject.toml` — makes the domain installable

Register it in `kvrm-bench/src/kvrm_bench/demo.py` (`DOMAIN_CONFIG`). Any
existing domain, e.g. `kvrm-demos/grid-ops-router/`, works as a template.

## Repository layout

Every directory has its own `README.md`. Three tiers: the published artifact,
supporting tooling, and large experimental satellites that are local-only
(gitignored) and not part of the paper.

```
KVRM/
│   ── Published artifact ──────────────────────────────────────────────
├── kvrm-core/          # The library: registry, selectors, support gate, runtime, validator
├── kvrm-bench/         # Benchmark suite + publication pipeline
├── kvrm-demos/         # 12 domain implementations (registry + cases + domain config)
├── kvrm-models/        # Trained learned-selector artifacts (.joblib), one per domain
├── kvrm-bench-results/ # Committed evidence snapshots cited by the manuscript
├── baselines/          # External small-model baselines (finetune/ is gitignored)
├── scripts/            # Entry points (TUI, training, benchmarks) and maintenance utilities
├── tests/              # Test suite; tests/kvrm_bench is the publication-critical part
├── docs/               # papers/ (manuscript + LaTeX build), figures, specs, reports
├── examples/           # quickstart.py walkthrough
├── archive/            # Superseded material, kept for provenance
├── memory/             # Dated development-session notes
│
│   ── Supporting tooling ──────────────────────────────────────────────
├── kvrm-compiler/      # Registry / DSL compiler tooling
├── kvrm-rate-limiter/  # Rate-limiting component
│
│   ── Experimental satellites (gitignored, local-only, not in the paper) ──
├── kvrm-llm-compiler/  # Earlier neural instruction-decoder research thread
├── kvrm-os/            # OS experiment
├── kvrm-gpu/           # GPU-accelerated selector experiments
├── kvrm-vector/        # Vector-similarity selector experiments
└── kvrm-ecosystem/     # Productization sketches
```

## Documentation

- [KVRM Overview](docs/KVRM_OVERVIEW.md) — what KVRM is, how it works, when to
  use it. Start here.
- [examples/quickstart.py](examples/quickstart.py) — five-minute walkthrough of
  the fail-closed pipeline.
- [AGENTS.md](AGENTS.md) — repository governance, testing discipline, working
  conventions. Read first if you are contributing (human or agent).
- [Pre-submission checklist](docs/papers/KVRM_PRE_SUBMISSION_CHECKLIST.md) —
  the publication readiness gate.

## Paper

*Registry-Constrained Decision Architectures for Audited Finite Action Spaces*
(working title). The manuscript source is
`docs/papers/KVRM_FLAGSHIP_PAPER_DRAFT.md`; `docs/papers/latex/build_paper.py`
renders the PDF. Every benchmark number in the paper traces to a committed
artifact via the evidence matrix, and
`kvrm-bench/scripts/run_publication_check.py` verifies the whole bundle
deterministically.

## License

MIT — see [LICENSE](LICENSE).
