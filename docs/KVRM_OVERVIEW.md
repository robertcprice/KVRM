# KVRM Technical Overview

## What KVRM Is

KVRM is a decision architecture for routing among a finite set of audited actions under uncertainty. It is designed for operational settings where the set of things you can do is small, known, and safety-relevant -- incident remediation, security playbooks, clinical workflows, access control decisions -- and where picking the wrong action (or hallucinating a nonexistent one) has real consequences.

The core idea is straightforward: instead of letting a model produce free-form output and hoping it maps to a valid action, KVRM restricts all decisions to a versioned action registry and places deterministic validation between prediction and execution. Every action must exist in the registry, satisfy its declared support constraints against the current input state, and pass runtime validation before anything executes.

KVRM is not a model. It is a runtime that can contain models (classifiers, retrievers, learned selectors) as components, but wraps them in an architecture that enforces structural safety properties no individual model can guarantee on its own.

## The Problem

Consider a common pattern: an alert fires, you feed context into a model, and the model picks a remediation action. This works until it does not. The failure modes are predictable:

**Hallucinated actions.** The model outputs "restart_primary_db" but no such action exists in your runbook. You now need a separate system to catch this, or you execute something undefined.

**Unsupported actions.** The model picks "failover_region" -- a real action -- but the secondary region has no capacity. The action is valid in general but dangerous right now. A classifier has no mechanism to check this; it picks the most likely label regardless of whether the preconditions hold.

**Forced predictions.** A classifier must always output a label. When the input does not match any safe action (corrupted telemetry, unknown fault type, ambiguous signals), the system forces a choice anyway instead of abstaining. In safety-critical domains, forcing a guess is worse than doing nothing.

**Silent drift.** You update your runbook -- deprecate an action, add a new one, tighten a constraint. Your model does not know. It continues to route to the old action space because nothing ties its output to the live registry.

**No audit trail.** After an incident, you need to explain why the system chose action X. A classifier gives you a confidence score. KVRM gives you the full chain: which selectors fired, what evidence each produced, which candidates were eliminated by support checks, what the validator found, and what the executor did.

These are not edge cases. They are the default failure mode of treating action selection as a classification problem.

## How It Works

KVRM processes every decision through four layers, in strict sequence. No layer can be skipped.

```
Input Features --> [Selector Ensemble] --> [Support Gate] --> [Validator] --> [Executor]
```

### Layer 1: Selector Ensemble

Multiple independent selectors evaluate the input features and produce scored candidate actions. KVRM ships six selector types:

- **Rule selectors** -- Exact feature-key lookups in a static rule table. Fast, auditable, brittle to unseen combinations.
- **Retrieval selectors** -- Match the input against a bank of known-good feature vectors. Good for covering trained cases.
- **Semantic selectors** -- Evaluate which actions' support specs match the input, scoring by specificity (leaf count in the support expression tree).
- **Prototype selectors** -- Distance-based matching against representative examples per action.
- **Learned selectors** -- Compact models (RandomForest) trained on labeled cases. Fill gaps that rules and retrieval miss.
- **Hybrid selectors** -- Combine multiple selector types and fuse their evidence.

No single selector type is sufficient. Rules miss novel combinations. Retrieval only covers known cases. Learned models can overfit. The ensemble provides redundancy: when multiple independent selectors agree on an action, the fused confidence increases. When they disagree, ambiguity penalties reduce confidence, making abstention more likely.

The fusion logic (implemented in `EvidenceFusionCalibrator`) groups candidates by action ID, applies source bonuses for multi-selector agreement, margin bonuses for clear winners, specificity bonuses for well-constrained support specs, and ambiguity penalties when the top two candidates are too close.

### Layer 2: Support Gate

This is the architectural boundary that distinguishes "high confidence" from "actually executable."

Every action in the registry declares a **support spec** -- a boolean expression tree over input features that defines when the action is valid. For example, the SRE `failover_region` action requires `dependency_health=failing AND region_health=failing AND failover_ready=true AND automation_policy_permits_failover=true AND ...` (16 conditions total).

The support gate evaluates each candidate's support spec against the current input features. Candidates that fail their support spec are eliminated *before* they compete in fused scoring. This prevents a pathological case: a candidate with high similarity or model confidence dominating the final ranking despite being unsafe to execute in the current state.

If no candidate survives the support gate, the system does not force a choice. It falls back to a safe default (typically `request_human_review`) or fails closed entirely.

### Layer 3: Validator

Selection is not execution. After the calibrator picks a winner, the `DeterministicValidator` checks it against the live registry:

1. **Action exists** -- The selected action ID must be present in the current registry version. If the registry was updated and this action was removed, validation fails.
2. **Parameters match schema** -- Required parameters must be present; unexpected parameters are rejected.
3. **Support spec holds** -- The action's support constraints are re-evaluated against the input features at validation time (not just at selection time).
4. **Preconditions pass** -- Domain-specific precondition functions, if registered, must return true.

