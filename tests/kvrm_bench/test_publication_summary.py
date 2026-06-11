from __future__ import annotations

import json
from pathlib import Path

from kvrm_bench.publication_summary import build_publication_summary


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_publication_summary_reads_live_artifacts_and_writes_outputs(tmp_path: Path) -> None:
    result = build_publication_summary(REPO_ROOT, output_dir=tmp_path)

    json_path = Path(result["path"])
    markdown_path = Path(result["markdown_path"])
    assert json_path.exists()
    assert markdown_path.exists()

    summary = json.loads(json_path.read_text(encoding="utf-8"))
    sections = summary["sections"]

    assert sections["canonical_suite"]["available"] is True
    assert sections["canonical_suite"]["domain_count"] == 9
    # customer_support (97.2%) and content_moderation (97.5%) are not at 100%
    # so this is False with 9 domains; the original 7 canonical domains are still perfect
    assert sections["canonical_suite"]["all_semantic_correctness_one"] is False
    assert sections["canonical_suite"]["all_false_accept_zero"] is True
    assert sections["support_gate_stress"]["available"] is True
    assert sections["support_gate_stress"]["gated_perfect_semantic_domain_count"] == 7
    assert sections["fallback_feasibility"]["strict_zero_unsafe_execution_domain_count"] == 2
    assert sections["registry_evolution"]["live_continuity_domain_count"] == 7
    assert sections["incident_replay"]["hybrid_loss_count"] == 0
    assert sections["counterfactual_boundary"]["hybrid_loss_count"] == 0
    assert sections["temporal_transition"]["hybrid_loss_count"] == 0
    assert sections["coordination_chain"]["hybrid_loss_count"] == 0
    assert sections["ambiguity_frontier"]["zero_regret_domain_count"] == 7
    assert sections["feature_ceiling"]["exact_oracle_match_domain_count"] == 7
    assert sections["external_baselines"]["available"] is True
    assert sections["external_baselines"]["best_model"]["name"] == "gemma4:e2b"

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# KVRM Publication Summary" in markdown
    assert "Canonical hybrid KVRM remains perfect on the live canonical suite." in markdown
    assert "Best evaluated Ollama baseline on the live six-domain subset is `gemma4:e2b`" in markdown
