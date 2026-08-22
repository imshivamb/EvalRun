"""Evaluation profile for the minimal support-triage benchmark."""

from framework.evaluation.dimensions import (
    ADAPTABILITY,
    CONSTRAINT_SATISFACTION,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    PLANNING_QUALITY,
)
from framework.models import EvaluationProfile


# The existing dimensions are intentionally reused for this small proof of
# generalization. Their support interpretation is documented in the scenario:
# constraints=SLA/policy, planning=triage actions, accuracy=category/facts,
# personalization=tone, adaptability=escalation judgment.
SUPPORT_TRIAGE_PROFILE = EvaluationProfile(
    name="support-triage",
    weights={
        CONSTRAINT_SATISFACTION: 30.0,
        INFORMATION_ACCURACY: 25.0,
        PLANNING_QUALITY: 20.0,
        ADAPTABILITY: 15.0,
        PERSONALIZATION: 10.0,
    },
    pass_threshold=75.0,
)