This double-check (support gate at selection, support spec at validation) is intentional. The support gate filters candidates during scoring. The validator re-checks the *winner* before execution. This catches edge cases where fusion or calibration logic might promote a candidate that technically passed the gate but whose support status changed or was borderline.

Even fallback actions are validated. If `request_human_review` has its own support spec, it must satisfy that spec too. If it cannot, the system fails closed -- `FinalStatus.FAIL_CLOSED` -- rather than executing an unsupported fallback.

### Layer 4: Executor

Only after validation succeeds does the executor run. Execution is domain-specific: in the SRE domain it might trigger a runbook, in the SOC domain it might activate a playbook, in the medical domain it might initiate a workflow. The executor receives only validated candidates and produces a structured `ExecutionResult` with status (`success`, `handoff`, `blocked`, `failed`), output payload, and reason.

Fallback-tagged actions that pass validation receive `ExecutionStatus.HANDOFF`, making it explicit in the audit trail that this was an escalation, not a primary action.

## Key Concepts

**Registry** -- A versioned JSON document that defines all valid actions for a domain, their support constraints, parameter schemas, and tags. The registry is SHA-256 digested so every decision records exactly which registry version was used.

**Action** -- A single entry in the registry. Has an `action_id`, human-readable name, description, parameter schema, support spec, and tags. Example: `restart_service`, `failover_region`, `page_human_operator`.

**Support Spec** -- A boolean expression tree (`all`, `any`, `not` combinators over leaf conditions like `{feature: "latency", op: "in", value: ["high", "severe"]}`) that defines the valid input envelope for an action. The action should only execute when its support spec evaluates to true against the current features.

**Selector** -- A component that takes input features and produces scored `DecisionCandidate` objects. Selectors propose; they do not decide.

**Calibrator** -- The `EvidenceFusionCalibrator` that fuses candidates across selectors, applies bonuses and penalties, and picks a winner (or abstains). Implements source agreement, margin, specificity, and ambiguity signals.

**Fallback** -- A safe default action (typically `request_human_review`) used when no primary action is supported or when the primary action fails validation. Fallback actions are tagged `"fallback"` in the registry and can have their own support specs.

**Fail-Closed** -- The terminal state when *no* action -- including the fallback -- passes validation. The system blocks execution entirely rather than guessing. This is the `FinalStatus.FAIL_CLOSED` state.

## What Makes It Different

Three properties distinguish KVRM from a plain classifier or an LLM-based router:

### Structural Validity

Every decision output is either a valid registered action or an explicit abstention. The system cannot hallucinate actions, produce malformed outputs, or select actions that have been removed from the registry. This is enforced architecturally (the validator checks the live registry), not statistically (hoping the model gets it right).

Across the canonical benchmark suite (610 cases, 9 domains), KVRM achieves `invalid_output_rate=0.0`. When tested against real small language models (Qwen3 0.6B/1.7B, Gemma4 e2b) running as external selectors under structured output, those models produce `false_accept_rate=0.9964` and Qwen3 1.7B collapses with `invalid_output_rate=1.0`.

### Fail-Closure

Unsupported inputs are rejected, not forced into the nearest label. This matters in safety-critical domains where doing nothing is safer than doing the wrong thing. KVRM achieves `false_accept_rate=0.0` and `unsupported_case_rejection_rate=1.0` across all 9 domains on the canonical packs.

Under support-gate stress testing (high-confidence but support-incompatible candidates injected upstream), gated KVRM preserves `semantic_correctness_rate=1.0` while an ungated baseline drops to 0.11-0.23. The gate is architecturally necessary.

### Auditability

Every decision produces an `AuditRecord` containing: the registry digest, input features, all candidate scores from all selectors, the selected action and its confidence, evidence signals (agreement, margin, source families, support leaf count), whether fallback was used, the validation reason, execution status, final status, and latency. This is a complete decision trace, not just a score.

## Example Walkthrough

An SRE monitoring system detects a service degradation and produces the following feature vector:

```
latency:              "elevated"
error_rate:           "high"
dependency_health:    "degraded"
fault_scope:          "service"
deploy_regression_suspected: false
node_locality_score:  0.2
recent_restart_attempts: 0
replica_skew:         0.52
saturation:           "high"
write_path_available: true
rollback_safe:        false
telemetry_confidence: "high"
... (26 features total)
```

Here is what happens, step by step:

**1. Selector Ensemble.** The rule selector looks up the feature key and finds a match for `restart_service` at confidence 0.92. The retrieval selector matches a similar case from the training bank, also pointing to `restart_service` at 0.88. The semantic selector evaluates all 8 actions' support specs against the features: `restart_service` matches all 9 leaf conditions in its support spec and scores 0.85; `rollback_deploy` fails because `deploy_regression_suspected=false`; `failover_region` fails because `region_health` is not `"failing"`. The learned selector (RandomForest) predicts `restart_service` with probability 0.91.

