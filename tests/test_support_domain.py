"""Smoke tests for the minimal support-triage second domain."""

import unittest
from unittest.mock import Mock

from agents.support import SupportTriageAgent
from framework import parse_benchmark
from framework.llms.base import LLMResponse
from framework.profiles import PROFILE_REGISTRY, SUPPORT_TRIAGE_PROFILE


SCENARIO = "evals/scenarios/support-triage/urgent-ticket-escalation.md"


class TestSupportDomain(unittest.TestCase):
    def test_scenario_and_profile_are_registered(self):
        benchmark = parse_benchmark(SCENARIO)
        self.assertEqual(benchmark.profile, SUPPORT_TRIAGE_PROFILE.name)
        self.assertIn(SUPPORT_TRIAGE_PROFILE.name, PROFILE_REGISTRY)
        self.assertEqual(set(SUPPORT_TRIAGE_PROFILE.weights), set(benchmark.evaluation_criteria))

    def test_agent_uses_common_agent_output_contract(self):
        llm = Mock()
        llm.generate.return_value = LLMResponse(text="P1; page Payments on-call.")
        output = SupportTriageAgent(llm).run("triage this ticket")
        self.assertEqual(output.content, "P1; page Payments on-call.")
        self.assertEqual(output.metadata["domain"], "support-triage")
        self.assertEqual(llm.generate.call_args.args[0][0].role, "system")


if __name__ == "__main__":
    unittest.main()
