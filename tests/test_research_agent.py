import unittest
from agents.research.agent import ResearchAgent
from agents.research.planner import ResearchPlanner
from framework.llms import MockLLM


class TestResearchAgent(unittest.TestCase):
    """Tests the ResearchAgent class."""

    def test_research_agent_run(self):
        # Setup mock responses
        mock_response = "The train from Kyoto to Hiroshima takes about 1 hour and 40 minutes via Tokaido-Sanyo Shinkansen."
        llm = MockLLM(responses=[mock_response])
        agent = ResearchAgent(llm)

        # Run agent
        query = "What is the train time from Kyoto to Hiroshima?"
        output = agent.run(query)

        # Verify output
        self.assertEqual(output.content, mock_response)
        self.assertEqual(output.metadata["agent"], "ResearchAgent")
        self.assertEqual(output.metadata["llm"], "MockLLM")


class TestResearchPlanner(unittest.TestCase):
    """Tests the ResearchPlanner class."""

    def test_research_planner_queries(self):
        llm = MockLLM(responses=['["Kyoto to Tokyo train duration", "Shinjuku Gyoen opening hours"]'])
        planner = ResearchPlanner(llm)

        queries = planner.plan_queries("Plan a trip to Kyoto and Tokyo.")
        self.assertEqual(queries, ["Kyoto to Tokyo train duration", "Shinjuku Gyoen opening hours"])


if __name__ == "__main__":
    unittest.main()
