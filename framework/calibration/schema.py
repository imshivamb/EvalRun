"""Calibration case identity and human-label validation."""

import hashlib
import re
from typing import Any, Dict, List

from framework.evaluation.dimensions import (
    ADAPTABILITY,
    CONSTRAINT_SATISFACTION,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    PLANNING_QUALITY,
)

TRAVEL_AND_SUPPORT_DIMENSIONS = (
    CONSTRAINT_SATISFACTION,
    PLANNING_QUALITY,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    ADAPTABILITY,
)

ALLOWED_SCALE = "0-100-step-5"
ALLOWED_SCORES = set(range(0, 101, 5))

# Version 2 adds typed decisions so one labeling pass serves both judge
# calibration (scores) and typed-decision model benchmarks (decisions).
LABEL_SCHEMA_VERSION = 2

YES_NO = ("yes", "no")
FAILURE_CATEGORIES = (
    "none",
    "constraint_violation",
    "factual_error",
    "missing_requirement",
    "wrong_action",
    "unsafe_or_policy",
    "low_quality",
)
DECISION_CHOICES = {
    "release": ("approve", "block"),
    "hard_failure": YES_NO,
    "policy_violation": YES_NO,
    "needs_human_review": YES_NO,
    "primary_failure_category": FAILURE_CATEGORIES,
    "rater_confidence": ("certain", "unsure"),
}


def normalize_output_text(text: str) -> str:
    """Collapse whitespace so near-duplicate itineraries hash the same."""
    return " ".join((text or "").split())


def content_sha256(text: str) -> str:
    normalized = normalize_output_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def make_case_id(scenario_id: str, source_tag: str, digest: str) -> str:
    scenario = _slug(scenario_id)
    source = _slug(source_tag)
    return f"{scenario}__{source}__{digest[:8]}"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    return cleaned.strip("-") or "unknown"


def validate_labels(payload: Dict[str, Any]) -> List[str]:
    """Return human-readable errors; empty list means the payload is valid."""
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["labels payload must be an object"]
    if not payload.get("case_id"):
        errors.append("case_id is required")
    if not payload.get("rater_id"):
        errors.append("rater_id is required")
    if payload.get("schema_version") != LABEL_SCHEMA_VERSION:
        errors.append(f"schema_version must be {LABEL_SCHEMA_VERSION}")
    if payload.get("scale") != ALLOWED_SCALE:
        errors.append(f"scale must be {ALLOWED_SCALE}")
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        errors.append("scores must be an object")
    else:
        for dimension in TRAVEL_AND_SUPPORT_DIMENSIONS:
            if dimension not in scores:
                errors.append(f"missing score for {dimension}")
                continue
            raw = scores[dimension]
            if not isinstance(raw, int) or isinstance(raw, bool) or raw not in ALLOWED_SCORES:
                errors.append(f"{dimension} score {raw!r} is not in the 0-100 step-5 grid")
    errors.extend(_validate_decisions(payload.get("decisions")))
    return errors


def _validate_decisions(decisions: Any) -> List[str]:
    if not isinstance(decisions, dict):
        return ["decisions must be an object"]
    errors: List[str] = []
    for name, choices in DECISION_CHOICES.items():
        if name not in decisions:
            errors.append(f"missing decision {name}")
        elif decisions[name] not in choices:
            errors.append(f"decision {name} {decisions[name]!r} must be one of {', '.join(choices)}")
    if errors:
        return errors
    # A release verdict must be explainable by the rater's own failure labels.
    if decisions["release"] == "approve":
        if decisions["hard_failure"] == "yes":
            errors.append("release cannot be approve when hard_failure is yes")
        if decisions["policy_violation"] == "yes":
            errors.append("release cannot be approve when policy_violation is yes")
    if decisions["release"] == "block" and decisions["primary_failure_category"] == "none":
        errors.append("release block requires a primary_failure_category other than none")
    return errors
