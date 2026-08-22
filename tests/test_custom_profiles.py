"""Unit tests for custom evaluation profiles registry."""

import json
import os
import shutil
import tempfile
import unittest

from framework.profiles.registry import register_profile, get_custom_profile, load_profile_from_file
from framework.models import EvaluationProfile


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


if __name__ == "__main__":
    unittest.main()
