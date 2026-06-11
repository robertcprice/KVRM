# KVRM Core Spec

Purpose: define the canonical Phase 1 KVRM runtime for bounded selection over finite audited action spaces.

## Non-goals
- End-to-end LLM autonomy
- Continuous control
- Formal verification claims
- Domain-specific business logic in the core package

## Canonical runtime order
1. Load and validate registry.
2. Normalize input features into a serializable context.
3. Try exact profile hit if configured.
4. Try retrieval/support-bank match if configured.
5. Run selector if needed.
6. Calibrate candidate confidence.
7. Abstain if confidence is below threshold.
8. Validate chosen action and parameters.
9. On validation failure, fail closed or invoke deterministic fallback.
10. Execute deterministic action or safe handoff.
11. Emit audit log and benchmark artifacts.

## Required abstractions
- Registry
- Context encoder
- Selector
- Calibration layer
- Deterministic validator
- Deterministic executor or safe handoff
- Audit record

## Required failure modes
- abstained
- validation_failed
- fallback_executed
- executed
- fail_closed

## Logging requirements
Every decision must log:
- case_id
- normalized input features
- registry digest
- candidate scores
- selected action
- abstain/fallback reason
- validation outcome
- execution outcome
- latency

## Serialization requirements
All runtime inputs, outputs, and logs must be JSON-serializable.

## Phase 1 exclusions
- heavy model dependencies
- learned runtime selectors beyond compact placeholders
- domain-specific demos beyond a toy benchmark
