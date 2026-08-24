"""Support-domain evaluator prompts.

The core dimensions are shared with travel, but their rubrics are not.  Keeping
these prompts separate prevents a support ticket from being judged as if it
were an itinerary.
"""

from typing import List

from framework.evaluation.dimensions import (
    ADAPTABILITY,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    PLANNING_QUALITY,
)
from framework.evaluation.evaluators.base_llm import BaseLLMEvaluator
from framework.evaluation.prompts.base import build_llm_judge_prompt
from framework.llms import Message
from framework.models import AgentOutput, Benchmark
from framework.verification.pipeline import VerificationPipeline


class _SupportEvaluator(BaseLLMEvaluator):
    rubric = ""

    def build_prompt(self, benchmark: Benchmark, output: AgentOutput) -> List[Message]:
        return build_llm_judge_prompt(
            "You are an objective evaluator for a customer-support triage agent.",
            self.rubric,
            benchmark,
            output,
        )


class SupportPlanningEvaluator(_SupportEvaluator):
    dimension = PLANNING_QUALITY
    rubric = (
        "Evaluate whether the triage workflow is ordered and operationally useful. "
        "Check acknowledgement, SLA preservation, escalation order, evidence gathering, "
        "containment actions, and the next customer update. Do not apply travel or itinerary criteria."
    )


class SupportPersonalizationEvaluator(_SupportEvaluator):
    dimension = PERSONALIZATION
    rubric = (
        "Evaluate whether the response is appropriately tailored to this enterprise customer, "
        "the EU production impact, the imminent launch, and the requested support-owner role. "
        "Assess empathy, clarity, and usefulness of the customer-facing message."
    )


class SupportAdaptabilityEvaluator(_SupportEvaluator):
    dimension = ADAPTABILITY
    rubric = (
        "Evaluate how well the triage plan handles uncertainty and branching conditions. "
        "Check the distinction between immediate Payments/Incident Commander escalation and "
        "conditional EU platform escalation, while avoiding an unverified root-cause claim."
    )


class SupportInformationAccuracyEvaluator(BaseLLMEvaluator):
    dimension = INFORMATION_ACCURACY

    def __init__(self, llm, pipeline: VerificationPipeline):
        super().__init__(llm)
        self.pipeline = pipeline

    def build_prompt(self, benchmark: Benchmark, output: AgentOutput) -> List[Message]:
        report = self.pipeline.run(output)
        return build_llm_judge_prompt(
            "You are an objective evaluator checking factual accuracy in a customer-support triage response.",
            (
                "Check that observed incident facts, priority, timestamps, impact, and escalation "
                "targets match the scenario. Separate facts from hypotheses and do not penalize "
                "unknown claims merely because they are absent from an unrelated knowledge base.\n\n"
                f"Verification evidence:\n{report}"
            ),
            benchmark,
            output,
        )
