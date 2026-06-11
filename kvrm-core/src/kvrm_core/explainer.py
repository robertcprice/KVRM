"""Decision explainability layer for KVRM.

Generates human-readable and machine-readable explanations for every routing
decision.  Designed for compliance-heavy domains (medical, finance, content
moderation) where operators must understand *why* a particular action was
chosen.

The explainer is **read-only** -- it never retrains or mutates the decision
pipeline.  It combines:

  1. Per-action feature importances (pre-computed offline) to surface the
     strongest factors behind each routing choice.
  2. The support-spec evaluation to describe which conditions were met/unmet.
  3. Candidate scores from the audit record to describe runner-up actions and
     why they were rejected.
  4. Counterfactual explanations describing what would need to change to reach
     a different action.
  5. Optional SHAP integration for directional feature attribution.
  6. Batch export for bulk analysis (CSV or JSON array).
"""

from __future__ import annotations

import csv
import io
import json
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .support import evaluate_support_spec
from .types import DecisionResult, RegistrySpec


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class FactorContribution:
    """A single feature that contributed to the routing decision."""

    feature: str
    value: Any
    importance: float  # 0-1, from the interpretability report
    rank: int  # 1-based rank among features for this action


@dataclass
class RunnerUpAction:
    """The next-best candidate action considered by the router."""

    action_id: str
    confidence: float
    effective_confidence: float
    rejection_reason: str  # human-readable reason it was not chosen


@dataclass
class SupportStatus:
    """Whether the input fell inside the support boundary of the chosen action."""

    in_support: bool
    conditions_met: list[str]
    conditions_unmet: list[str]


@dataclass
class ShapFactor:
    """A single SHAP-derived directional feature attribution."""

    feature: str
    direction: str  # "pushes_toward", "pushes_away", "neutral"
    mean_abs_shap: float
    mean_shap: float


@dataclass
class FeatureChange:
    """A single feature change required for a counterfactual explanation."""

    feature: str
    current_value: Any
    required_value: Any
    change_type: str  # "value_change", "add_to_set", "remove_from_set"


@dataclass
class CounterfactualExplanation:
    """Describes what would need to change to route to a different action."""

    target_action_id: str
    feature_changes: list[FeatureChange]
    feasibility: str  # "possible" or "impossible"
    human_summary: str


@dataclass
class DecisionExplanation:
    """Full structured explanation of a single routing decision."""

    case_id: str
    selected_action: str
    confidence: float
    final_status: str
    top_factors: list[FactorContribution]
    runner_up: RunnerUpAction | None
    support_status: SupportStatus
    human_summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    input_features: dict[str, Any] = field(default_factory=dict)
    all_candidate_scores: list[dict[str, Any]] = field(default_factory=list)
    shap_factors: list[ShapFactor] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core explainer
# ---------------------------------------------------------------------------

