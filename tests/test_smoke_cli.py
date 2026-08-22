"""Clean-checkout smoke test for evalrun CLI."""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from cli.main import create_parser, run_command, main
from framework.models import EvaluationResult, DimensionScore


class TestCleanCheckoutSmokeCLI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_cli_help_parser(self):
        parser = create_parser()
        self.assertEqual(parser.prog, "evalrun")

    @patch("cli.main.BenchmarkRunner")
    @patch("cli.main.OpenAICompatibleLLM")
    def test_smoke_evaluation_produces_all_artifacts(self, mock_llm_class, mock_runner_class):
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Mock successful evaluation result
        mock_res = EvaluationResult(
            benchmark_id="budget-constrained-itinerary",
            benchmark_name="Budget Constrained Itinerary",
            overall_score=92.5,
            dimension_scores=[
                DimensionScore("Constraint Satisfaction", 95.0, "Satisfied budget"),
                DimensionScore("Planning Quality", 90.0, "Logical flow"),
            ],
            passed=True,
            agent_metadata={
                "audit_gate_decision": "PASS",
                "run_trace": {"latency_seconds": 1.25, "status": "success"},
            },
        )
        mock_runner.run.return_value = mock_res

        parser = create_parser()
        args = parser.parse_args([
            "run",
            "--scenario", "evals/scenarios/travel-agent/budget-constrained-itinerary.md",
            "--agent", "tests.test_cli:DummyAgentClass",
            "--model", "qwen2.5-smoke",
            "--base-url", "http://localhost:8000/v1",
            "--api-key", "secret-key-to-redact",
            "--output", self.temp_dir,
        ])

        # 1. Execute CLI run command
        exit_code = run_command(args)
        self.assertEqual(exit_code, 0)

        # 2. Verify manifest.json exists and credentials are redacted
        manifest_path = os.path.join(self.temp_dir, "manifest.json")
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        self.assertEqual(manifest_data["target_model"]["api_key"], "[REDACTED]")
        self.assertTrue(manifest_data["overall_passed"])

        # 3. Verify report.html exists
        html_report_path = os.path.join(self.temp_dir, "report.html")
        self.assertTrue(os.path.exists(html_report_path))
        with open(html_report_path, "r", encoding="utf-8") as f:
            html_text = f.read()

        self.assertIn("evalrun Benchmark Evaluation Report", html_text)
        self.assertIn("Budget Constrained Itinerary", html_text)
        self.assertIn("92.50 / 100", html_text)


if __name__ == "__main__":
    unittest.main()
