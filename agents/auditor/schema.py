"""Data contracts for the Independent Budget Auditor."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


class FailureCode:
    MATH_HALLUCINATION = "MATH_HALLUCINATION"
    DAILY_OVERRUN = "DAILY_OVERRUN"
    HIDDEN_OVERHEAD = "HIDDEN_OVERHEAD"
    ANCHOR_MUTATION = "ANCHOR_MUTATION"

    ALL_CODES = [MATH_HALLUCINATION, DAILY_OVERRUN, HIDDEN_OVERHEAD, ANCHOR_MUTATION]


@dataclass
class BudgetViolation:
    violation_type: str  # One of FailureCode.ALL_CODES
    description: str
    estimated_discrepancy_inr: float = 0.0
    affected_days: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_type": self.violation_type,
            "description": self.description,
            "estimated_discrepancy_inr": self.estimated_discrepancy_inr,
            "affected_days": self.affected_days,
        }


@dataclass
class AuditReport:
    status: str  # "PASS" or "BLOCK"
    audit_score: float  # 0.0 to 100.0
    violations: List[BudgetViolation] = field(default_factory=list)
    total_estimated_spend_inr: float = 0.0
    budget_limit_inr: float = 0.0
    variance_inr: float = 0.0
    audit_confidence: float = 1.0
    reasoning_summary: str = ""
    parse_error: Optional[str] = None
    retries_attempted: int = 0
    raw_model_response: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.status.upper() == "PASS"

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "status": self.status,
            "passed": self.passed,
            "audit_score": self.audit_score,
            "violations": [v.to_dict() for v in self.violations],
            "total_estimated_spend_inr": self.total_estimated_spend_inr,
            "budget_limit_inr": self.budget_limit_inr,
            "variance_inr": self.variance_inr,
            "audit_confidence": self.audit_confidence,
            "reasoning_summary": self.reasoning_summary,
            "retries_attempted": self.retries_attempted,
        }
        if self.parse_error:
            res["parse_error"] = self.parse_error
        if self.raw_model_response:
            res["raw_model_response"] = self.raw_model_response
        return res
