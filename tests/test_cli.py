"""Unit tests for evalrun CLI, dynamic agent resolution, and exit codes."""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from cli.formatter import redact_credentials, format_terminal_summary
from cli.main import create_parser, run_command, main
from cli.resolver import resolve_agent
from framework.llms.base import LLMResponse
from framework.models import AgentOutput, EvaluationResult, DimensionScore


class DummyAgentClass:
    def __init__(self, llm=None):
        self.llm = llm

    def run(self, prompt, **kwargs):
        return AgentOutput(content="Dummy CLI agent output")


def dummy_agent_factory(llm=None):
    return DummyAgentClass(llm=llm)


class TestCLIFunctionality(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_resolve_agent_class_and_factory(self):
        mock_llm = MagicMock()

        # Resolve class
        agent1 = resolve_agent("tests.test_cli:DummyAgentClass", mock_llm)
        self.assertEqual(type(agent1).__name__, "DummyAgentClass")
        self.assertEqual(agent1.llm, mock_llm)

        # Resolve factory
        agent2 = resolve_agent("tests.test_cli:dummy_agent_factory", mock_llm)
        self.assertEqual(type(agent2).__name__, "DummyAgentClass")
        self.assertEqual(agent2.llm, mock_llm)

        # Malformed specifier
        with self.assertRaises(ValueError):
            resolve_agent("invalid_specifier_without_colon", mock_llm)

    def test_redact_credentials(self):
        raw_manifest = {
            "api_key": "sk-secret-key-12345",
            "model": {"name": "gpt-4o", "api_key": "secret-nvapi"},
            "nested": [{"authorization": "Bearer token123"}],
            "safe_param": "http://localhost:8000/v1",
        }

        redacted = redact_credentials(raw_manifest)
        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redacted["model"]["api_key"], "[REDACTED]")
        self.assertEqual(redacted["nested"][0]["authorization"], "[REDACTED]")
        self.assertEqual(redacted["safe_param"], "http://localhost:8000/v1")

    def test_cli_argument_parsing(self):
        parser = create_parser()

        # Test single scenario parsing
        args = parser.parse_args([
            "run",
            "--scenario", "evals/scenarios/travel-agent/budget-constrained-itinerary.md",
            "--agent", "tests.test_cli:DummyAgentClass",
            "--model", "qwen2.5-72b",
            "--base-url", "http://localhost:8000/v1",
            "--output", self.temp_dir,
        ])
        self.assertEqual(args.scenario, "evals/scenarios/travel-agent/budget-constrained-itinerary.md")
        self.assertEqual(args.agent, "tests.test_cli:DummyAgentClass")
        self.assertEqual(args.model, "qwen2.5-72b")

    @patch("cli.main.BenchmarkRunner")
    @patch("cli.main.OpenAICompatibleLLM")
    def test_run_command_end_to_end_success(self, mock_llm_class, mock_runner_class):
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Mock successful evaluation result
        mock_res = EvaluationResult(
            benchmark_id="test-b",
            benchmark_name="Test Benchmark",
            overall_score=85.0,
            dimension_scores=[DimensionScore("Constraint Satisfaction", 85.0, "Good")],
            passed=True,
        )
        mock_runner.run.return_value = mock_res

        parser = create_parser()
        args = parser.parse_args([
            "run",
            "--scenario", "evals/scenarios/travel-agent/budget-constrained-itinerary.md",
            "--agent", "tests.test_cli:DummyAgentClass",
            "--model", "qwen2.5-72b",
            "--api-key", "my-secret-key",
            "--output", self.temp_dir,
        ])

        exit_code = run_command(args)
        self.assertEqual(exit_code, 0)

        # Check manifest was created and credentials redacted
        manifest_path = os.path.join(self.temp_dir, "manifest.json")
        self.assertTrue(os.path.exists(manifest_path))

        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)

        self.assertEqual(manifest_data["target_model"]["api_key"], "[REDACTED]")
        self.assertEqual(manifest_data["total_scenarios"], 1)

    @patch("cli.main.BenchmarkRunner")
    @patch("cli.main.OpenAICompatibleLLM")
    def test_auditor_block_triggers_exit_code_1(self, mock_llm_class, mock_runner_class):
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Mock result where evaluator score is 100 but auditor gate blocked
        mock_res = EvaluationResult(
            benchmark_id="test-b",
            benchmark_name="Test Benchmark",
            overall_score=100.0,
            dimension_scores=[DimensionScore("Planning Quality", 100.0, "Great")],
            passed=True,
            agent_metadata={"audit_gate_decision": "BLOCK"},
        )
        mock_runner.run.return_value = mock_res

        parser = create_parser()
        args = parser.parse_args([
            "run",
            "--scenario", "evals/scenarios/travel-agent/budget-constrained-itinerary.md",
            "--agent", "tests.test_cli:DummyAgentClass",
            "--model", "qwen2.5-72b",
            "--output", self.temp_dir,
        ])

        exit_code = run_command(args)
        self.assertEqual(exit_code, 1)

        summary = format_terminal_summary([mock_res], {"output_dir": self.temp_dir})
        self.assertIn("BLOCK", summary)
        self.assertIn("EVALUATION OR GATE FAILURE (Exit Code: 1)", summary)

    @patch("cli.main.BenchmarkRunner")
    @patch("cli.main.OpenAICompatibleLLM")
    def test_baseline_regression_gate_triggers_exit_code_1(self, mock_llm_class, mock_runner_class):
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Candidate result with dropped score (75.0 vs 90.0 baseline)
        mock_res = EvaluationResult(
            benchmark_id="budget-constrained-itinerary",
            benchmark_name="Budget Constrained Itinerary",
            overall_score=75.0,
            dimension_scores=[DimensionScore("Constraint Satisfaction", 75.0, "Score dropped")],
            passed=True,
            agent_metadata={"audit_gate_decision": "PASS"},
        )
        mock_runner.run.return_value = mock_res

        # Create baseline directory & manifest.json
        baseline_dir = os.path.join(self.temp_dir, "baseline_run")
        os.makedirs(baseline_dir, exist_ok=True)
        baseline_manifest = {
            "run_id": "baseline-001",
            "scenarios": [
                {
                    "scenario_id": "budget-constrained-itinerary",
                    "scenario_name": "Budget Constrained Itinerary",
                    "overall_score": 90.0,
                    "passed": True,
                    "audit_gate_decision": "PASS",
                    "dimension_scores": {"Constraint Satisfaction": 90.0},
                }
            ],
        }
        with open(os.path.join(baseline_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(baseline_manifest, f)

        parser = create_parser()
        args = parser.parse_args([
            "run",
            "--scenario", "evals/scenarios/travel-agent/budget-constrained-itinerary.md",
            "--agent", "tests.test_cli:DummyAgentClass",
            "--model", "qwen2.5-72b",
            "--baseline", baseline_dir,
            "--max-regression", "5.0",
            "--output", self.temp_dir,
        ])

        exit_code = run_command(args)
        self.assertEqual(exit_code, 1)

        reg_report_path = os.path.join(self.temp_dir, "regression_report.json")
        self.assertTrue(os.path.exists(reg_report_path))
        with open(reg_report_path, "r", encoding="utf-8") as f:
            reg_data = json.load(f)

        self.assertTrue(reg_data["regression_detected"])
        self.assertTrue(reg_data["release_blocked"])

    def test_run_command_missing_file_returns_exit_code_2(self):
        parser = create_parser()
        args = parser.parse_args([
            "run",
            "--scenario", "non_existent_file.md",
            "--agent", "tests.test_cli:DummyAgentClass",
            "--model", "qwen2.5-72b",
            "--output", self.temp_dir,
        ])

        exit_code = run_command(args)
        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
