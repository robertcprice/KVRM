from __future__ import annotations

from typing import Any

from kvrm_core.context import feature_key
from kvrm_core.domain_factory import DomainConfig, build_domain_selectors, build_domain_executor
from kvrm_core.execution import DictionaryExecutor

FEATURE_ORDER = [
    "toxicity_level",
    "content_type",
    "reporter_credibility",
    "user_trust_score",
    "context_sensitivity",
    "audience_reach",
    "recidivism_risk",
    "content_age_hours",
]

CATEGORICAL_VALUES = {
    "toxicity_level": ["none", "mild", "moderate", "severe", "extreme"],
    "content_type": ["text", "image", "video", "link", "mixed"],
    "reporter_credibility": ["new_reporter", "established", "trusted", "internal_tool"],
    "user_trust_score": ["new_user", "low", "medium", "high", "verified"],
    "context_sensitivity": ["general", "minor_present", "workplace", "public_figure", "crisis"],
    "audience_reach": ["private", "small_group", "community", "viral"],
    "recidivism_risk": ["first_offense", "repeat_minor", "repeat_major", "serial"],
    "content_age_hours": ["fresh", "recent", "aged", "archived"],
}


def _is_inconsistent_moderation_state(features: dict[str, Any]) -> bool:
    if features.get("content_age_hours") == "archived" and features.get("audience_reach") == "viral":
        return True
    if features.get("recidivism_risk") == "serial" and features.get("user_trust_score") == "verified":
        return True
    if (
        features.get("content_type") == "video"
        and features.get("content_age_hours") == "fresh"
        and features.get("reporter_credibility") == "internal_tool"
    ):
        return True
    if features.get("toxicity_level") == "none" and features.get("recidivism_risk") == "serial":
        return True
    return False


RULES = {
    feature_key({
        "toxicity_level": "none",
        "content_type": "text",
        "reporter_credibility": "new_reporter",
        "user_trust_score": "medium",
        "context_sensitivity": "general",
        "audience_reach": "private",
        "recidivism_risk": "first_offense",
        "content_age_hours": "fresh",
    }): ("auto_approve", 0.98),
    feature_key({
        "toxicity_level": "mild",
        "content_type": "text",
        "reporter_credibility": "established",
        "user_trust_score": "low",
        "context_sensitivity": "general",
        "audience_reach": "community",
        "recidivism_risk": "first_offense",
        "content_age_hours": "recent",
    }): ("reduce_visibility", 0.92),
    feature_key({
        "toxicity_level": "moderate",
        "content_type": "image",
        "reporter_credibility": "trusted",
        "user_trust_score": "medium",
        "context_sensitivity": "workplace",
        "audience_reach": "community",
        "recidivism_risk": "repeat_minor",
        "content_age_hours": "recent",
    }): ("flag_for_human_review", 0.92),
    feature_key({
        "toxicity_level": "extreme",
        "content_type": "text",
        "reporter_credibility": "trusted",
        "user_trust_score": "low",
        "context_sensitivity": "general",
        "audience_reach": "viral",
        "recidivism_risk": "repeat_major",
        "content_age_hours": "fresh",
    }): ("remove_content", 0.97),
    feature_key({
        "toxicity_level": "severe",
        "content_type": "text",
        "reporter_credibility": "internal_tool",
        "user_trust_score": "new_user",
        "context_sensitivity": "general",
        "audience_reach": "viral",
        "recidivism_risk": "serial",
        "content_age_hours": "fresh",
    }): ("suspend_account", 0.96),
    feature_key({
        "toxicity_level": "severe",
        "content_type": "video",
        "reporter_credibility": "internal_tool",
        "user_trust_score": "low",
        "context_sensitivity": "crisis",
        "audience_reach": "viral",
        "recidivism_risk": "repeat_major",
        "content_age_hours": "fresh",
    }): ("escalate_trust_safety", 0.99),
    feature_key({
        "toxicity_level": "extreme",
        "content_type": "image",
        "reporter_credibility": "established",
        "user_trust_score": "medium",
        "context_sensitivity": "general",
        "audience_reach": "community",
        "recidivism_risk": "first_offense",
        "content_age_hours": "recent",
    }): ("remove_content", 0.97),
    feature_key({
        "toxicity_level": "moderate",
        "content_type": "text",
        "reporter_credibility": "trusted",
        "user_trust_score": "high",
        "context_sensitivity": "minor_present",
        "audience_reach": "small_group",
        "recidivism_risk": "first_offense",
        "content_age_hours": "fresh",
    }): ("remove_content", 0.95),
    feature_key({
        "toxicity_level": "severe",
        "content_type": "text",
        "reporter_credibility": "trusted",
        "user_trust_score": "new_user",
        "context_sensitivity": "general",
        "audience_reach": "community",
        "recidivism_risk": "serial",
        "content_age_hours": "fresh",
    }): ("suspend_account", 0.96),
    feature_key({
        "toxicity_level": "mild",
        "content_type": "text",
        "reporter_credibility": "established",
        "user_trust_score": "medium",
        "context_sensitivity": "crisis",
        "audience_reach": "small_group",
        "recidivism_risk": "first_offense",
        "content_age_hours": "recent",
    }): ("escalate_trust_safety", 0.99),
    feature_key({
        "toxicity_level": "moderate",
        "content_type": "link",
        "reporter_credibility": "established",
        "user_trust_score": "medium",
        "context_sensitivity": "general",
        "audience_reach": "viral",
        "recidivism_risk": "serial",
        "content_age_hours": "recent",
    }): ("escalate_trust_safety", 0.97),
    feature_key({
        "toxicity_level": "mild",
        "content_type": "mixed",
        "reporter_credibility": "new_reporter",
        "user_trust_score": "high",
        "context_sensitivity": "general",
        "audience_reach": "private",
        "recidivism_risk": "first_offense",
        "content_age_hours": "aged",
    }): ("request_human_review", 0.88),
}

EXECUTOR_HANDLERS = {
    "auto_approve": "auto_approve",
    "reduce_visibility": "reduce_visibility",
    "flag_for_human_review": "flag_for_human_review",
    "remove_content": "remove_content",
    "suspend_account": "suspend_account",
    "escalate_trust_safety": "escalate_trust_safety",
    "request_human_review": "request_human_review",
}

CONFIG = DomainConfig(
    name="content_moderation",
    feature_order=FEATURE_ORDER,
    categorical_values=CATEGORICAL_VALUES,
    rules=RULES,
    executor_handlers=EXECUTOR_HANDLERS,
    executor_output_key="workflow",
    reason_actions={"escalate_trust_safety", "request_human_review"},
    fallback_action_id="request_human_review",
    unsupported_penalty=1.5,
    extra_predicate=_is_inconsistent_moderation_state,
    prototype_max_distance=5.5,
    prototype_raw_distance_floor_ratio=0.8,
    semantic_tags={"fallback"},
    semantic_min_leaf_count=3,
    semantic_base_confidence=0.80,
    semantic_per_leaf_bonus=0.02,
    semantic_max_confidence=0.96,
    learned_min_confidence=0.42,
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
