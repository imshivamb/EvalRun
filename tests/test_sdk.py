"""Unit tests for public Python SDK API (framework/sdk.py)."""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from framework import evaluate, compare
from framework.models import EvaluationResult, DimensionScore


class TestPythonSDK(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch("framework.sdk.BenchmarkRunner")
    @patch("framework.sdk.OpenAICompatibleLLM")
    def test_evaluate_sdk_function(self, mock_llm_class, mock_runner_class):
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        mock_res = EvaluationResult(
            benchmark_id="sdk-test-scenario",
            benchmark_name="SDK Test Scenario",
            overall_score=88.0,
            dimension_scores=[DimensionScore("Constraint Satisfaction", 88.0, "Pass")],
            passed=True,
        )
        mock_runner.run.return_value = mock_res

        results = evaluate(
            scenario="evals/scenarios/travel-agent/budget-constrained-itinerary.md",
            agent="tests.test_cli:DummyAgentClass",
            model="qwen2.5-72b",
            output_dir=self.temp_dir,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].overall_score, 88.0)
        self.assertTrue(results[0].passed)

    def test_compare_sdk_function(self):
        # Create baseline manifest
        baseline_dir = os.path.join(self.temp_dir, "baseline_dir")
        os.makedirs(baseline_dir, exist_ok=True)
        manifest_data = {
            "run_id": "sdk-base-001",
            "scenarios": [
                {
                    "scenario_id": "sdk-test-scenario",
                    "scenario_name": "SDK Test Scenario",
                    "overall_score": 90.0,
                    "passed": True,
                    "audit_gate_decision": "PASS",
                }
            ],
        }
        with open(os.path.join(baseline_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        cand_results = [
            EvaluationResult(
                benchmark_id="sdk-test-scenario",
                benchmark_name="SDK Test Scenario",
                overall_score=92.0,
                dimension_scores=[],
                passed=True,
            )
        ]

        report = compare(
            candidate_results=cand_results,
            baseline=baseline_dir,
            max_regression=5.0,
        )

        self.assertFalse(report.regression_detected)
        self.assertFalse(report.release_blocked)

    @patch("framework.sdk.BenchmarkRunner")
    @patch("framework.sdk.OpenAICompatibleLLM")
    def test_suite_execution_failure_is_not_reported_as_pass(self, mock_llm_class, mock_runner_class):
        suite_dir = os.path.join(self.temp_dir, "suite")
        os.makedirs(suite_dir, exist_ok=True)
        scenario_path = os.path.join(suite_dir, "broken.md")
        with open(scenario_path, "w", encoding="utf-8") as f:
            f.write("placeholder")

        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        mock_runner.run.side_effect = RuntimeError("model endpoint unavailable")

        results = evaluate(
            scenario=suite_dir,
            agent="tests.test_cli:DummyAgentClass",
            model="test-model",
            output_dir=self.temp_dir,
        )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].passed)
        self.assertEqual(results[0].agent_metadata["execution_error"], "model endpoint unavailable")

        with open(os.path.join(self.temp_dir, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["total_scenarios"], 1)
        self.assertEqual(manifest["successful_scenarios"], 0)
        self.assertEqual(len(manifest["execution_errors"]), 1)
        self.assertFalse(manifest["overall_passed"])


if __name__ == "__main__":
    unittest.main()
