"""Independent Budget Auditor implementation for financial verification."""

from typing import Optional, Any

from agents.base import BaseAgent
from agents.auditor.schema import AuditReport, BudgetViolation, FailureCode
from agents.auditor.prompts import AUDITOR_SYSTEM_PROMPT, format_auditor_user_prompt
from agents.auditor.parser import AuditParser
from framework.llms.base import BaseLLM, Message


class IndependentBudgetAuditor(BaseAgent):
    """An independent budget auditing agent with zero shared memory of reflection state."""

    def __init__(self, llm: BaseLLM, max_retries: int = 2):
        self.llm = llm
        self.max_retries = max_retries

    def audit(
        self,
        scenario_prompt: str,
        itinerary_content: str,
        total_budget_inr: Optional[float] = None,
        daily_budget_jpy: Optional[float] = None,
    ) -> AuditReport:
        """Independently audits an itinerary against scenario budget constraints.

        Args:
            scenario_prompt: Original scenario specification prompt.
            itinerary_content: Finalized itinerary content to audit.
            total_budget_inr: Optional overall total budget limit in INR.
            daily_budget_jpy: Optional daily spend allowance limit in JPY.

        Returns:
            An AuditReport instance detailing PASS/BLOCK status and violations.
        """
        user_content = format_auditor_user_prompt(
            scenario_prompt=scenario_prompt,
            itinerary_content=itinerary_content,
            total_budget_inr=total_budget_inr,
            daily_budget_jpy=daily_budget_jpy,
        )

        messages = [
            Message(role="system", content=AUDITOR_SYSTEM_PROMPT),
            Message(role="user", content=user_content),
        ]

        last_error = ""
        last_raw_response = ""

        for attempt in range(self.max_retries + 1):
            response = self.llm.generate(messages)
            last_raw_response = response.text
            report, parse_err = AuditParser.parse_and_validate(response.text)
            if report is not None:
                report.retries_attempted = attempt
                return report

            last_error = parse_err or "Unknown validation error"
            if attempt < self.max_retries:
                messages.append(Message(role="assistant", content=response.text))
                messages.append(
                    Message(
                        role="user",
                        content=f"Your previous response was rejected due to validation failure: '{last_error}'. Please correct your output and return ONLY a valid JSON object matching the exact schema inside ```json ... ```.",
                    )
                )

        # Fallback default report if all retries fail
        return AuditReport(
            status="BLOCK",
            audit_score=0.0,
            violations=[
                BudgetViolation(
                    violation_type=FailureCode.MATH_HALLUCINATION,
                    description=f"Auditor failed output validation: {last_error}",
                )
            ],
            reasoning_summary=f"Audit failed due to model output validation failure: {last_error}",
            audit_confidence=0.0,
            parse_error=last_error,
            retries_attempted=self.max_retries + 1,
            raw_model_response=last_raw_response,
        )

    def run(self, prompt: str, **kwargs) -> Any:
        """Standard AgentOutput wrapper for pipeline runner compatibility."""
        itinerary = kwargs.get("itinerary_content", prompt)
        scenario = kwargs.get("scenario_prompt", prompt)
        return self.audit(scenario_prompt=scenario, itinerary_content=itinerary)