**2. Support Gate.** Each candidate's support spec is checked. `restart_service` passes: `dependency_health=degraded` (required), `fault_scope=service` (required), `node_locality_score=0.2 <= 0.35` (required), `recent_restart_attempts=0 <= 1.0` (required), etc. All 9 conditions hold. No other primary action's full support spec is satisfied. `page_human_operator` (the fallback) is also evaluated but its support spec requires `dependency_health=failing`, which does not match.

**3. Evidence Fusion.** The calibrator groups all candidates by action ID. `restart_service` has candidates from 4 sources. It receives a source bonus (+0.09 for 4 independent families), an agreement bonus (agreement > 0.5), and a margin bonus (clear gap over the runner-up). Fused confidence: ~0.96. No ambiguity penalty because the runner-up is well below the ambiguity window.

**4. Validation.** The `DeterministicValidator` checks: `restart_service` exists in registry v1.5.0, no required parameters, support spec re-evaluated and passes. Validation result: `valid=true`.

**5. Execution.** The SRE executor runs the `restart_service` action. `ExecutionResult(status=SUCCESS, action_id="restart_service")`.

**6. Audit Record.** The system logs the full `AuditRecord`: registry digest, all 4 candidate scores, fused evidence, validation outcome, execution status, `FinalStatus.EXECUTED`, and latency.

Now consider a different input where `dependency_health="unknown"` and `fault_scope="unknown"` -- values outside any action's support spec. Every candidate fails the support gate. The system falls back to `request_human_review`, which also fails validation (its support spec is not satisfied). Final status: `FinalStatus.FAIL_CLOSED`. No action executes. The system pages a human with full context.

## Domains

KVRM currently supports 9 domains across three verticals:

| Domain | Vertical | Actions | What It Routes |
|---|---|---|---|
| SRE Policy | Infrastructure | 8 | Incident remediation: restart, failover, scale, drain, rollback, read-only mode, gather telemetry, page human |
| SOC Playbook | Infrastructure | 8 | Security operations: isolate host, block IP, revoke credentials, escalate threat, scan, contain, investigate, review |
| Drone Mission | Infrastructure | 8 | Autonomous drone policy: continue mission, return to base, emergency land, hold position, reroute, abort, transfer control, shelter |
| Grid Ops | Infrastructure | 8 | Power grid operations: load shed, reroute power, dispatch crew, isolate fault, activate reserve, curtail generation, shed non-critical, escalate |
| Finance Risk | Enterprise | 8 | Financial risk workflows: approve, flag for review, block, escalate, request documentation, apply enhanced due diligence, freeze, report |
| Medical Workflow | Enterprise | 8 | Clinical workflows: standard care, urgent referral, emergency protocol, watchful waiting, specialist consult, diagnostic workup, palliative, triage |
| IAM Access | Enterprise | 7 | Identity and access: grant, deny, require MFA step-up, temporary elevation, revoke, audit review, conditional grant |
| Customer Support | Enterprise | 7 | Support ticket routing: auto-resolve, tier-1, tier-2, engineering escalation, billing, account recovery, manager review |
| Content Moderation | Trust and Safety | 7 | Content decisions: approve, flag, remove, restrict, age-gate, appeal review, escalate to policy |

All 9 domains share the same 2,296-LOC core substrate. Each domain provides its own registry, training cases, evaluation cases (supported and unsupported), selectors, and executor.

## When to Use KVRM

### Good Fit

- **Finite action spaces.** Your system chooses among a known, enumerable set of actions (runbooks, playbooks, workflows, escalation paths). Typically under 20 actions per domain.
- **Safety-critical decisions.** Executing the wrong action has real consequences: data loss, security exposure, patient harm, financial loss. You need fail-closed behavior, not best-guess behavior.
- **Audit requirements.** Regulatory or operational requirements demand a complete, deterministic trace from input to decision to execution. You need to explain every decision after the fact.
- **Registry governance.** Your action space evolves (new runbooks, deprecated workflows, tightened constraints) and you need decisions to track the live registry, not a stale model.
- **Unsupported inputs are normal.** Your system regularly encounters states where no action is safe, and "do nothing / escalate" is the correct response. A system that must always pick a label is dangerous here.

### Bad Fit

- **Open-ended generation.** If your system needs to compose free-form responses (chat, content creation, code generation), KVRM does not apply. It routes among finite actions; it does not generate text.
- **High-cardinality action spaces.** If you have thousands of possible actions, the registry-and-support-spec pattern becomes unwieldy. KVRM is designed for tens of actions per domain, not thousands.
- **Pure classification without safety constraints.** If misclassification has low cost and you do not need fail-closed behavior or audit trails, a plain classifier is simpler and sufficient.
- **Real-time latency under 1ms.** KVRM's multi-selector fusion and validation adds overhead. For sub-millisecond decisions, a single model inference is more appropriate.
