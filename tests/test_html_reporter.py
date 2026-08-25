"""Unit tests for HTML report rendering (cli/html_reporter.py)."""

import os
import shutil
import tempfile
import unittest

from cli.html_reporter import generate_html_report
from framework.models import EvaluationResult, DimensionScore


class TestHTMLReporter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_report_generation_all_passed(self):
        results = [
            EvaluationResult(
                benchmark_id="test-scenario-001",
                benchmark_name="Test Scenario 001",
                overall_score=90.0,
                dimension_scores=[DimensionScore("Constraint Satisfaction", 90.0, "Pass")],
                passed=True,
                agent_metadata={"audit_gate_decision": "PASS", "raw_content": "Valid agent response"},
            )
        ]
        manifest = {
            "run_id": "test-run-001",
            "target_agent_spec": "agents.travel:TravelPlanningAgent",
            "target_model": {"model_name": "qwen2.5-72b-instruct"},
            "judge_model": {"model_name": "qwen2.5-72b-instruct"},
            "timestamp_utc": "2026-08-25T15:00:00Z",
        }

        report_path = generate_html_report(results, manifest, self.temp_dir)
        self.assertTrue(os.path.exists(report_path))

        with open(report_path, "r", encoding="utf-8") as f:
            html_text = f.read()

        self.assertIn("RELEASE APPROVED", html_text)
        self.assertIn("Test Scenario 001", html_text)
        self.assertIn("Evaluator: PASS", html_text)
        self.assertIn("Auditor: PASS", html_text)

    def test_report_generation_failed_scenario_remediation(self):
        results = [
            EvaluationResult(
                benchmark_id="failing-scenario",
                benchmark_name="Failing Scenario",
                overall_score=40.0,
                dimension_scores=[DimensionScore("Constraint Satisfaction", 40.0, "Exceeded budget")],
                passed=False,
                agent_metadata={"audit_gate_decision": "PASS", "scenario_path": "evals/scenarios/failing.md"},
            )
        ]
        manifest = {
            "run_id": "test-run-002",
            "target_agent_spec": "agents.travel:TravelPlanningAgent",
            "target_model": {"model_name": "gpt-4o"},
            "judge_model": {"model_name": "gpt-4o"},
        }

        report_path = generate_html_report(results, manifest, self.temp_dir)
        with open(report_path, "r", encoding="utf-8") as f:
            html_text = f.read()

        self.assertIn("RELEASE BLOCKED", html_text)
        self.assertIn("1 evaluator failure(s)", html_text)
        self.assertIn("Remediation CLI Command:", html_text)
        self.assertIn("evalrun run --scenario evals/scenarios/failing.md", html_text)

    def test_report_generation_zero_scenarios(self):
        report_path = generate_html_report([], {"run_id": "empty-run"}, self.temp_dir)
        with open(report_path, "r", encoding="utf-8") as f:
            html_text = f.read()

        self.assertIn("RELEASE BLOCKED — ZERO SCENARIOS EXECUTED", html_text)

    def test_report_generation_execution_error(self):
        results = [
            EvaluationResult(
                benchmark_id="execution-error:broken",
                benchmark_name="Broken Scenario",
                overall_score=0.0,
                dimension_scores=[],
                passed=False,
                agent_metadata={"execution_error": "Connection timed out to model endpoint"},
            )
        ]
        manifest = {"run_id": "test-error-run"}

        report_path = generate_html_report(results, manifest, self.temp_dir)
        with open(report_path, "r", encoding="utf-8") as f:
            html_text = f.read()

        self.assertIn("RELEASE BLOCKED", html_text)
        self.assertIn("1 execution error(s)", html_text)
        self.assertIn("Execution Failure Details", html_text)
        self.assertIn("Connection timed out to model endpoint", html_text)


if __name__ == "__main__":
    unittest.main()
