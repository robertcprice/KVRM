# KVRM Feature Ceiling Analysis

This report estimates what the current structured feature schema can separate before any selector improvements.

## SOC

- Supported cases: `88`
- Exact-feature oracle accuracy: `1.0000`
- Exact conflicting feature groups: `0`
- Exact conflicting supported cases: `0`
- Registry overlap rate on supported cases: `0.0000`
- Current hybrid semantic correctness: `1.0000`
- Oracle gap (percentage points): `0.00`
- Hybrid matches exact-feature oracle: `true`

Recommended next features:
- `monitoring_only` for domain-wide robustness: The current SOC benchmark is already linearly separable under the existing structured feature schema. Add `asset_isolation_feasibility`, `identity_scope_size`, `service_criticality_override`.

## SRE

- Supported cases: `94`
- Exact-feature oracle accuracy: `1.0000`
- Exact conflicting feature groups: `0`
- Exact conflicting supported cases: `0`
- Registry overlap rate on supported cases: `0.0000`
- Current hybrid semantic correctness: `1.0000`
- Oracle gap (percentage points): `0.00`
- Hybrid matches exact-feature oracle: `true`

Recommended next features:
- `monitoring_only` for domain-wide robustness: The canonical SRE schema now includes locality, failover-policy, deployment-causality, handoff-feasibility, and coordination-state signals, and the current supported pack is separable under the existing audited feature contract. Add `quorum_recovery_eta`, `write_consistency_requirement`, `traffic_shift_capacity_margin`, `incident_command_ready`.
- `medium` for failover_region vs enable_readonly_mode, failover_region vs page_human_operator: The next SRE expansion should target recovery-planning and write-consistency constraints on top of the now-explicit coordination envelope rather than re-adding generic severity features. Add `quorum_recovery_eta`, `write_consistency_requirement`, `control_plane_rate_limit_state`, `incident_command_ready`.

## DRONE

- Supported cases: `98`
- Exact-feature oracle accuracy: `1.0000`
- Exact conflicting feature groups: `0`
- Exact conflicting supported cases: `0`
- Registry overlap rate on supported cases: `0.0000`
- Current hybrid semantic correctness: `1.0000`
- Oracle gap (percentage points): `0.00`
- Hybrid matches exact-feature oracle: `true`

Recommended next features:
- `monitoring_only` for domain-wide robustness: The canonical drone schema now encodes route-energy, landing safety, takeover feasibility, and airspace-governance signals, and the current supported pack is separable under that audited contract. Add `airspace_corridor_stability`, `operator_attention_budget`, `replan_authorization_state`, `diversion_site_commitment`.
- `medium` for switch_to_low_observable_path vs manual_handoff, return_to_home vs manual_handoff: The next drone expansion should target contested-airspace transitions and command-authority constraints on top of the now-explicit path, recovery, and handoff boundaries. Add `airspace_corridor_stability`, `jamming_severity`, `operator_attention_budget`, `replan_authorization_state`.

## GRID

- Supported cases: `18`
- Exact-feature oracle accuracy: `1.0000`
- Exact conflicting feature groups: `0`
- Exact conflicting supported cases: `0`
- Registry overlap rate on supported cases: `0.0000`
- Current hybrid semantic correctness: `1.0000`
- Oracle gap (percentage points): `0.00`
- Hybrid matches exact-feature oracle: `true`

Recommended next features:
- `medium` for dispatch_field_crew vs transfer_load, isolate_faulted_feeder vs transfer_load: The grid registry now cleanly separates audited transfer-vs-dispatch behavior with transfer-path availability, so the next step is richer topology and authorization semantics rather than another generic outage severity field. Add `remote_switching_ready`, `alternate_topology_capacity_margin`, `protective_zone_confidence`, `restoration_sequence_locked`.

## FINANCE

- Supported cases: `18`
- Exact-feature oracle accuracy: `1.0000`
- Exact conflicting feature groups: `0`
- Exact conflicting supported cases: `0`
- Registry overlap rate on supported cases: `0.0000`
- Current hybrid semantic correctness: `1.0000`
- Oracle gap (percentage points): `0.00`
- Hybrid matches exact-feature oracle: `true`

Recommended next features:
- `medium` for enhanced_due_diligence vs manual_review, require_additional_docs vs manual_review: The finance registry now separates bounded due-diligence and documentation workflows from ambiguous human-review cases, so the next gains come from source-of-funds and identity-assurance signals. Add `source_of_funds_confidence`, `beneficial_owner_complexity`, `document_authenticity_confidence`, `merchant_risk_cluster`.

## MEDICAL

- Supported cases: `18`
- Exact-feature oracle accuracy: `1.0000`
- Exact conflicting feature groups: `0`
- Exact conflicting supported cases: `0`
- Registry overlap rate on supported cases: `0.0000`
- Current hybrid semantic correctness: `1.0000`
- Oracle gap (percentage points): `0.00`
- Hybrid matches exact-feature oracle: `true`

Recommended next features:
- `medium` for sepsis_screen_pathway vs respiratory_support_pathway, sepsis_screen_pathway vs escalate_supervisor_review: The medical registry now forces explicit sepsis precedence over generic respiratory or supervisor escalation, so the next frontier is multi-protocol coordination and contraindication handling. Add `protocol_contraindication_flag`, `icu_bed_pressure`, `lactate_trend_bucket`, `antibiotic_delay_risk`.

## IAM

- Supported cases: `18`
- Exact-feature oracle accuracy: `1.0000`
- Exact conflicting feature groups: `0`
- Exact conflicting supported cases: `0`
- Registry overlap rate on supported cases: `0.0000`
- Current hybrid semantic correctness: `1.0000`
- Oracle gap (percentage points): `0.00`
- Hybrid matches exact-feature oracle: `true`

Recommended next features:
- `medium` for require_manager_approval vs require_security_review, grant_break_glass_access vs escalate_identity_admin: The IAM registry now cleanly separates bounded approval, review, break-glass, denial, and manual-admin escalation flows, so the next gains come from stronger identity-assurance and delegated-authority signals rather than another generic risk bucket. Add `identity_assurance_level`, `resource_owner_approval`, `delegated_admin_scope`, `just_in_time_token_health`.

## Interpretation

- If hybrid accuracy already equals the exact-feature oracle, more selector tuning alone will not improve benchmark accuracy.
- In those cases the next gains require feature expansion, registry policy features, or relabeling contradictory examples.
