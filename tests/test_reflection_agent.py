import unittest
from agents.reflection.agent import ReflectionAgent
from agents.travel import TravelSessionMemory, UserPreferences
from framework.llms import MockLLM


class TestReflectionAgent(unittest.TestCase):
    """Tests the ReflectionAgent audit and critique behaviors."""

    def test_reflection_agent_run(self):
        llm = MockLLM(responses=["ITINERARY APPROVED"])
        agent = ReflectionAgent(llm)

        output = agent.run("Critique this draft plan.")
        self.assertEqual(output.content, "ITINERARY APPROVED")
        self.assertEqual(output.metadata["agent"], "ReflectionAgent")

    def test_reflection_agent_reflect(self):
        llm = MockLLM(responses=["Critique: Day 3 has a work conflict."])
        agent = ReflectionAgent(llm)

        pref = UserPreferences(interests=["museums"])
        session_memory = TravelSessionMemory(session_id="ref_session", preferences=pref)

        output = agent.reflect(
            prompt="Plan a trip.",
            itinerary="Day 1: Tokyo. Day 2: Kyoto.",
            session_memory=session_memory
        )

        self.assertEqual(output.content, "Critique: Day 3 has a work conflict.")


if __name__ == "__main__":
    unittest.main()
