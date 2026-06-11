from __future__ import annotations

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "age_bracket",
    "acuity_score",
    "fever_bucket",
    "hypotension",
    "focal_neuro_deficit",
    "chest_pain",
    "respiratory_distress",
    "infection_risk",
    "symptom_onset",
    "clinician_note_flag",
]

CATEGORICAL_VALUES = {
    "age_bracket": ["pediatric", "adult", "older_adult"],
    "acuity_score": ["low", "moderate", "high", "critical"],
    "fever_bucket": ["none", "mild", "high"],
    "infection_risk": ["low", "medium", "high"],
    "symptom_onset": ["sudden", "progressive", "unclear"],
    "clinician_note_flag": ["none", "sepsis_concern", "stroke_concern", "cardiac_concern", "complex"],
}

RULES = {
    feature_key({"age_bracket": "adult", "acuity_score": "low", "fever_bucket": "none", "hypotension": False, "focal_neuro_deficit": False, "chest_pain": False, "respiratory_distress": False, "infection_risk": "low", "symptom_onset": "progressive", "clinician_note_flag": "none"}): ("routine_review", 0.95),
    feature_key({"age_bracket": "adult", "acuity_score": "critical", "fever_bucket": "high", "hypotension": True, "focal_neuro_deficit": False, "chest_pain": False, "respiratory_distress": True, "infection_risk": "high", "symptom_onset": "progressive", "clinician_note_flag": "sepsis_concern"}): ("sepsis_screen_pathway", 0.99),
    feature_key({"age_bracket": "older_adult", "acuity_score": "critical", "fever_bucket": "none", "hypotension": False, "focal_neuro_deficit": True, "chest_pain": False, "respiratory_distress": False, "infection_risk": "low", "symptom_onset": "sudden", "clinician_note_flag": "stroke_concern"}): ("stroke_alert_pathway", 0.99),
    feature_key({"age_bracket": "older_adult", "acuity_score": "high", "fever_bucket": "none", "hypotension": False, "focal_neuro_deficit": False, "chest_pain": True, "respiratory_distress": False, "infection_risk": "low", "symptom_onset": "sudden", "clinician_note_flag": "cardiac_concern"}): ("cardiac_chest_pain_pathway", 0.96),
    feature_key({"age_bracket": "adult", "acuity_score": "high", "fever_bucket": "mild", "hypotension": False, "focal_neuro_deficit": False, "chest_pain": False, "respiratory_distress": True, "infection_risk": "medium", "symptom_onset": "progressive", "clinician_note_flag": "none"}): ("respiratory_support_pathway", 0.94),
    feature_key({"age_bracket": "adult", "acuity_score": "moderate", "fever_bucket": "mild", "hypotension": False, "focal_neuro_deficit": False, "chest_pain": False, "respiratory_distress": False, "infection_risk": "high", "symptom_onset": "progressive", "clinician_note_flag": "none"}): ("lab_panel_priority_order", 0.88),
    feature_key({"age_bracket": "adult", "acuity_score": "critical", "fever_bucket": "mild", "hypotension": True, "focal_neuro_deficit": True, "chest_pain": True, "respiratory_distress": True, "infection_risk": "high", "symptom_onset": "unclear", "clinician_note_flag": "complex"}): ("escalate_supervisor_review", 0.97),
}

EXECUTOR_HANDLERS = {
    "routine_review": "routine_review",
    "urgent_clinician_review": "urgent_clinician_review",
    "sepsis_screen_pathway": "sepsis_screen_pathway",
    "stroke_alert_pathway": "stroke_alert_pathway",
    "cardiac_chest_pain_pathway": "cardiac_chest_pain_pathway",
    "respiratory_support_pathway": "respiratory_support_pathway",
    "lab_panel_priority_order": "lab_panel_priority_order",
    "escalate_supervisor_review": "escalate_supervisor_review",
}

CONFIG = DomainConfig(
    name="medical",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="workflow",
    reason_actions={"escalate_supervisor_review"},
    fallback_action_id="escalate_supervisor_review",
    prototype_max_distance=5.0,
    prototype_raw_distance_floor_ratio=0.8,
    semantic_min_leaf_count=4,
    semantic_base_confidence=0.78,
    semantic_per_leaf_bonus=0.02,
    semantic_max_confidence=0.96,
    learned_min_confidence=0.45,
    learned_candidate_floor=0.20,
)

(
    build_rule_selector,
    build_retrieval_selector,
    build_prototype_selector,
    build_semantic_selector,
    build_learned_selector,
    build_hybrid_selector,
) = build_domain_selectors(CONFIG)


def build_executor() -> DictionaryExecutor:
    return build_domain_executor(CONFIG)
