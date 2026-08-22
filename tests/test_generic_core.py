"""Unit tests for Phase 3 generic core evaluation abstractions and adapters."""

import unittest
from unittest.mock import MagicMock, patch

from framework.core import (
    Scenario,
    RunTrace,
    to_scenario,
    to_benchmark,
    PythonAgentAdapter,
    HttpAgentAdapter,
    CliAgentAdapter,
    EvaluationSuite,
)
from framework.models import Benchmark, AgentOutput, EvaluationProfile


class TestGenericCoreContracts(unittest.TestCase):

    def setUp(self):
        self.scenario = Scenario(
            id="test-scenario-01",
            name="Test Scenario",
            domain="support_triage",
            description="Testing generic scenario",
            prompt="Process urgent ticket",
            constraints={"sla_hours": 2},
            expected_behavior=["Categorize as P1"],
            evaluation_criteria={"SLA Compliance": ["Must respond within 2h"]},
            pass_criteria=["P1 assigned"],
            failure_conditions=["Missed SLA"],
            profile_name="support-profile",
        )

    def test_scenario_backward_compatibility_properties(self):
        self.assertEqual(self.scenario.benchmark_id, "test-scenario-01")
        self.assertEqual(self.scenario.profile, "support-profile")

    def test_bidirectional_benchmark_scenario_conversion(self):
        benchmark = to_benchmark(self.scenario)
        self.assertIsInstance(benchmark, Benchmark)
        self.assertEqual(benchmark.benchmark_id, "test-scenario-01")
        self.assertEqual(benchmark.profile, "support-profile")

        converted_scenario = to_scenario(benchmark, domain="support_triage")
        self.assertEqual(converted_scenario.id, self.scenario.id)
        self.assertEqual(converted_scenario.domain, "support_triage")
        self.assertEqual(converted_scenario.benchmark_id, "test-scenario-01")

    def test_run_trace_dataclass(self):
        trace = RunTrace(
            trace_id="tr-123",
            scenario_id=self.scenario.id,
            agent_id="support-agent-v1",
            model_name="qwen2.5-72b-instruct",
            started_at_utc="2026-08-22T10:00:00Z",
            finished_at_utc="2026-08-22T10:00:05Z",
            latency_seconds=5.0,
            status="success",
            token_usage={"prompt_tokens": 150, "completion_tokens": 300},
        )
        self.assertEqual(trace.status, "success")
        self.assertEqual(trace.latency_seconds, 5.0)
        self.assertEqual(trace.token_usage["prompt_tokens"], 150)
        self.assertEqual(trace.token_usage["completion_tokens"], 300)

    def test_python_agent_adapter(self):
        dummy_agent = MagicMock()
        dummy_agent.run.return_value = AgentOutput(content="P1 Ticket Escalation Plan")

        adapter = PythonAgentAdapter(dummy_agent)
        output = adapter.run(self.scenario)

        self.assertIsInstance(output, AgentOutput)
        self.assertEqual(output.content, "P1 Ticket Escalation Plan")
        dummy_agent.run.assert_called_once_with("Process urgent ticket")

    @patch("requests.post")
    def test_http_agent_adapter(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "HTTP Agent Output", "metadata": {"status": "ok"}}
        mock_post.return_value = mock_response

        adapter = HttpAgentAdapter("http://localhost:8080/agent")
        output = adapter.run(self.scenario)

        self.assertEqual(output.content, "HTTP Agent Output")
        self.assertEqual(output.metadata["adapter"], "HttpAgentAdapter")

    def test_evaluation_suite_multi_profile_resolution(self):
        prof_travel = EvaluationProfile(name="travel-profile", weights={"Constraint Satisfaction": 1.0})
        prof_support = EvaluationProfile(name="support-profile", weights={"SLA Compliance": 1.0})

        suite = EvaluationSuite(
            suite_id="multi-domain-suite",
            name="Multi Domain Suite",
            domain="general",
            version="1.0.0",
            scenarios=[self.scenario],
            profiles={
                "travel-profile": prof_travel,
                "support-profile": prof_support,
            },
        )

        resolved = suite.get_profile("support-profile")
        self.assertEqual(resolved.name, "support-profile")
        self.assertIn("SLA Compliance", resolved.weights)


if __name__ == "__main__":
    unittest.main()
