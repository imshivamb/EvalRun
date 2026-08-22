"""Independent Budget Auditor implementation for financial verification."""

import json
import re
import sys
from typing import Dict, Any, Optional

from agents.base import BaseAgent
from agents.auditor.schema import AuditReport, BudgetViolation, FailureCode
from framework.llms.base import BaseLLM, Message


AUDITOR_SYSTEM_PROMPT = """You are an Independent Financial Budget Auditor for travel itineraries.
Your sole job is to independently inspect a finalized travel itinerary against the given scenario requirements and verify financial compliance.

CRITICAL RULES:
1. You are READ-ONLY. You MUST NOT rewrite, edit, or summarize the itinerary.
2. You MUST NOT negotiate constraints or assume unstated discounts.
3. Be strict, precise, and objective.

You must check for four specific failure types:
1. MATH_HALLUCINATION: The itinerary claims to save money (e.g. "taking highway bus saves ₹20,000") without providing verifiable pricing arithmetic or explicit itemized breakdowns.
2. DAILY_OVERRUN: The sum of food, local transit, and activities on any given day exceeds the specified daily budget allowance limit.
3. HIDDEN_OVERHEAD: Essential travel expenses (e.g. airport return transfer, luggage lockers, mandatory temple/attraction entry fees, local IC card top-ups) are omitted to artificially appear under budget.
4. ANCHOR_MUTATION: Pre-paid, locked, or non-refundable bookings (e.g. specific hotel stays or return flights) are altered, canceled, or replaced without authorization.

OUTPUT FORMAT:
You MUST respond ONLY with a valid JSON object wrapped in ```json ... ``` with the following keys:
{
  "status": "PASS" | "BLOCK",
  "audit_score": <float between 0.0 and 100.0>,
  "violations": [
    {
      "violation_type": "MATH_HALLUCINATION" | "DAILY_OVERRUN" | "HIDDEN_OVERHEAD" | "ANCHOR_MUTATION",
      "description": "<detailed explanation of the violation>",
      "estimated_discrepancy_inr": <estimated discrepancy in INR float>,
      "affected_days": [<list of integer day numbers>]
    }
  ],
  "total_estimated_spend_inr": <float>,
  "budget_limit_inr": <float>,
  "variance_inr": <float, positive means under budget, negative means overspend>,
  "audit_confidence": <float between 0.0 and 1.0>,
  "reasoning_summary": "<brief summary of findings>"
}
"""


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
        user_content = f"### SCENARIO PROMPT\n{scenario_prompt}\n\n"
        if total_budget_inr is not None:
            user_content += f"TOTAL BUDGET LIMIT (INR): ₹{total_budget_inr:,.2f}\n"
        if daily_budget_jpy is not None:
            user_content += f"DAILY ALLOWANCE LIMIT (JPY): ¥{daily_budget_jpy:,.2f}\n"

        user_content += f"\n### FINAL ITINERARY TO AUDIT\n{itinerary_content}\n\n"
        user_content += "Perform your independent budget audit and return JSON only."

        messages = [
            Message(role="system", content=AUDITOR_SYSTEM_PROMPT),
            Message(role="user", content=user_content),
        ]

        last_error = ""
        last_raw_response = ""

        for attempt in range(self.max_retries + 1):
            response = self.llm.generate(messages)
            last_raw_response = response.text
            report, parse_err = self._parse_and_validate_json(response.text)
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

    def _parse_and_validate_json(self, text: str) -> (Optional[AuditReport], Optional[str]):
        """Strictly extracts and validates AuditReport from LLM response.

        Returns:
            (AuditReport, None) on success, or (None, error_message) on validation failure.
        """
        try:
            # 1. Extract JSON text
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                raw_json = match.group(1)
            else:
                match_brace = re.search(r"(\{.*\})", text, re.DOTALL)
                if match_brace:
                    raw_json = match_brace.group(1)
                else:
                    return None, "No JSON codeblock or object found in model output"

            # 2. Parse JSON syntax
            try:
                data = json.loads(raw_json)
            except Exception as ex:
                return None, f"JSON syntax error: {str(ex)}"

            if not isinstance(data, dict):
                return None, "Root JSON payload must be an object"

            # 3. Check mandatory keys
            required_keys = [
                "status",
                "audit_score",
                "violations",
                "total_estimated_spend_inr",
                "budget_limit_inr",
                "variance_inr",
                "audit_confidence",
                "reasoning_summary",
            ]
            missing_keys = [k for k in required_keys if k not in data]
            if missing_keys:
                return None, f"Missing required top-level JSON keys: {missing_keys}"

            # 4. Validate status
            status = str(data["status"]).upper().strip()
            if status not in ("PASS", "BLOCK"):
                return None, f"Invalid status '{data['status']}'; must be 'PASS' or 'BLOCK'"

            # 5. Validate ranges for numerical metrics
            try:
                audit_score = float(data["audit_score"])
                if not (0.0 <= audit_score <= 100.0):
                    return None, f"audit_score {audit_score} out of bounds [0.0, 100.0]"
            except (ValueError, TypeError):
                return None, "audit_score must be a numeric float"

            try:
                audit_confidence = float(data["audit_confidence"])
                if not (0.0 <= audit_confidence <= 1.0):
                    return None, f"audit_confidence {audit_confidence} out of bounds [0.0, 1.0]"
            except (ValueError, TypeError):
                return None, "audit_confidence must be a numeric float"

            # 6. Validate violations list and failure codes
            raw_violations = data["violations"]
            if not isinstance(raw_violations, list):
                return None, "'violations' must be a JSON array"

            violations = []
            for idx, v in enumerate(raw_violations):
                if not isinstance(v, dict):
                    return None, f"violation at index {idx} must be an object"

                v_type = v.get("violation_type")
                if not v_type or v_type not in FailureCode.ALL_CODES:
                    return None, f"violation at index {idx} has invalid type '{v_type}'; must be one of {FailureCode.ALL_CODES}"

                description = v.get("description")
                if not description or not str(description).strip():
                    return None, f"violation at index {idx} is missing a description"

                try:
                    disc = float(v.get("estimated_discrepancy_inr", 0.0))
                except (ValueError, TypeError):
                    disc = 0.0

                affected_days = []
                if "affected_days" in v and isinstance(v["affected_days"], list):
                    for d in v["affected_days"]:
                        try:
                            affected_days.append(int(d))
                        except (ValueError, TypeError):
                            pass

                violations.append(
                    BudgetViolation(
                        violation_type=v_type,
                        description=str(description).strip(),
                        estimated_discrepancy_inr=disc,
                        affected_days=affected_days,
                    )
                )

            # 7. Validate Status vs Violations Consistency
            if status == "PASS" and len(violations) > 0:
                return None, f"Status is 'PASS' but violations array is non-empty ({len(violations)} violations specified)"
            if status == "BLOCK" and len(violations) == 0:
                return None, "Status is 'BLOCK' but violations array is empty (must list at least 1 violation)"

            return (
                AuditReport(
                    status=status,
                    audit_score=audit_score,
                    violations=violations,
                    total_estimated_spend_inr=float(data.get("total_estimated_spend_inr", 0.0)),
                    budget_limit_inr=float(data.get("budget_limit_inr", 0.0)),
                    variance_inr=float(data.get("variance_inr", 0.0)),
                    audit_confidence=audit_confidence,
                    reasoning_summary=str(data.get("reasoning_summary", "")),
                ),
                None,
            )
        except Exception as e:
            return None, f"Unexpected error parsing audit JSON: {str(e)}"
