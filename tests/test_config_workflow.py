"""Unit tests for configuration-file workflow (evalrun --config)."""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from cli.main import create_parser, run_command
from framework.models import EvaluationResult, DimensionScore


class TestConfigWorkflow(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch("cli.main.BenchmarkRunner")
    @patch("cli.main.OpenAICompatibleLLM")
    def test_run_command_with_json_config(self, mock_llm_class, mock_runner_class):
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        mock_res = EvaluationResult(
            benchmark_id="config-test",
            benchmark_name="Config Test",
            overall_score=95.0,
            dimension_scores=[DimensionScore("Constraint Satisfaction", 95.0, "Great")],
            passed=True,
        )
        mock_runner.run.return_value = mock_res

        # Create config file
        config_path = os.path.join(self.temp_dir, "test_config.json")
        config_data = {
            "scenario": "evals/scenarios/travel-agent/budget-constrained-itinerary.md",
            "agent": "tests.test_cli:DummyAgentClass",
            "model": "qwen2.5-72b",
            "output": self.temp_dir,
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        parser = create_parser()
        args = parser.parse_args(["run", "--config", config_path])

        exit_code = run_command(args)
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "manifest.json")))


if __name__ == "__main__":
    unittest.main()
