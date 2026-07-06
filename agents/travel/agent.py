from langfuse import observe

from typing import Optional
from framework.llms import BaseLLM, Message
from framework.models import AgentOutput
from framework.utils import parse_json_markdown
from framework.memory import BaseSessionMemory
from agents.base import BaseAgent
from agents.research.planner import ResearchPlanner
from .prompts import TRAVEL_PLANNING_SYSTEM_PROMPT


class TravelPlanningAgent(BaseAgent):
    """A travel planning assistant agent powered by an LLM.

    Accepts user prompts/scenarios and plans itineraries accordingly,
    optionally collaborating with a ResearchAgent, ResearchPlanner, and SessionMemory.
    """

    def __init__(
        self,
        llm: BaseLLM,
        research_agent: Optional[BaseAgent] = None,
        research_planner: Optional[ResearchPlanner] = None,
        reflection_agent: Optional[BaseAgent] = None,
    ):
        """Initializes the TravelPlanningAgent.

        Args:
            llm: The LLM client wrapper to generate itineraries.
            research_agent: An optional research subagent to query for factual details.
            research_planner: An optional planner to determine what queries to research.
            reflection_agent: An optional reflection subagent to critique itineraries.
        """
        self.llm = llm
        self.research_agent = research_agent
        self.research_planner = research_planner or ResearchPlanner(llm)
        self.reflection_agent = reflection_agent

    @observe(name="travel-planning-agent")
    def run(self, prompt: str, session_memory: Optional[BaseSessionMemory] = None) -> AgentOutput:
        """Generates a travel itinerary based on user preferences.

        Args:
            prompt: The user prompt describing constraints and preferences.
            session_memory: Optional session memory to provide state context.

        Returns:
            An AgentOutput containing the planned travel itinerary.
        """
        research_context = ""
        research_metadata = []

        if self.research_agent:
            # Delegate query generation to the external planner component
            queries = self.research_planner.plan_queries(prompt)
            if queries:
                findings = []
                for query in queries:
                    try:
                        research_output = self.research_agent.run(query)
                        escaped_query = query.replace('"', '\\"')
                        # Indent multi-line answers to preserve YAML block formatting
                        indented_answer = research_output.content.replace('\n', '\n    ')
                        findings.append(
                            f"- query: \"{escaped_query}\"\n"
                            f"  answer: |\n"
                            f"    {indented_answer}"
                        )
                        research_metadata.append({
                            "query": query,
                            "researcher": research_output.metadata.get("agent"),
                        })
                    except Exception as e:
                        findings.append(f"- query: \"{query}\"\n  answer: \"FAILED: {e}\"")
                
                research_context = (
                    "### FACTUAL RESEARCH FINDINGS (YAML format):\n"
                    "Research Findings:\n"
                    + "\n".join(findings)
                    + "\n==================================================\n\n"
                )

        memory_context = ""
        if session_memory:
            memory_context = (
                "### CURRENT TRAVELER SESSION STATE (YAML format):\n"
                f"{session_memory.to_yaml()}\n"
                "==================================================\n\n"
            )

        system_prompt = TRAVEL_PLANNING_SYSTEM_PROMPT
        user_content = ""
        if memory_context:
            user_content += memory_context
        if research_context:
            user_content += research_context
        user_content += prompt

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_content),
        ]

        # 1. Generate initial draft plan (v1)
        response = self.llm.generate(messages)
        final_itinerary = response.text

        # 2. Invoke reflection loop if a reflection agent is set
        reflection_critique = None
        if self.reflection_agent:
            if hasattr(self.reflection_agent, "reflect"):
                reflection_output = self.reflection_agent.reflect(prompt, final_itinerary, session_memory)
            else:
                reflection_output = self.reflection_agent.run(
                    f"Scenario: {prompt}\n\nDraft Itinerary:\n{final_itinerary}"
                )
            
            critique = reflection_output.content
            if "ITINERARY APPROVED" not in critique:
                reflection_critique = critique
                # Increment plan version in memory
                if session_memory:
                    session_memory.state.current_plan_version += 1
                
                # Regenerate memory context with updated plan version
                memory_context_v2 = ""
                if session_memory:
                    memory_context_v2 = (
                        "### CURRENT TRAVELER SESSION STATE (YAML format):\n"
                        f"{session_memory.to_yaml()}\n"
                        "==================================================\n\n"
                    )

                # Formulate revision prompt
                revision_prompt = (
                    f"### ORIGINAL SCENARIO REQUEST:\n{prompt}\n\n"
                    f"### INITIAL DRAFT PLAN:\n{final_itinerary}\n\n"
                    f"### REFLECTION CRITIQUE:\n{critique}\n\n"
                    "Please revise the initial draft plan to completely address all the critiques listed above. "
                    "Maintain the parts of the plan that are already correct and respect all travel, budget, and work constraints."
                )

                user_content_v2 = ""
                if memory_context_v2:
                    user_content_v2 += memory_context_v2
                if research_context:
                    user_content_v2 += research_context
                user_content_v2 += revision_prompt

                messages_v2 = [
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_content_v2),
                ]
                # Generate revised plan (v2)
                response = self.llm.generate(messages_v2)
                final_itinerary = response.text

        # 3. Assemble metadata
        metadata = {
            "agent": self.__class__.__name__,
            "llm": type(self.llm).__name__,
        }
        if research_metadata:
            metadata["research_steps"] = research_metadata
        if reflection_critique:
            metadata["reflection_critique"] = reflection_critique
            metadata["final_plan_version"] = session_memory.state.current_plan_version if session_memory else 2

        return AgentOutput(
            content=final_itinerary,
            metadata=metadata,
        )
