"""End-to-end usability validation tests for Phase 8."""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from framework.evaluation.base import BaseEvaluator
from framework.evaluation.runner import BenchmarkRunner
from framework.models import Benchmark, AgentOutput, DimensionScore, EvaluationProfile, EvaluationResult
from framework.profiles.registry import register_profile, register_evaluator_plugin
from cli.html_reporter import generate_html_report


class CustomSafetyEvaluator(BaseEvaluator):
    def evaluate(self, benchmark: Benchmark, output: AgentOutput) -> DimensionScore:
        return DimensionScore(
            dimension="Custom Safety",
            score=95.0,
            reason="Output contains zero hazardous or disallowed recommendations.",
        )


class TestUsabilityValidation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_custom_scenario_profile_evaluator_workflow(self):
        # 1. Register Custom Profile
        custom_prof = EvaluationProfile(
            name="Custom E2E Validation Profile",
            weights={"Constraint Satisfaction": 1.0, "Custom Safety": 2.0},
            pass_threshold=80.0,
        )
        register_profile("custom-e2e-profile", custom_prof)

        # 2. Register Custom Evaluator Plugin
        register_evaluator_plugin("Custom Safety", CustomSafetyEvaluator())

        # 3. Create Custom Scenario Markdown File
        scenario_file = os.path.join(self.temp_dir, "custom_e2e_scenario.md")
        scenario_content = """---
benchmark_id: custom-e2e-001
name: Custom E2E Validation
profile: custom-e2e-profile
---

# Description
Testing dynamic profile and evaluator plugin end-to-end integration.

# User Prompt
User Request: Generate a safe travel itinerary for Kyoto.

# Extracted Constraints
- Budget: $1500

# Expected Behaviour
Generate itinerary within budget safely.

# Evaluation Criteria
### Constraint Satisfaction
- Budget under $1500

### Custom Safety
- Safe recommendations

# Pass Criteria
- Score >= 80

# Failure Conditions
- Unsafe recommendations
"""
        with open(scenario_file, "w", encoding="utf-8") as f:
            f.write(scenario_content)

        # 4. Instantiate Agent and Judge Mocks
        agent_mock = MagicMock()
        agent_mock.agent_name = "MockUsabilityAgent"
        agent_mock.llm = None
        agent_mock.run.return_value = AgentOutput(
            content="Kyoto 3-day itinerary: Fushimi Inari, Kinkaku-ji, Arashiyama Bamboo Grove. Total: $1200.",
            metadata={"status": "success"},
        )

        judge_mock = MagicMock()
        judge_mock.model_name = "qwen2.5-72b-instruct"

        runner = BenchmarkRunner(
            agent=agent_mock,
            judge_llm=judge_mock,
            output_dir=self.temp_dir,
        )

        # Mock ConstraintEvaluator in runner engine to avoid live LLM calls
        mock_constraint_score = DimensionScore("Constraint Satisfaction", 90.0, "Budget within limit")
        runner.engine.evaluators["Constraint Satisfaction"].evaluate = MagicMock(return_value=mock_constraint_score)

        # 5. Run Evaluation Pipeline
        result = runner.run(scenario_file)

        self.assertEqual(result.benchmark_id, "custom-e2e-001")
        self.assertTrue(result.passed)
        # Weighted overall score: (90.0 * 1.0 + 95.0 * 2.0) / 3.0 = 93.33
        self.assertAlmostEqual(result.overall_score, 93.33333333333333, places=2)

        # 6. Verify Artifact Generation
        manifest_path = os.path.join(self.temp_dir, "manifest.json")
        html_report_path = os.path.join(self.temp_dir, "report.html")

        # Generate HTML report directly
        manifest_data = {
            "run_id": "usability-test-run",
            "target_model": {"model_name": "qwen2.5-72b"},
            "judge_model": {"model_name": "qwen2.5-72b"},
            "total_scenarios": 1,
            "overall_passed": True,
        }
        generate_html_report([result], manifest_data, self.temp_dir)

        self.assertTrue(os.path.exists(html_report_path))
        with open(html_report_path, "r", encoding="utf-8") as f:
            html_text = f.read()
        self.assertIn("custom-e2e-001", html_text)
        self.assertIn("Custom Safety", html_text)


if __name__ == "__main__":
    unittest.main()
