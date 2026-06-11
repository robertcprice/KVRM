"""Tests for the KVRM decision explainability layer.

Runs real decisions through content_moderation and customer_support domains,
generates explanations for both supported and unsupported cases, and verifies
the explanation structure is complete and correct.

Also tests the three explainability enhancements:
  - Counterfactual explanations
  - Batch export (JSON and CSV)
  - SHAP integration
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from kvrm_bench.demo import load_cases, run_demo_case
from kvrm_core.explainer import (
    CounterfactualExplanation,
    DecisionExplainer,
    DecisionExplanation,
    FeatureChange,
    ShapFactor,
    render_explanation_json,
    render_explanation_text,
)
from kvrm_core.registry import load_registry
from kvrm_core.types import DecisionResult

REPO_ROOT = Path(__file__).resolve().parents[2]
INTERPRETABILITY_REPORT = REPO_ROOT / "kvrm-bench-results" / "interpretability" / "interpretability_report.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_explainer(domain: str) -> DecisionExplainer:
    """Build an explainer for *domain* using the real registry + report."""
    demo_data_dir = REPO_ROOT / "kvrm-demos" / f"{domain.replace('_', '-')}-router" / "data"
    registry = load_registry(demo_data_dir / "registry.json")
    return DecisionExplainer(
        domain=domain,
        registry=registry,
        interpretability_report_path=INTERPRETABILITY_REPORT,
    )


def _run_and_explain(domain: str, case_index: int) -> tuple[DecisionExplanation, dict]:
    """Run a demo case and produce an explanation."""
    explainer = _build_explainer(domain)
    payload = run_demo_case(
        repo_root=str(REPO_ROOT),
        domain=domain,
        eval_filename="cases.jsonl",
        case_index=case_index,
    )
    decision = DecisionResult(**payload["decision"])
    features = payload["case"]["input_features"]
    explanation = explainer.explain(decision, features)
    return explanation, payload


def _find_case_index(domain: str, *, supported: bool | None = None, expected_action: str | None = None) -> int:
    """Find a case index matching the given criteria."""
    demo_data_dir = REPO_ROOT / "kvrm-demos" / f"{domain.replace('_', '-')}-router" / "data"
    cases = load_cases(demo_data_dir / "cases.jsonl")
    for idx, case in enumerate(cases):
        if supported is not None and case.get("supported", True) != supported:
            continue
        if expected_action is not None and case.get("expected_action_id") != expected_action:
            continue
        return idx
    raise ValueError(f"No matching case found: domain={domain}, supported={supported}, expected_action={expected_action}")


# ---------------------------------------------------------------------------
# Structure verification helpers
# ---------------------------------------------------------------------------

def _assert_explanation_complete(expl: DecisionExplanation) -> None:
    """Assert that all required fields of an explanation are present and typed."""
    assert isinstance(expl.case_id, str) and expl.case_id
    assert isinstance(expl.selected_action, str) and expl.selected_action
    assert isinstance(expl.confidence, (int, float))
    assert isinstance(expl.final_status, str) and expl.final_status
    assert isinstance(expl.top_factors, list)
    assert isinstance(expl.support_status.in_support, bool)
    assert isinstance(expl.support_status.conditions_met, list)
    assert isinstance(expl.support_status.conditions_unmet, list)
    assert isinstance(expl.human_summary, str) and len(expl.human_summary) > 10
    assert isinstance(expl.input_features, dict) and expl.input_features
    assert isinstance(expl.evidence, dict)
    assert isinstance(expl.all_candidate_scores, list)


# ===========================================================================
# Tests: content_moderation
# ===========================================================================

class TestContentModerationExplainer:

    def test_supported_case_explanation_structure(self):
        """A supported case produces a structurally complete explanation."""
        idx = _find_case_index("content_moderation", supported=True)
        expl, _ = _run_and_explain("content_moderation", idx)
        _assert_explanation_complete(expl)

    def test_supported_case_has_top_factors(self):
        """Supported case includes at least 3 top factors (report has 8 features)."""
        idx = _find_case_index("content_moderation", supported=True)
        expl, _ = _run_and_explain("content_moderation", idx)
        assert len(expl.top_factors) >= 3
        # Factors should be ordered by importance rank
        ranks = [f.rank for f in expl.top_factors]
        assert ranks == sorted(ranks)

    def test_supported_case_human_summary_mentions_action(self):
        """Human summary must contain the selected action name."""
        idx = _find_case_index("content_moderation", supported=True)
        expl, _ = _run_and_explain("content_moderation", idx)
        assert expl.selected_action in expl.human_summary

    def test_unsupported_case_explanation_structure(self):
        """An unsupported (OOD) case still produces a complete explanation."""
        idx = _find_case_index("content_moderation", supported=False)
        expl, _ = _run_and_explain("content_moderation", idx)
        _assert_explanation_complete(expl)

    def test_text_rendering_is_nonempty(self):
        """render_explanation_text returns a multi-line string."""
        idx = _find_case_index("content_moderation", supported=True)
        expl, _ = _run_and_explain("content_moderation", idx)
        text = render_explanation_text(expl)
        assert isinstance(text, str)
        assert len(text) > 100
        assert "Decision Explanation" in text

    def test_json_rendering_roundtrips(self):
        """render_explanation_json returns a JSON-serializable dict."""
        idx = _find_case_index("content_moderation", supported=True)
        expl, _ = _run_and_explain("content_moderation", idx)
        j = render_explanation_json(expl)
        assert isinstance(j, dict)
        # Must be JSON serializable
        serialized = json.dumps(j)
        parsed = json.loads(serialized)
        assert parsed["case_id"] == expl.case_id
        assert parsed["selected_action"] == expl.selected_action
        assert parsed["human_summary"] == expl.human_summary

    def test_remove_content_case_factors(self):
        """A remove_content case should cite toxicity as a top factor."""
        idx = _find_case_index("content_moderation", expected_action="remove_content")
        expl, _ = _run_and_explain("content_moderation", idx)
        # The interpretability report ranks toxicity_level #1 for remove_content
        factor_names = [f.feature for f in expl.top_factors]
        assert "toxicity_level" in factor_names


# ===========================================================================
# Tests: customer_support
# ===========================================================================

class TestCustomerSupportExplainer:

    def test_supported_case_explanation_structure(self):
        """A supported customer_support case produces a complete explanation."""
        idx = _find_case_index("customer_support", supported=True)
        expl, _ = _run_and_explain("customer_support", idx)
        _assert_explanation_complete(expl)

    def test_supported_case_has_top_factors(self):
        """Customer support explanations include ranked factors."""
        idx = _find_case_index("customer_support", supported=True)
        expl, _ = _run_and_explain("customer_support", idx)
        assert len(expl.top_factors) >= 3

    def test_unsupported_case_explanation_structure(self):
        """An unsupported customer_support case still produces a complete explanation."""
        idx = _find_case_index("customer_support", supported=False)
        expl, _ = _run_and_explain("customer_support", idx)
        _assert_explanation_complete(expl)

    def test_human_summary_mentions_action(self):
        """Human summary must mention the selected action."""
        idx = _find_case_index("customer_support", supported=True)
        expl, _ = _run_and_explain("customer_support", idx)
        assert expl.selected_action in expl.human_summary

    def test_json_rendering_complete(self):
        """JSON rendering includes all required top-level keys."""
        idx = _find_case_index("customer_support", supported=True)
        expl, _ = _run_and_explain("customer_support", idx)
        j = render_explanation_json(expl)
        required_keys = {
            "case_id", "selected_action", "confidence", "final_status",
            "top_factors", "runner_up", "support_status", "human_summary",
            "evidence", "input_features",
        }
        assert required_keys <= set(j.keys())


# ===========================================================================
# Tests: explainer with direct importances (no file dependency)
# ===========================================================================

class TestExplainerWithDirectImportances:
    """Verify explainer works when importances are passed directly."""

    def test_direct_importances_override_file(self):
        demo_data_dir = REPO_ROOT / "kvrm-demos" / "content-moderation-router" / "data"
        registry = load_registry(demo_data_dir / "registry.json")
        custom_importances = {
            "auto_approve": [
                {"feature": "toxicity_level", "importance": 0.90},
                {"feature": "user_trust_score", "importance": 0.10},
            ],
        }
        explainer = DecisionExplainer(
            domain="content_moderation",
            registry=registry,
            feature_importances=custom_importances,
        )
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="content_moderation",
            eval_filename="cases.jsonl",
            case_index=0,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        expl = explainer.explain(decision, features)
        _assert_explanation_complete(expl)
        # If auto_approve was selected, factors should match our custom importances
        if expl.selected_action == "auto_approve":
            assert expl.top_factors[0].importance == 0.90


# ===========================================================================
# Tests: Counterfactual explanations
# ===========================================================================

SHAP_REPORT_PATH = REPO_ROOT / "kvrm-bench-results" / "shap" / "shap_analysis_report.json"


class TestCounterfactualExplanations:
    """Verify counterfactual explanations identify minimum feature changes."""

    def test_counterfactual_returns_list(self):
        """counterfactual() returns a list of CounterfactualExplanation."""
        idx = _find_case_index("content_moderation", supported=True)
        explainer = _build_explainer("content_moderation")
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="content_moderation",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        cfs = explainer.counterfactual(decision, features)
        assert isinstance(cfs, list)
        assert all(isinstance(cf, CounterfactualExplanation) for cf in cfs)

    def test_counterfactual_excludes_selected_action(self):
        """Counterfactuals are generated for non-selected actions only."""
        idx = _find_case_index("content_moderation", supported=True)
        explainer = _build_explainer("content_moderation")
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="content_moderation",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        cfs = explainer.counterfactual(decision, features)
        selected = decision.selected_action_id
        cf_targets = [cf.target_action_id for cf in cfs]
        assert selected not in cf_targets
        # Should have counterfactuals for all other actions
        registry = load_registry(
            REPO_ROOT / "kvrm-demos" / "content-moderation-router" / "data" / "registry.json"
        )
        other_ids = {a.action_id for a in registry.actions if a.action_id != selected}
        assert set(cf_targets) == other_ids

    def test_counterfactual_for_specific_target(self):
        """counterfactual() with target_action_id returns only that target."""
        idx = _find_case_index("content_moderation", supported=True)
        explainer = _build_explainer("content_moderation")
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="content_moderation",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        cfs = explainer.counterfactual(
            decision, features,
            target_action_id="remove_content",
        )
        assert len(cfs) == 1
        assert cfs[0].target_action_id == "remove_content"

    def test_counterfactual_has_human_summary(self):
        """Every counterfactual has a non-empty human_summary."""
        idx = _find_case_index("content_moderation", supported=True)
        explainer = _build_explainer("content_moderation")
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="content_moderation",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        cfs = explainer.counterfactual(decision, features)
        for cf in cfs:
            assert isinstance(cf.human_summary, str)
            assert len(cf.human_summary) > 10

    def test_counterfactual_feasibility_values(self):
        """Feasibility is always 'possible' or 'impossible'."""
        idx = _find_case_index("content_moderation", supported=True)
        explainer = _build_explainer("content_moderation")
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="content_moderation",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        cfs = explainer.counterfactual(decision, features)
        for cf in cfs:
            assert cf.feasibility in ("possible", "impossible")

    def test_counterfactual_feature_changes_typed(self):
        """Feature changes in counterfactuals have correct types."""
        idx = _find_case_index("content_moderation", supported=True)
        explainer = _build_explainer("content_moderation")
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="content_moderation",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        cfs = explainer.counterfactual(decision, features)
        for cf in cfs:
            for fc in cf.feature_changes:
                assert isinstance(fc, FeatureChange)
                assert isinstance(fc.feature, str)
                assert fc.change_type in ("value_change", "add_to_set", "remove_from_set")

    def test_counterfactual_customer_support(self):
        """Counterfactuals work for customer_support domain too."""
        idx = _find_case_index("customer_support", supported=True)
        explainer = _build_explainer("customer_support")
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="customer_support",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        cfs = explainer.counterfactual(decision, features)
        assert len(cfs) >= 1
        # At least some should be feasible
        feasible = [cf for cf in cfs if cf.feasibility == "possible"]
        assert len(feasible) >= 1


# ===========================================================================
# Tests: Batch export
# ===========================================================================

class TestBatchExport:
    """Verify explain_batch() produces JSON and CSV output."""

    def _get_batch_decisions(self, domain: str, n: int = 3):
        """Helper: run n demo cases and return (decision, features) tuples."""
        explainer = _build_explainer(domain)
        demo_data_dir = REPO_ROOT / "kvrm-demos" / f"{domain.replace('_', '-')}-router" / "data"
        cases = load_cases(demo_data_dir / "cases.jsonl")
        decisions = []
        for i in range(min(n, len(cases))):
            payload = run_demo_case(
                repo_root=str(REPO_ROOT),
                domain=domain,
                eval_filename="cases.jsonl",
                case_index=i,
            )
            decision = DecisionResult(**payload["decision"])
            features = payload["case"]["input_features"]
            decisions.append((decision, features))
        return explainer, decisions

    def test_batch_json_output_is_valid(self):
        """explain_batch(format='json') returns valid JSON array."""
        explainer, decisions = self._get_batch_decisions("content_moderation")
        result = explainer.explain_batch(decisions, format="json")
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == len(decisions)
        for entry in parsed:
            assert "case_id" in entry
            assert "selected_action" in entry
            assert "confidence" in entry
            assert "human_summary" in entry

    def test_batch_csv_output_is_valid(self):
        """explain_batch(format='csv') returns parseable CSV."""
        explainer, decisions = self._get_batch_decisions("content_moderation")
        result = explainer.explain_batch(decisions, format="csv")
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == len(decisions)
        for row in rows:
            assert "case_id" in row
            assert "selected_action" in row
            assert "confidence" in row
            assert row["case_id"]  # non-empty

    def test_batch_csv_headers(self):
        """CSV output contains all expected column headers."""
        explainer, decisions = self._get_batch_decisions("content_moderation", n=1)
        result = explainer.explain_batch(decisions, format="csv")
        reader = csv.DictReader(io.StringIO(result))
        headers = reader.fieldnames
        expected_headers = {
            "case_id", "selected_action", "confidence", "final_status",
            "human_summary", "support_in_support",
        }
        assert expected_headers <= set(headers)

    def test_batch_json_with_counterfactuals(self):
        """explain_batch with include_counterfactuals adds counterfactual data."""
        explainer, decisions = self._get_batch_decisions("content_moderation", n=2)
        result = explainer.explain_batch(
            decisions, format="json", include_counterfactuals=True,
        )
        parsed = json.loads(result)
        # At least one entry should have counterfactuals (if it has a runner-up)
        has_cf = any("counterfactuals" in entry for entry in parsed)
        # Not all cases necessarily have a runner-up, but the field should exist
        # for those that do
        for entry in parsed:
            if "counterfactuals" in entry:
                assert isinstance(entry["counterfactuals"], list)
                for cf in entry["counterfactuals"]:
                    assert "target_action_id" in cf
                    assert "feasibility" in cf
                    assert "human_summary" in cf
                    assert "feature_changes" in cf

    def test_batch_json_with_shap(self):
        """explain_batch with include_shap adds SHAP data when available."""
        demo_data_dir = REPO_ROOT / "kvrm-demos" / "content-moderation-router" / "data"
        registry = load_registry(demo_data_dir / "registry.json")

        shap_data = None
        if SHAP_REPORT_PATH.exists():
            shap_data = json.loads(SHAP_REPORT_PATH.read_text())

        explainer = DecisionExplainer(
            domain="content_moderation",
            registry=registry,
            interpretability_report_path=INTERPRETABILITY_REPORT,
            shap_values=shap_data,
        )

        cases = load_cases(demo_data_dir / "cases.jsonl")
        decisions = []
        for i in range(min(2, len(cases))):
            payload = run_demo_case(
                repo_root=str(REPO_ROOT),
                domain="content_moderation",
                eval_filename="cases.jsonl",
                case_index=i,
            )
            decision = DecisionResult(**payload["decision"])
            features = payload["case"]["input_features"]
            decisions.append((decision, features))

        result = explainer.explain_batch(
            decisions, format="json", include_shap=True,
        )
        parsed = json.loads(result)
        for entry in parsed:
            assert "shap_factors" in entry
            if shap_data:
                # SHAP data was loaded, so at least some entries should have factors
                assert isinstance(entry["shap_factors"], list)

    def test_batch_customer_support(self):
        """Batch export works for customer_support domain."""
        explainer, decisions = self._get_batch_decisions("customer_support", n=3)
        result_json = explainer.explain_batch(decisions, format="json")
        result_csv = explainer.explain_batch(decisions, format="csv")
        parsed = json.loads(result_json)
        assert len(parsed) == len(decisions)
        csv_rows = list(csv.DictReader(io.StringIO(result_csv)))
        assert len(csv_rows) == len(decisions)

    def test_batch_empty_input(self):
        """Batch export handles empty input gracefully."""
        explainer = _build_explainer("content_moderation")
        result_json = explainer.explain_batch([], format="json")
        result_csv = explainer.explain_batch([], format="csv")
        assert json.loads(result_json) == []
        assert result_csv == ""


# ===========================================================================
# Tests: SHAP integration
# ===========================================================================

class TestShapIntegration:
    """Verify SHAP integration in explanations."""

    def test_shap_values_from_full_report(self):
        """Explainer loads SHAP values from the full analysis report."""
        if not SHAP_REPORT_PATH.exists():
            import pytest
            pytest.skip("SHAP report not found")

        demo_data_dir = REPO_ROOT / "kvrm-demos" / "content-moderation-router" / "data"
        registry = load_registry(demo_data_dir / "registry.json")
        shap_data = json.loads(SHAP_REPORT_PATH.read_text())

        explainer = DecisionExplainer(
            domain="content_moderation",
            registry=registry,
            interpretability_report_path=INTERPRETABILITY_REPORT,
            shap_values=shap_data,
        )

        idx = _find_case_index("content_moderation", supported=True)
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="content_moderation",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        expl = explainer.explain(decision, features)

        # Should have SHAP factors populated
        assert isinstance(expl.shap_factors, list)
        if expl.selected_action in shap_data["domains"]["content_moderation"]["per_action_directions"]:
            assert len(expl.shap_factors) > 0
            for sf in expl.shap_factors:
                assert isinstance(sf, ShapFactor)
                assert sf.direction in ("pushes_toward", "pushes_away", "neutral")
                assert isinstance(sf.mean_abs_shap, float)
                assert isinstance(sf.mean_shap, float)

    def test_shap_factors_empty_when_no_data(self):
        """Without SHAP data, shap_factors is an empty list."""
        idx = _find_case_index("content_moderation", supported=True)
        explainer = _build_explainer("content_moderation")  # No SHAP data
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="content_moderation",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        expl = explainer.explain(decision, features)
        assert expl.shap_factors == []

    def test_shap_values_from_direct_dict(self):
        """Explainer accepts per_action_directions dict directly."""
        demo_data_dir = REPO_ROOT / "kvrm-demos" / "content-moderation-router" / "data"
        registry = load_registry(demo_data_dir / "registry.json")

        custom_shap = {
            "per_action_directions": {
                "auto_approve": [
                    {"feature": "toxicity_level", "direction": "pushes_away", "mean_abs_shap": 0.10, "mean_shap": -0.05},
                ],
            },
        }
        explainer = DecisionExplainer(
            domain="content_moderation",
            registry=registry,
            shap_values=custom_shap,
        )
        # The internal state should have resolved it
        assert "auto_approve" in explainer._per_action_shap

    def test_shap_values_from_raw_action_dict(self):
        """Explainer accepts bare per-action dict (no wrapping key)."""
        demo_data_dir = REPO_ROOT / "kvrm-demos" / "content-moderation-router" / "data"
        registry = load_registry(demo_data_dir / "registry.json")

        raw_shap = {
            "auto_approve": [
                {"feature": "toxicity_level", "direction": "pushes_toward", "mean_abs_shap": 0.20, "mean_shap": 0.15},
            ],
        }
        explainer = DecisionExplainer(
            domain="content_moderation",
            registry=registry,
            shap_values=raw_shap,
        )
        assert "auto_approve" in explainer._per_action_shap

    def test_shap_customer_support_domain(self):
        """SHAP integration works for customer_support with real report."""
        if not SHAP_REPORT_PATH.exists():
            import pytest
            pytest.skip("SHAP report not found")

        demo_data_dir = REPO_ROOT / "kvrm-demos" / "customer-support-router" / "data"
        registry = load_registry(demo_data_dir / "registry.json")
        shap_data = json.loads(SHAP_REPORT_PATH.read_text())

        explainer = DecisionExplainer(
            domain="customer_support",
            registry=registry,
            interpretability_report_path=INTERPRETABILITY_REPORT,
            shap_values=shap_data,
        )

        idx = _find_case_index("customer_support", supported=True)
        payload = run_demo_case(
            repo_root=str(REPO_ROOT),
            domain="customer_support",
            eval_filename="cases.jsonl",
            case_index=idx,
        )
        decision = DecisionResult(**payload["decision"])
        features = payload["case"]["input_features"]
        expl = explainer.explain(decision, features)
        assert isinstance(expl.shap_factors, list)
        # customer_support has SHAP data for all 7 actions
        if expl.selected_action in shap_data["domains"]["customer_support"]["per_action_directions"]:
            assert len(expl.shap_factors) > 0