class DecisionExplainer:
    """Generates explanations for KVRM routing decisions.

    Parameters
    ----------
    domain : str
        Domain name (e.g. ``"content_moderation"``).
    registry : RegistrySpec
        The action registry used by the runtime.
    feature_importances : dict | None
        Per-action feature importances.  If *None*, the explainer will attempt
        to load them from *interpretability_report_path*.
    interpretability_report_path : str | Path | None
        Path to the JSON report produced by ``kvrm-bench``'s interpretability
        pipeline.  Only consulted when *feature_importances* is not supplied.
    top_k : int
        Number of top factors to surface in explanations (default 5).
    shap_values : dict | None
        Pre-computed SHAP directional values from the SHAP analysis report.
        Expected structure: ``{"per_action_directions": {"action_id": [...]}}``
        or the full report dict (auto-detected by domain).
    """

    def __init__(
        self,
        *,
        domain: str,
        registry: RegistrySpec,
        feature_importances: dict[str, list[dict[str, Any]]] | None = None,
        interpretability_report_path: str | Path | None = None,
        top_k: int = 5,
        shap_values: dict[str, Any] | None = None,
    ) -> None:
        self.domain = domain
        self.registry = registry
        self.top_k = top_k
        self._actions = {a.action_id: a for a in registry.actions}

        # Resolve feature importances ----------------------------------------
        if feature_importances is not None:
            self._per_action_importances = feature_importances
        elif interpretability_report_path is not None:
            self._per_action_importances = self._load_importances(
                Path(interpretability_report_path), domain,
            )
        else:
            self._per_action_importances = {}

        # Resolve SHAP values ------------------------------------------------
        self._per_action_shap = self._resolve_shap_values(shap_values, domain)

    # -- public API ----------------------------------------------------------

    def explain(
        self,
        decision_result: DecisionResult,
        input_features: dict[str, Any],
    ) -> DecisionExplanation:
        """Produce a structured explanation for a completed decision."""

        audit = decision_result.audit_record
        selected = decision_result.selected_action_id or "(none)"
        confidence = decision_result.confidence if decision_result.confidence is not None else 0.0

        # 1. Top factors
        top_factors = self._top_factors(selected, input_features)

        # 2. Runner-up
        runner_up = self._runner_up(audit.candidate_scores, selected, confidence)

        # 3. Support status
        support_status = self._support_status(selected, input_features)

        # 4. Human summary
        human_summary = self._build_human_summary(
            selected=selected,
            confidence=confidence,
            top_factors=top_factors,
            runner_up=runner_up,
            support_status=support_status,
            decision_result=decision_result,
        )

        # 5. SHAP factors
        shap_factors = self._shap_factors_for_action(selected)

        return DecisionExplanation(
            case_id=decision_result.case_id,
            selected_action=selected,
            confidence=confidence,
            final_status=decision_result.final_status.value,
            top_factors=top_factors,
            runner_up=runner_up,
            support_status=support_status,
            human_summary=human_summary,
            evidence=dict(audit.selected_evidence),
            input_features=dict(input_features),
            all_candidate_scores=list(audit.candidate_scores),
            shap_factors=shap_factors,
        )

    # -- rendering -----------------------------------------------------------

    @staticmethod
    def render_explanation_text(explanation: DecisionExplanation) -> str:
        """Pretty-print a multi-line human-readable explanation."""

        lines: list[str] = []
        lines.append(f"=== Decision Explanation: {explanation.case_id} ===")
        lines.append("")
        lines.append(f"  Action   : {explanation.selected_action}")
        lines.append(f"  Confidence: {explanation.confidence:.4f}")
        lines.append(f"  Status   : {explanation.final_status}")
        lines.append("")

        lines.append("  Top Factors:")
        if explanation.top_factors:
            for f in explanation.top_factors:
                lines.append(
                    f"    #{f.rank} {f.feature} = {f.value!r}  "
                    f"(importance {f.importance:.3f})"
                )
        else:
            lines.append("    (no per-action importances available)")
        lines.append("")

        lines.append("  Support Status:")
        label = "IN-SUPPORT" if explanation.support_status.in_support else "OUT-OF-SUPPORT"
        lines.append(f"    {label}")
        if explanation.support_status.conditions_met:
            lines.append("    Met:")
            for cond in explanation.support_status.conditions_met:
                lines.append(f"      + {cond}")
        if explanation.support_status.conditions_unmet:
            lines.append("    Unmet:")
            for cond in explanation.support_status.conditions_unmet:
                lines.append(f"      - {cond}")
        lines.append("")

        if explanation.runner_up:
            ru = explanation.runner_up
            lines.append("  Runner-Up:")
            lines.append(f"    Action    : {ru.action_id}")
            lines.append(f"    Confidence: {ru.effective_confidence:.4f}")
            lines.append(f"    Rejected  : {ru.rejection_reason}")
        else:
            lines.append("  Runner-Up: (none)")
        lines.append("")

        lines.append("  Summary:")
        wrapped = textwrap.fill(explanation.human_summary, width=78, initial_indent="    ", subsequent_indent="    ")
        lines.append(wrapped)
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def render_explanation_json(explanation: DecisionExplanation) -> dict:
        """Machine-readable explanation suitable for API responses."""

        return {
            "case_id": explanation.case_id,
            "selected_action": explanation.selected_action,
            "confidence": explanation.confidence,
            "final_status": explanation.final_status,
            "top_factors": [
                {
                    "feature": f.feature,
                    "value": f.value,
                    "importance": f.importance,
                    "rank": f.rank,
                }
                for f in explanation.top_factors
            ],
            "runner_up": (
                {
                    "action_id": explanation.runner_up.action_id,
                    "confidence": explanation.runner_up.confidence,
                    "effective_confidence": explanation.runner_up.effective_confidence,
                    "rejection_reason": explanation.runner_up.rejection_reason,
                }
                if explanation.runner_up
                else None
            ),
            "support_status": {
                "in_support": explanation.support_status.in_support,
                "conditions_met": explanation.support_status.conditions_met,
                "conditions_unmet": explanation.support_status.conditions_unmet,
            },
            "human_summary": explanation.human_summary,
            "evidence": explanation.evidence,
            "input_features": explanation.input_features,
        }

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _load_importances(
        report_path: Path, domain: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Load per-action importances from the interpretability report."""

        if not report_path.exists():
            return {}
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        domain_data = payload.get("domains", {}).get(domain)
        if domain_data is None:
            return {}
        return domain_data.get("per_action_importances", {})

    def _top_factors(
        self,
        action_id: str,
        input_features: dict[str, Any],
    ) -> list[FactorContribution]:
        """Return the top-k features driving the chosen action."""

        importances = self._per_action_importances.get(action_id, [])
        factors: list[FactorContribution] = []
        for idx, entry in enumerate(importances[: self.top_k]):
            feat_name = entry["feature"]
            factors.append(
                FactorContribution(
                    feature=feat_name,
                    value=input_features.get(feat_name),
                    importance=entry["importance"],
                    rank=idx + 1,
                )
            )
        return factors

    def _runner_up(
        self,
        candidate_scores: list[dict[str, Any]],
        selected_action_id: str,
        selected_confidence: float,
    ) -> RunnerUpAction | None:
        """Identify the next-best candidate and explain its rejection."""

        others = [
            c for c in candidate_scores
            if c.get("action_id") != selected_action_id
        ]
        if not others:
            return None

        # Pick the runner-up by effective_confidence (or confidence as fallback)
        best_other = max(
            others,
            key=lambda c: c.get("effective_confidence", c.get("confidence", 0.0)),
        )
        other_eff = best_other.get("effective_confidence", best_other.get("confidence", 0.0))
        other_raw = best_other.get("confidence", 0.0)

        # Build rejection reason
        reason_parts: list[str] = []
        gap = selected_confidence - other_eff
        if gap > 0:
            reason_parts.append(f"lower evidence fusion score (gap={gap:.3f})")
        elif gap == 0:
            reason_parts.append("tied confidence but lower selection priority")
        else:
            reason_parts.append("selected action had higher calibrated confidence after fusion")

        support_conf = best_other.get("support_confidence")
        if support_conf is not None and support_conf < 1.0:
            reason_parts.append(f"support_confidence={support_conf:.2f}")

        evidence = best_other.get("evidence", {})
        if evidence.get("support_gate") and evidence["support_gate"] != "passed":
            reason_parts.append(f"support_gate={evidence['support_gate']}")

        rejection_reason = "; ".join(reason_parts) if reason_parts else "lower ranking"

        return RunnerUpAction(
            action_id=best_other["action_id"],
            confidence=other_raw,
            effective_confidence=other_eff,
            rejection_reason=rejection_reason,
        )

    def _support_status(
        self,
        action_id: str,
        input_features: dict[str, Any],
    ) -> SupportStatus:
        """Evaluate support-spec conditions individually."""

        action = self._actions.get(action_id)
        if action is None or not action.support_spec:
            return SupportStatus(in_support=False, conditions_met=[], conditions_unmet=["action not in registry or has no support_spec"])

        spec = action.support_spec
        overall_supported, _ = evaluate_support_spec(spec, input_features)

        met: list[str] = []
        unmet: list[str] = []

        # Walk top-level spec to evaluate individual conditions
        self._walk_spec_conditions(spec, input_features, met, unmet)

        return SupportStatus(
            in_support=overall_supported,
            conditions_met=met,
            conditions_unmet=unmet,
        )

    def _walk_spec_conditions(
        self,
        spec: dict[str, Any],
        features: dict[str, Any],
        met: list[str],
        unmet: list[str],
    ) -> None:
        """Recursively walk a support_spec and populate met/unmet lists."""

        if "feature" in spec:
            feature = spec["feature"]
            op = spec["op"]
            value = spec.get("value")
            actual = features.get(feature)
            ok, _ = evaluate_support_spec(spec, features)
            desc = f"{feature} {op} {value!r} (actual={actual!r})"
            if ok:
                met.append(desc)
            else:
                unmet.append(desc)
            return

        if "all" in spec:
            for child in spec["all"]:
                self._walk_spec_conditions(child, features, met, unmet)
            return

        if "any" in spec:
            # For 'any', check each child independently
            any_met = False
            child_descs: list[tuple[bool, str]] = []
            for child in spec["any"]:
                ok, _ = evaluate_support_spec(child, features)
                if "feature" in child:
                    desc = f"{child['feature']} {child['op']} {child.get('value')!r} (actual={features.get(child['feature'])!r})"
                else:
                    desc = f"(compound condition)"
                child_descs.append((ok, desc))
                if ok:
                    any_met = True
            if any_met:
                for ok, desc in child_descs:
                    if ok:
                        met.append(f"[any-of] {desc}")
            else:
                for _, desc in child_descs:
                    unmet.append(f"[any-of, none matched] {desc}")
            return

        if "not" in spec:
            ok, _ = evaluate_support_spec(spec, features)
            inner = spec["not"]
            if "feature" in inner:
                desc = f"NOT ({inner['feature']} {inner['op']} {inner.get('value')!r})"
            else:
                desc = "NOT (compound condition)"
            if ok:
                met.append(desc)
            else:
                unmet.append(desc)

    def _build_human_summary(
        self,
        *,
        selected: str,
        confidence: float,
        top_factors: list[FactorContribution],
        runner_up: RunnerUpAction | None,
        support_status: SupportStatus,
        decision_result: DecisionResult,
    ) -> str:
        """Compose a single natural-language sentence explaining the decision."""

        parts: list[str] = []

        # Core routing statement
        action_label = selected.replace("_", " ")
        parts.append(f"Routed to {selected}")

        # Factor clause
        if top_factors:
            factor_strs = []
            for f in top_factors[:3]:
                factor_strs.append(f"{f.feature}={f.value!r}")
            strongest = top_factors[0]
            parts.append(
                f"because {strongest.feature}={strongest.value!r} (strongest factor)"
            )
            if len(factor_strs) > 1:
                parts[-1] += ", " + ", ".join(factor_strs[1:])

        # Confidence
        parts.append(f"Confidence: {confidence:.2f}.")

        # Support
        if not support_status.in_support:
            parts.append("Input was OUT-OF-SUPPORT for this action.")

        # Fallback
        if decision_result.fallback_used:
            parts.append("(fallback action)")

        # Runner-up
        if runner_up:
            parts.append(
                f"Alternative considered: {runner_up.action_id} "
                f"({runner_up.effective_confidence:.2f} confidence, "
                f"rejected due to {runner_up.rejection_reason})."
            )

        return " ".join(parts)

    # -- SHAP resolution -----------------------------------------------------

    @staticmethod
    def _resolve_shap_values(
        shap_values: dict[str, Any] | None,
        domain: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Resolve SHAP values into a per-action direction mapping.

        Accepts either:
          - A full SHAP analysis report (with ``domains.<domain>.per_action_directions``).
          - A dict with a top-level ``per_action_directions`` key.
          - ``None`` (returns empty dict).

        Returns a dict mapping action_id -> list of SHAP direction entries.
        """
        if shap_values is None:
            return {}

        # Full report format: {"domains": {"content_moderation": {"per_action_directions": {...}}}}
        if "domains" in shap_values:
            domain_data = shap_values["domains"].get(domain, {})
            return domain_data.get("per_action_directions", {})

        # Direct format: {"per_action_directions": {...}}
        if "per_action_directions" in shap_values:
            return shap_values["per_action_directions"]

        # Assume it IS the per_action_directions dict itself
        return shap_values

    # -- SHAP factor extraction -----------------------------------------------

    def _shap_factors_for_action(self, action_id: str) -> list[ShapFactor]:
        """Return ShapFactor entries for the given action from SHAP data."""
        entries = self._per_action_shap.get(action_id, [])
        return [
            ShapFactor(
                feature=e["feature"],
                direction=e["direction"],
                mean_abs_shap=e["mean_abs_shap"],
                mean_shap=e["mean_shap"],
            )
            for e in entries
        ]

    # -- Counterfactual explanations ------------------------------------------

    def counterfactual(
        self,
        decision_result: DecisionResult,
        input_features: dict[str, Any],
        *,
        target_action_id: str | None = None,
    ) -> list[CounterfactualExplanation]:
        """Compute counterfactual explanations for a decision.

        For each alternative action (or just *target_action_id* if specified),
        identify the minimum set of feature changes that would place the input
        inside that action's support_spec.

        This provides "what would need to change" insights.  The analysis is
        **support-spec based** -- it identifies which support_spec conditions
        the input currently fails for the target action and proposes the
        smallest value changes to satisfy them.

        Parameters
        ----------
        decision_result:
            The completed decision to explain.
        input_features:
            The input feature dict used in the decision.
        target_action_id:
            If specified, only compute the counterfactual for this action.
            Otherwise, compute counterfactuals for all non-selected actions.

        Returns
        -------
        A list of ``CounterfactualExplanation`` objects, one per target action.
        """
        selected = decision_result.selected_action_id or "(none)"
        results: list[CounterfactualExplanation] = []

        target_actions = (
            [a for a in self.registry.actions if a.action_id == target_action_id]
            if target_action_id
            else [a for a in self.registry.actions if a.action_id != selected]
        )

        for action in target_actions:
            if not action.support_spec:
                results.append(CounterfactualExplanation(
                    target_action_id=action.action_id,
                    feature_changes=[],
                    feasibility="impossible",
                    human_summary=f"Action {action.action_id} has no support_spec; cannot compute counterfactual.",
                ))
                continue

            changes = self._compute_feature_changes(
                action.support_spec, input_features,
            )
            feasibility = "possible" if changes is not None else "impossible"
            change_list = changes if changes is not None else []

            if feasibility == "possible" and not change_list:
                summary = (
                    f"Input already satisfies the support_spec for {action.action_id}. "
                    f"The selector's evidence fusion scores (retrieval, rules, prototypes) "
                    f"would need to shift to favour this action."
                )
            elif feasibility == "possible":
                change_strs = []
                for ch in change_list:
                    if ch.change_type == "value_change":
                        change_strs.append(
                            f"change {ch.feature} from {ch.current_value!r} to {ch.required_value!r}"
                        )
                    elif ch.change_type == "add_to_set":
                        change_strs.append(
                            f"set {ch.feature} to one of {ch.required_value!r} (currently {ch.current_value!r})"
                        )
                    elif ch.change_type == "remove_from_set":
                        change_strs.append(
                            f"change {ch.feature} from {ch.current_value!r} (currently matches an excluded value)"
                        )
                summary = (
                    f"To route to {action.action_id}, "
                    + "; ".join(change_strs)
                    + "."
                )
            else:
                summary = (
                    f"Cannot compute a counterfactual for {action.action_id}: "
                    f"the support_spec uses operators that prevent enumeration of required values."
                )

            results.append(CounterfactualExplanation(
                target_action_id=action.action_id,
                feature_changes=change_list,
                feasibility=feasibility,
                human_summary=summary,
            ))

        return results

    def _compute_feature_changes(
        self,
        spec: dict[str, Any],
        features: dict[str, Any],
    ) -> list[FeatureChange] | None:
        """Compute the minimum feature changes to satisfy a support_spec.

        Returns a list of FeatureChange objects, or None if the spec uses
        operators we cannot invert (making counterfactual computation impossible).
        An empty list means the input already satisfies the spec.
        """
        already_ok, _ = evaluate_support_spec(spec, features)
        if already_ok:
            return []

        changes: list[FeatureChange] = []

        if "feature" in spec:
            change = self._leaf_change(spec, features)
            if change is None:
                return None
            changes.append(change)

        elif "all" in spec:
            for child in spec["all"]:
                child_ok, _ = evaluate_support_spec(child, features)
                if not child_ok:
                    child_changes = self._compute_feature_changes(child, features)
                    if child_changes is None:
                        return None
                    changes.extend(child_changes)

        elif "any" in spec:
            # For 'any', find the child that requires the fewest changes
            best_changes: list[FeatureChange] | None = None
            for child in spec["any"]:
                child_ok, _ = evaluate_support_spec(child, features)
                if child_ok:
                    return []  # Already satisfied by this disjunct
                child_changes = self._compute_feature_changes(child, features)
                if child_changes is not None:
                    if best_changes is None or len(child_changes) < len(best_changes):
                        best_changes = child_changes
            if best_changes is None:
                return None
            changes.extend(best_changes)

        elif "not" in spec:
            # Negation is hard to invert generically
            return None

        return changes

    @staticmethod
    def _leaf_change(
        spec: dict[str, Any],
        features: dict[str, Any],
    ) -> FeatureChange | None:
        """Compute a single feature change for a leaf spec node.

        Returns None if the operator is not invertible.
        """
        feat = spec["feature"]
        op = spec["op"]
        val = spec.get("value")
        current = features.get(feat)

        if op == "eq":
            if current != val:
                return FeatureChange(
                    feature=feat,
                    current_value=current,
                    required_value=val,
                    change_type="value_change",
                )
            return None  # Already matches

        if op == "in":
            if current not in val:
                return FeatureChange(
                    feature=feat,
                    current_value=current,
                    required_value=val,
                    change_type="add_to_set",
                )
            return None  # Already in set

        if op == "neq":
            if current == val:
                return FeatureChange(
                    feature=feat,
                    current_value=current,
                    required_value=f"any value != {val!r}",
                    change_type="value_change",
                )
            return None

        if op == "not_in":
            if current in val:
                return FeatureChange(
                    feature=feat,
                    current_value=current,
                    required_value=f"any value not in {val!r}",
                    change_type="remove_from_set",
                )
            return None

        # Unknown operator
        return None

    # -- Batch export ---------------------------------------------------------

    def explain_batch(
        self,
        decisions: list[tuple[DecisionResult, dict[str, Any]]],
        *,
        format: str = "json",
        include_counterfactuals: bool = False,
        include_shap: bool = False,
    ) -> str:
        """Produce explanations for a batch of decisions.

        Parameters
        ----------
        decisions:
            List of (DecisionResult, input_features) tuples.
        format:
            Output format: ``"json"`` for a JSON array of explanation dicts,
            or ``"csv"`` for a CSV string.
        include_counterfactuals:
            If True, compute and include counterfactual explanations for
            each decision (limited to the runner-up action).
        include_shap:
            If True, include SHAP factor data in each explanation.

        Returns
        -------
        A string containing the serialized batch of explanations.
        """
        rows: list[dict[str, Any]] = []

        for decision_result, input_features in decisions:
            explanation = self.explain(decision_result, input_features)
            row = self.render_explanation_json(explanation)

            if include_shap:
                shap_factors = self._shap_factors_for_action(explanation.selected_action)
                row["shap_factors"] = [
                    {
                        "feature": sf.feature,
                        "direction": sf.direction,
                        "mean_abs_shap": sf.mean_abs_shap,
                        "mean_shap": sf.mean_shap,
                    }
                    for sf in shap_factors
                ]

            if include_counterfactuals:
                # Compute counterfactual for runner-up only (keeps output manageable)
                target = (
                    explanation.runner_up.action_id
                    if explanation.runner_up
                    else None
                )
                if target:
                    cfs = self.counterfactual(
                        decision_result, input_features,
                        target_action_id=target,
                    )
                    row["counterfactuals"] = [
                        {
                            "target_action_id": cf.target_action_id,
                            "feature_changes": [
                                {
                                    "feature": fc.feature,
                                    "current_value": fc.current_value,
                                    "required_value": fc.required_value,
                                    "change_type": fc.change_type,
                                }
                                for fc in cf.feature_changes
                            ],
                            "feasibility": cf.feasibility,
                            "human_summary": cf.human_summary,
                        }
                        for cf in cfs
                    ]

            rows.append(row)

        if format == "csv":
            return self._render_batch_csv(rows)
        return json.dumps(rows, indent=2, default=str)

    @staticmethod
    def _render_batch_csv(rows: list[dict[str, Any]]) -> str:
        """Render a list of explanation dicts as a CSV string."""
        if not rows:
            return ""

        flat_keys = [
            "case_id",
            "selected_action",
            "confidence",
            "final_status",
            "human_summary",
            "support_in_support",
            "runner_up_action",
            "runner_up_confidence",
            "runner_up_rejection_reason",
            "top_factor_1",
            "top_factor_1_importance",
            "top_factor_2",
            "top_factor_2_importance",
            "top_factor_3",
            "top_factor_3_importance",
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=flat_keys, extrasaction="ignore")
        writer.writeheader()

        for row in rows:
            flat: dict[str, Any] = {
                "case_id": row.get("case_id", ""),
                "selected_action": row.get("selected_action", ""),
                "confidence": row.get("confidence", ""),
                "final_status": row.get("final_status", ""),
                "human_summary": row.get("human_summary", ""),
                "support_in_support": row.get("support_status", {}).get("in_support", ""),
            }

            runner_up = row.get("runner_up")
            if runner_up:
                flat["runner_up_action"] = runner_up.get("action_id", "")
                flat["runner_up_confidence"] = runner_up.get("effective_confidence", "")
                flat["runner_up_rejection_reason"] = runner_up.get("rejection_reason", "")

            factors = row.get("top_factors", [])
            for i, f in enumerate(factors[:3], start=1):
                flat[f"top_factor_{i}"] = f.get("feature", "")
                flat[f"top_factor_{i}_importance"] = f.get("importance", "")

            writer.writerow(flat)

        return output.getvalue()


# ---------------------------------------------------------------------------
# Module-level convenience helpers
# ---------------------------------------------------------------------------

def render_explanation_text(explanation: DecisionExplanation) -> str:
    """Module-level shortcut for ``DecisionExplainer.render_explanation_text``."""
    return DecisionExplainer.render_explanation_text(explanation)


def render_explanation_json(explanation: DecisionExplanation) -> dict:
    """Module-level shortcut for ``DecisionExplainer.render_explanation_json``."""
    return DecisionExplainer.render_explanation_json(explanation)
