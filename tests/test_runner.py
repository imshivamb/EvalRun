import unittest
import os
import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch
from framework.models import AgentOutput, Benchmark, EvaluationResult, DimensionScore
from framework.evaluation.runner import BenchmarkRunner
from framework.llms import MockLLM


class MockAgent:
    """Mock agent for testing runner."""
    def run(self, prompt: str) -> AgentOutput:
        return AgentOutput(content="Test itinerary planned by agent.")


class TestRunner(unittest.TestCase):
    """Tests the BenchmarkRunner class."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.agent = MockAgent()
        self.judge_llm = MockLLM(responses=[])

        # Create temporary verifier database
        self.db_path = os.path.join(self.temp_dir, "db.json")
        with open(self.db_path, "w") as f:
            f.write("{}")

        # Mock the Benchmark instance
        self.benchmark = Benchmark(
            benchmark_id="test-gathering",
            name="Test Gathering Scenario",
            description="Desc",
            prompt="Prompt",
            constraints={},
            expected_behavior=[],
            evaluation_criteria={
                "Constraint Satisfaction": [],
                "Planning Quality": [],
                "Information Accuracy": [],
                "Personalization": [],
                "Adaptability": [],
            },
            pass_criteria=[],
            failure_conditions=[],
            notes=[],
            profile="travel-information-gathering-uncertainty",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch("framework.evaluation.runner.parse_benchmark")
    def test_runner_executes_pipeline(self, mock_parse):
        mock_parse.return_value = self.benchmark

        runner = BenchmarkRunner(
            agent=self.agent,
            judge_llm=self.judge_llm,
            local_verifier_path=self.db_path,
            output_dir=self.temp_dir,
        )

        # Mock engine.evaluate instead of mock calling actual LLM judges for unit tests
        mock_evaluate_result = EvaluationResult(
            benchmark_id=self.benchmark.benchmark_id,
            benchmark_name=self.benchmark.name,
            overall_score=85.0,
            dimension_scores=[
                DimensionScore(dimension="Constraint Satisfaction", score=90.0, reason="ok"),
                DimensionScore(dimension="Planning Quality", score=80.0, reason="ok"),
                DimensionScore(dimension="Information Accuracy", score=85.0, reason="ok"),
                DimensionScore(dimension="Personalization", score=75.0, reason="ok"),
                DimensionScore(dimension="Adaptability", score=80.0, reason="ok"),
            ],
            passed=True,
        )
        runner.engine.evaluate = MagicMock(return_value=mock_evaluate_result)

        # Run single benchmark
        result = runner.run("dummy_path.md")

        # Verify results
        self.assertEqual(result.overall_score, 85.0)
        self.assertTrue(result.passed)

        # Check saved report files
        expected_prefix = "mockagent_test-gathering"
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, f"{expected_prefix}_itinerary.md")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, f"{expected_prefix}_report.json")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, f"{expected_prefix}_report.md")))

        # Check JSON contents
        with open(os.path.join(self.temp_dir, f"{expected_prefix}_report.json"), "r") as f:
            data = json.load(f)
            self.assertEqual(data["overall_score"], 85.0)
            self.assertTrue(data["passed"])
            self.assertEqual(data["profile"], "travel-information-gathering-uncertainty")

    @patch("framework.evaluation.runner.parse_benchmark")
    def test_runner_run_directory(self, mock_parse):
        mock_parse.return_value = self.benchmark

        # Create dummy markdown file
        dummy_bench = os.path.join(self.temp_dir, "test_bench.md")
        with open(dummy_bench, "w") as f:
            f.write("# Dummy Benchmark")

        runner = BenchmarkRunner(
            agent=self.agent,
            judge_llm=self.judge_llm,
            local_verifier_path=self.db_path,
            output_dir=self.temp_dir,
        )

        mock_evaluate_result = EvaluationResult(
            benchmark_id=self.benchmark.benchmark_id,
            benchmark_name=self.benchmark.name,
            overall_score=90.0,
            dimension_scores=[
                DimensionScore(dimension="Constraint Satisfaction", score=90.0, reason="ok"),
                DimensionScore(dimension="Planning Quality", score=90.0, reason="ok"),
                DimensionScore(dimension="Information Accuracy", score=90.0, reason="ok"),
                DimensionScore(dimension="Personalization", score=90.0, reason="ok"),
                DimensionScore(dimension="Adaptability", score=90.0, reason="ok"),
            ],
            passed=True,
        )
        runner.engine.evaluate = MagicMock(return_value=mock_evaluate_result)

        results = runner.run_directory(self.temp_dir)
        self.assertIn("test-gathering", results)
        self.assertEqual(results["test-gathering"].overall_score, 90.0)


if __name__ == "__main__":
    unittest.main()
