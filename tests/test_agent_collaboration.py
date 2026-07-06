import unittest
from agents.travel import TravelPlanningAgent, TravelSessionMemory, UserPreferences
from agents.research import ResearchAgent, ResearchPlanner
from framework.llms import MockLLM


class TestAgentCollaboration(unittest.TestCase):
    """Tests the interaction/collaboration between TravelPlanningAgent, ResearchPlanner, and ResearchAgent."""

    def test_travel_agent_without_researcher(self):
        llm = MockLLM(responses=["Generated itinerary without research."])
        agent = TravelPlanningAgent(llm=llm, research_agent=None)

        output = agent.run("Plan a 3-day trip to Tokyo.")
        self.assertEqual(output.content, "Generated itinerary without research.")
        self.assertNotIn("research_steps", output.metadata)

    def test_travel_agent_with_researcher_success(self):
        # Setup mock responses for planning & research
        planner_responses = ["Generated final itinerary using research context."]
        planner_llm = MockLLM(responses=planner_responses)

        # Setup research planner responses to plan queries
        research_planner_llm = MockLLM(responses=['["Kyoto to Hiroshima train time"]'])
        research_planner = ResearchPlanner(llm=research_planner_llm)

        # Research subagent response
        research_response = "Shinkansen takes about 1 hour and 40 minutes."
        research_llm = MockLLM(responses=[research_response])
        research_agent = ResearchAgent(llm=research_llm)

        # Construct collaborative agent with planner and researcher
        agent = TravelPlanningAgent(
            llm=planner_llm,
            research_agent=research_agent,
            research_planner=research_planner,
        )

        # Run pipeline
        output = agent.run("Plan a trip from Kyoto to Hiroshima.")

        # Assertions
        self.assertEqual(output.content, "Generated final itinerary using research context.")
        self.assertIn("research_steps", output.metadata)
        self.assertEqual(len(output.metadata["research_steps"]), 1)
        self.assertEqual(output.metadata["research_steps"][0]["query"], "Kyoto to Hiroshima train time")
        self.assertEqual(output.metadata["research_steps"][0]["researcher"], "ResearchAgent")

    def test_travel_agent_with_session_memory(self):
        planner_llm = MockLLM(responses=["Generated itinerary using session memory context."])
        agent = TravelPlanningAgent(llm=planner_llm, research_agent=None)

        pref = UserPreferences(interests=["history"], travel_style="slow")
        session_memory = TravelSessionMemory(session_id="mem_test", preferences=pref)

        output = agent.run("Plan a trip.", session_memory=session_memory)
        self.assertEqual(output.content, "Generated itinerary using session memory context.")

    def test_travel_agent_with_reflection_loop(self):
        # We need two responses from the planner: v1 draft, and v2 revised draft
        planner_llm = MockLLM(responses=["Initial plan (v1)", "Revised plan (v2) addressing critique."])
        
        from agents.reflection.agent import ReflectionAgent
        reflection_llm = MockLLM(responses=["Critique: Day 2 lacks buffer."])
        reflection_agent = ReflectionAgent(llm=reflection_llm)

        agent = TravelPlanningAgent(
            llm=planner_llm,
            reflection_agent=reflection_agent,
        )

        pref = UserPreferences(interests=["culture"])
        session_memory = TravelSessionMemory(session_id="loop_test", preferences=pref)

        output = agent.run("Plan a trip.", session_memory=session_memory)

        self.assertEqual(output.content, "Revised plan (v2) addressing critique.")
        self.assertIn("reflection_critique", output.metadata)
        self.assertEqual(output.metadata["reflection_critique"], "Critique: Day 2 lacks buffer.")
        self.assertEqual(output.metadata["final_plan_version"], 2)
        self.assertEqual(session_memory.state.current_plan_version, 2)


if __name__ == "__main__":
    unittest.main()
