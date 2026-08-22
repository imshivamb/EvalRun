"""Unit tests for BenchmarkRunner v3 auditor gate integration."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from framework.evaluation.runner import BenchmarkRunner
from framework.models import AgentOutput
from framework.llms.base import BaseLLM, LLMResponse
from agents.auditor.schema import AuditReport, BudgetViolation, FailureCode


class DummyAgent:
    def __init__(self):
        self.llm = MagicMock()
        self.llm.model_name = "test-agent-model"

    def run(self, prompt: str, **kwargs) -> AgentOutput:
        return AgentOutput(
            content="Day 1-14 Itinerary content...",
            metadata={"planner_version": "v2"},
        )


class DummyAuditor:
    def __init__(self, status="PASS", score=95.0, violations=None):
        self.status = status
        self.score = score
        self.violations = violations or []

    def audit(self, scenario_prompt: str, itinerary_content: str, **kwargs) -> AuditReport:
        return AuditReport(
            status=self.status,
            audit_score=self.score,
            violations=self.violations,
            reasoning_summary="Mock auditor run complete.",
        )


class TestRunnerV3AuditorIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_runner_executes_auditor_and_records_metadata(self):
        agent = DummyAgent()
        def mock_generate(messages, **kwargs):
            full_text = " ".join(m.content for m in messages if hasattr(m, 'content')).lower()
            if "factual information extraction" in full_text or "json array of objects" in full_text:
                return LLMResponse(text='```json\n[]\n```')
            return LLMResponse(text='```json\n{"score": 85.0, "reason": "Good plan."}\n```')

        judge_llm = MagicMock()
        judge_llm.model_name = "mock-judge"
        judge_llm.generate.side_effect = mock_generate

        auditor = DummyAuditor(status="BLOCK", score=40.0, violations=[
            BudgetViolation(
                violation_type=FailureCode.MATH_HALLUCINATION,
                description="Unsubstantiated savings claim",
            )
        ])

        runner = BenchmarkRunner(
            agent=agent,
            judge_llm=judge_llm,
            output_dir=self.temp_dir,
            auditor=auditor,
        )

        scenario_path = "evals/scenarios/travel-agent/budget-constrained-itinerary.md"
        if not os.path.exists(scenario_path):
            self.skipTest(f"Scenario path {scenario_path} not found.")

        result = runner.run(scenario_path)

        self.assertIsNotNone(result)
        # Verify JSON report file was created and contains audit_report
        json_files = [f for f in os.listdir(self.temp_dir) if f.endswith(".json")]
        self.assertTrue(len(json_files) > 0)

        import json
        with open(os.path.join(self.temp_dir, json_files[0]), "r") as f:
            data = json.load(f)

        self.assertIn("agent_metadata", data)
        self.assertIn("audit_report", data["agent_metadata"])
        self.assertEqual(data["agent_metadata"]["audit_gate_decision"], "BLOCK")
        self.assertEqual(data["agent_metadata"]["audit_report"]["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
