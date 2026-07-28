"""Controlled tests for MCP feedback in the travel replanning loop."""

import unittest

from agents.reflection import ReflectionAgent
from agents.travel import CurrentTripState, TravelPlanningAgent, TravelSessionMemory
from framework.llms import MockLLM


class RecordingMockLLM(MockLLM):
    """Captures prompts so the test can inspect the final revision context."""

    def __init__(self, responses):
        super().__init__(responses)
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        return super().generate(messages)


class StubValidationClient:
    """A deterministic stand-in for the MCP transport layer."""

    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "get_locked_constraints":
            return {"immutable_booking_ids": ["kyoto-hostel", "narita-return-flight"]}
        if name == "validate_revision":
            return {
                "valid": False,
                "violations": ["Locked booking 'kyoto-hostel' must be preserved, not 'move'."],
            }
        if name == "calculate_savings":
            return {
                "target_met": False,
                "remaining_gap_inr": 8000.0,
            }
        raise AssertionError(f"Unexpected tool call: {name}")


class PassingValidationClient(StubValidationClient):
    """Returns a passing deterministic check for the reflection-approved path."""

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "get_locked_constraints":
            return {"immutable_booking_ids": ["kyoto-hostel", "narita-return-flight"]}
        if name == "validate_revision":
            return {"valid": True, "violations": []}
        if name == "calculate_savings":
            return {"target_met": True, "remaining_gap_inr": 0.0}
        raise AssertionError(f"Unexpected tool call: {name}")


class TestMCPAgentIntegration(unittest.TestCase):
    scenario_id = "travel-mid-trip-replanning"

    def _session_memory(self):
        return TravelSessionMemory(
            session_id="mcp-test",
            state=CurrentTripState(current_day=12),
        )

    def test_mcp_failures_are_included_in_final_revision_prompt(self):
        planner_llm = RecordingMockLLM(
            [
                "Initial draft itinerary.",
                """{
                  "scenario_id": "travel-mid-trip-replanning",
                  "changed_days": [13, 15, 19],
                  "booking_actions": [
                    {"booking_id": "kyoto-hostel", "action": "move"},
                    {"booking_id": "narita-return-flight", "action": "preserve"}
                  ],
                  "savings_items": [{"label": "Cheaper food", "amount_inr": 12000}]
                }""",
                "Final revised itinerary preserving Kyoto.",
                """{
                  "scenario_id": "travel-mid-trip-replanning",
                  "changed_days": [13, 19, 22],
                  "booking_actions": [
                    {"booking_id": "kyoto-hostel", "action": "preserve"},
                    {"booking_id": "narita-return-flight", "action": "preserve"}
                  ],
                  "savings_items": [{"label": "Cheaper food", "amount_inr": 20000}]
                }""",
            ]
        )
        reflection_agent = ReflectionAgent(
            MockLLM("Critique: reduce costs but preserve all locked bookings.")
        )
        validation_client = StubValidationClient()
        agent = TravelPlanningAgent(
            llm=planner_llm,
            reflection_agent=reflection_agent,
            validation_client=validation_client,
        )

        output = agent.run(
            "I am currently on Day 12 and need replanning after a disruption.",
            session_memory=self._session_memory(),
            validation_scenario_id=self.scenario_id,
        )

        self.assertEqual(output.content, "Final revised itinerary preserving Kyoto.")
        self.assertEqual(
            [name for name, _ in validation_client.calls],
            [
                "get_locked_constraints", "validate_revision", "calculate_savings",
                "get_locked_constraints", "validate_revision", "calculate_savings",
            ],
        )
        final_revision_prompt = planner_llm.calls[2][1].content
        self.assertIn("DETERMINISTIC MCP VALIDATION REPORT", final_revision_prompt)
        self.assertIn("kyoto-hostel", final_revision_prompt)
        self.assertIn("remaining_gap_inr", final_revision_prompt)
        self.assertEqual(output.metadata["mcp_validation"]["initial"]["status"], "completed")
        self.assertFalse(output.metadata["mcp_validation"]["initial"]["revision_check"]["valid"])
        self.assertEqual(output.metadata["mcp_validation"]["final"]["status"], "completed")

    def test_malformed_summary_is_reported_instead_of_silently_passing(self):
        planner_llm = RecordingMockLLM(
            [
                "Initial draft itinerary.",
                "This is not valid JSON.",
                "Final revised itinerary.",
                "This is not valid JSON either.",
            ]
        )
        agent = TravelPlanningAgent(
            llm=planner_llm,
            reflection_agent=ReflectionAgent(MockLLM("Critique: revise Day 13.")),
            validation_client=StubValidationClient(),
        )

        output = agent.run(
            "I am currently on Day 12 and need replanning after a disruption.",
            session_memory=self._session_memory(),
            validation_scenario_id=self.scenario_id,
        )

        self.assertEqual(output.metadata["mcp_validation"]["initial"]["status"], "unavailable")
        self.assertEqual(output.metadata["mcp_validation"]["final"]["status"], "unavailable")
        final_revision_prompt = planner_llm.calls[2][1].content
        self.assertIn('"status": "unavailable"', final_revision_prompt)
        self.assertIn("This is not valid JSON.", final_revision_prompt)

    def test_reflection_approval_still_runs_mcp_validation(self):
        planner_llm = RecordingMockLLM(
            [
                "Approved initial itinerary.",
                """{
                  "scenario_id": "travel-mid-trip-replanning",
                  "changed_days": [13, 19, 22],
                  "booking_actions": [
                    {"booking_id": "kyoto-hostel", "action": "preserve"},
                    {"booking_id": "narita-return-flight", "action": "preserve"}
                  ],
                  "savings_items": [{"label": "Budget changes", "amount_inr": 20000}]
                }""",
            ]
        )
        validation_client = PassingValidationClient()
        agent = TravelPlanningAgent(
            llm=planner_llm,
            reflection_agent=ReflectionAgent(MockLLM("ITINERARY APPROVED")),
            validation_client=validation_client,
        )

        output = agent.run(
            "I am currently on Day 12 and need replanning after a disruption.",
            session_memory=self._session_memory(),
            validation_scenario_id=self.scenario_id,
        )

        self.assertEqual(output.content, "Approved initial itinerary.")
        self.assertTrue(output.metadata["reflection_approved"])
        self.assertFalse(output.metadata["revision_triggered"])
        self.assertEqual(output.metadata["mcp_validation"]["initial"]["status"], "completed")
        self.assertIsNone(output.metadata["mcp_validation"]["final"])
        self.assertEqual(
            [name for name, _ in validation_client.calls],
            ["get_locked_constraints", "validate_revision", "calculate_savings"],
        )


if __name__ == "__main__":
    unittest.main()
