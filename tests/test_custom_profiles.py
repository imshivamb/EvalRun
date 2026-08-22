"""Unit tests for custom evaluation profiles registry."""

import json
import os
import shutil
import tempfile
import unittest

from framework.profiles.registry import register_profile, get_custom_profile, load_profile_from_file
from framework.models import EvaluationProfile, EvaluationResult


class TestCustomProfilesRegistry(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_register_and_get_custom_profile(self):
        profile = EvaluationProfile(
            name="Custom Test Profile",
            weights={"Planning Quality": 2.0},
            pass_threshold=80.0,
        )
        register_profile("custom-test-prof", profile)
        retrieved = get_custom_profile("custom-test-prof")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Custom Test Profile")
        self.assertEqual(retrieved.pass_threshold, 80.0)

    def test_load_profile_from_json_file(self):
        file_path = os.path.join(self.temp_dir, "custom_profile.json")
        json_data = {
            "profile_id": "file-profile-001",
            "name": "File Profile",
            "pass_threshold": 85.0,
            "dimension_weights": [
                {"dimension": "Constraint Satisfaction", "weight": 1.5, "description": "High weight constraint"}
            ],
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f)

        profile = load_profile_from_file(file_path)
        self.assertEqual(profile.name, "File Profile")
        self.assertEqual(profile.pass_threshold, 85.0)
        self.assertEqual(profile.weights["Constraint Satisfaction"], 1.5)

    def test_register_and_get_evaluator_plugin(self):
        from framework.profiles.registry import register_evaluator_plugin, get_evaluator_plugin
        from framework.evaluation.base import BaseEvaluator
        from framework.models import DimensionScore

        class CustomDummyEvaluator(BaseEvaluator):
            def evaluate(self, benchmark, output):
                return DimensionScore("Custom Safety", 100.0, "Fully safe")

        evaluator = CustomDummyEvaluator()
        register_evaluator_plugin("Custom Safety", evaluator)

        retrieved = get_evaluator_plugin("Custom Safety")
        self.assertEqual(retrieved, evaluator)

    def test_runner_resolves_custom_profile_and_errors_on_unknown(self):
        from unittest.mock import MagicMock
        from framework.evaluation.runner import BenchmarkRunner
        from framework.models import Benchmark

        agent_mock = MagicMock()
        judge_mock = MagicMock()
        judge_mock.model_name = "test-judge-model"
        runner = BenchmarkRunner(agent_mock, judge_mock)

        # Register custom profile
        custom_prof = EvaluationProfile(name="My Custom Profile", weights={"Constraint Satisfaction": 1.0}, pass_threshold=80.0)
        register_profile("my-custom-profile", custom_prof)

        # Test dynamic profile resolution via parse_benchmark mock
        with unittest.mock.patch("framework.evaluation.runner.parse_benchmark") as mock_parse:
            real_bm = Benchmark(
                benchmark_id="test-custom-bm",
                name="Test Custom Benchmark",
                description="Desc",
                prompt="Prompt",
                constraints={},
                expected_behavior=[],
                evaluation_criteria={"Constraint Satisfaction": ["Pass constraint"]},
                pass_criteria=[],
                failure_conditions=[],
                notes=[],
                profile="my-custom-profile",
            )
            mock_parse.return_value = real_bm

            from framework.models import AgentOutput
            agent_mock.run.return_value = AgentOutput(content="Output", metadata={})
            real_result = EvaluationResult(
                benchmark_id="test-custom-bm",
                benchmark_name="Test Custom Benchmark",
                overall_score=90.0,
                dimension_scores=[],
                passed=True,
            )
            runner.engine = MagicMock()
            runner.engine.evaluate.return_value = real_result

            with unittest.mock.patch.object(runner, "_save_execution_files"):
                res = runner.run("dummy_path.md")
                runner.engine.evaluate.assert_called_once()
                resolved_prof = runner.engine.evaluate.call_args[0][2]
                self.assertEqual(resolved_prof.name, "My Custom Profile")

        # Test unknown profile raises ValueError
        with unittest.mock.patch("framework.evaluation.runner.parse_benchmark") as mock_parse:
            mock_bm = MagicMock()
            mock_bm.profile = "unknown-nonexistent-profile"
            mock_parse.return_value = mock_bm

            with self.assertRaises(ValueError) as ctx:
                runner.run("dummy_path.md")
            self.assertIn("unknown-nonexistent-profile", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
