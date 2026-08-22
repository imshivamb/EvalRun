"""Unit tests for the Independent Budget Auditor."""

import unittest
from unittest.mock import MagicMock

from agents.auditor import IndependentBudgetAuditor, FailureCode, AuditReport, BudgetViolation
from framework.llms.base import BaseLLM, LLMResponse


class MockLLM(BaseLLM):
    def __init__(self, responses=None):
        self.model_name = "mock-auditor-llm"
        self.responses = responses or []
        self.call_count = 0

    def generate(self, messages, **kwargs) -> LLMResponse:
        if self.call_count < len(self.responses):
            text = self.responses[self.call_count]
        else:
            text = self.responses[-1] if self.responses else "{}"
        self.call_count += 1
        return LLMResponse(text=text)


class TestIndependentAuditor(unittest.TestCase):

    def test_auditor_initialization(self):
        llm = MockLLM()
        auditor = IndependentBudgetAuditor(llm)
        self.assertIsNotNone(auditor)

    def test_audit_valid_pass_report(self):
        json_output = """```json
{
  "status": "PASS",
  "audit_score": 95.0,
  "violations": [],
  "total_estimated_spend_inr": 180000.0,
  "budget_limit_inr": 200000.0,
  "variance_inr": 20000.0,
  "audit_confidence": 0.95,
  "reasoning_summary": "All daily budgets and transit items are well within specified INR/JPY limits."
}
```"""
        llm = MockLLM([json_output])
        auditor = IndependentBudgetAuditor(llm)
        report = auditor.audit(
            scenario_prompt="Travel to Japan under ₹2,00,000.",
            itinerary_content="Day 1-14 Itinerary: Pre-paid accommodation ₹80,000...",
            total_budget_inr=200000.0,
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.audit_score, 95.0)
        self.assertEqual(len(report.violations), 0)

    def test_reject_pass_status_with_non_empty_violations(self):
        json_output = """```json
{
  "status": "PASS",
  "audit_score": 90.0,
  "violations": [
    {
      "violation_type": "MATH_HALLUCINATION",
      "description": "Unsubstantiated claim",
      "estimated_discrepancy_inr": 5000.0,
      "affected_days": [1]
    }
  ],
  "total_estimated_spend_inr": 180000.0,
  "budget_limit_inr": 200000.0,
  "variance_inr": 20000.0,
  "audit_confidence": 0.95,
  "reasoning_summary": "Conflicting report"
}
```"""
        llm = MockLLM([json_output, json_output])
        auditor = IndependentBudgetAuditor(llm, max_retries=1)
        report = auditor.audit("Scenario", "Itinerary")

        self.assertFalse(report.passed)
        self.assertEqual(report.status, "BLOCK")
        self.assertIn("Status is 'PASS' but violations array is non-empty", report.parse_error)

    def test_reject_block_status_with_empty_violations(self):
        json_output = """```json
{
  "status": "BLOCK",
  "audit_score": 40.0,
  "violations": [],
  "total_estimated_spend_inr": 180000.0,
  "budget_limit_inr": 200000.0,
  "variance_inr": 20000.0,
  "audit_confidence": 0.95,
  "reasoning_summary": "Empty violations block"
}
```"""
        llm = MockLLM([json_output, json_output])
        auditor = IndependentBudgetAuditor(llm, max_retries=1)
        report = auditor.audit("Scenario", "Itinerary")

        self.assertFalse(report.passed)
        self.assertEqual(report.status, "BLOCK")
        self.assertIn("Status is 'BLOCK' but violations array is empty", report.parse_error)

    def test_reject_unknown_violation_type(self):
        json_output = """```json
{
  "status": "BLOCK",
  "audit_score": 50.0,
  "violations": [
    {
      "violation_type": "UNKNOWN_CUSTOM_ERROR",
      "description": "Invalid type test",
      "estimated_discrepancy_inr": 1000.0,
      "affected_days": [1]
    }
  ],
  "total_estimated_spend_inr": 180000.0,
  "budget_limit_inr": 200000.0,
  "variance_inr": 20000.0,
  "audit_confidence": 0.95,
  "reasoning_summary": "Unknown code test"
}
```"""
        llm = MockLLM([json_output, json_output])
        auditor = IndependentBudgetAuditor(llm, max_retries=1)
        report = auditor.audit("Scenario", "Itinerary")

        self.assertFalse(report.passed)
        self.assertIn("invalid type 'UNKNOWN_CUSTOM_ERROR'", report.parse_error)

    def test_reject_out_of_bounds_score_or_confidence(self):
        json_output = """```json
{
  "status": "PASS",
  "audit_score": 150.0,
  "violations": [],
  "total_estimated_spend_inr": 180000.0,
  "budget_limit_inr": 200000.0,
  "variance_inr": 20000.0,
  "audit_confidence": 1.5,
  "reasoning_summary": "Out of bounds"
}
```"""
        llm = MockLLM([json_output, json_output])
        auditor = IndependentBudgetAuditor(llm, max_retries=1)
        report = auditor.audit("Scenario", "Itinerary")

        self.assertFalse(report.passed)
        self.assertIn("out of bounds", report.parse_error)

    def test_audit_detects_math_hallucination(self):
        json_output = """```json
{
  "status": "BLOCK",
  "audit_score": 40.0,
  "violations": [
    {
      "violation_type": "MATH_HALLUCINATION",
      "description": "Claimed savings of ₹20,000 by taking bus, but price breakdown only totals ₹5,000.",
      "estimated_discrepancy_inr": 15000.0,
      "affected_days": [14, 19]
    }
  ],
  "total_estimated_spend_inr": 215000.0,
  "budget_limit_inr": 200000.0,
  "variance_inr": -15000.0,
  "audit_confidence": 0.90,
  "reasoning_summary": "Unsubstantiated math claims found."
}
```"""
        llm = MockLLM([json_output])
        auditor = IndependentBudgetAuditor(llm)
        report = auditor.audit(
            scenario_prompt="Mid-trip replanning with ₹20,000 savings required.",
            itinerary_content="Day 14: Take bus...",
        )

        self.assertFalse(report.passed)
        self.assertEqual(report.status, "BLOCK")
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].violation_type, FailureCode.MATH_HALLUCINATION)

    def test_audit_detects_all_four_failure_types(self):
        json_output = """```json
{
  "status": "BLOCK",
  "audit_score": 10.0,
  "violations": [
    {
      "violation_type": "MATH_HALLUCINATION",
      "description": "Arbitrary price claims",
      "estimated_discrepancy_inr": 5000.0,
      "affected_days": [2]
    },
    {
      "violation_type": "DAILY_OVERRUN",
      "description": "Day 4 spent ¥8,000 when daily limit is ¥3,000",
      "estimated_discrepancy_inr": 3000.0,
      "affected_days": [4]
    },
    {
      "violation_type": "HIDDEN_OVERHEAD",
      "description": "Omitted Keisei line Narita transfer cost",
      "estimated_discrepancy_inr": 1200.0,
      "affected_days": [28]
    },
    {
      "violation_type": "ANCHOR_MUTATION",
      "description": "Canceled non-refundable Kyoto hostel stay",
      "estimated_discrepancy_inr": 10000.0,
      "affected_days": [15, 16]
    }
  ],
  "total_estimated_spend_inr": 250000.0,
  "budget_limit_inr": 200000.0,
  "variance_inr": -50000.0,
  "audit_confidence": 0.95,
  "reasoning_summary": "Multiple critical financial violations detected."
}
```"""
        llm = MockLLM([json_output])
        auditor = IndependentBudgetAuditor(llm)
        report = auditor.audit("Japan trip", "Itinerary draft")

        self.assertFalse(report.passed)
        self.assertEqual(len(report.violations), 4)
        violation_types = {v.violation_type for v in report.violations}
        self.assertEqual(
            violation_types,
            {
                FailureCode.MATH_HALLUCINATION,
                FailureCode.DAILY_OVERRUN,
                FailureCode.HIDDEN_OVERHEAD,
                FailureCode.ANCHOR_MUTATION,
            },
        )

    def test_malformed_json_retry_handling(self):
        # 1st attempt: malformed text; 2nd attempt: valid JSON
        valid_json = """```json
{
  "status": "PASS",
  "audit_score": 90.0,
  "violations": [],
  "total_estimated_spend_inr": 180000.0,
  "budget_limit_inr": 200000.0,
  "variance_inr": 20000.0,
  "audit_confidence": 0.95,
  "reasoning_summary": "Passed on retry."
}
```"""
        llm = MockLLM(["Not a json output", valid_json])
        auditor = IndependentBudgetAuditor(llm, max_retries=1)
        report = auditor.audit("Scenario", "Itinerary")

        self.assertTrue(report.passed)
        self.assertEqual(llm.call_count, 2)
        self.assertEqual(report.retries_attempted, 1)

    def test_exhausted_retries_returns_block_with_error_metadata(self):
        llm = MockLLM(["Broken text 1", "Broken text 2"])
        auditor = IndependentBudgetAuditor(llm, max_retries=1)
        report = auditor.audit("Scenario", "Itinerary")

        self.assertFalse(report.passed)
        self.assertEqual(report.status, "BLOCK")
        self.assertEqual(report.violations[0].violation_type, FailureCode.MATH_HALLUCINATION)
        self.assertIsNotNone(report.parse_error)
        self.assertEqual(report.retries_attempted, 2)
        self.assertEqual(report.raw_model_response, "Broken text 2")


if __name__ == "__main__":
    unittest.main()
