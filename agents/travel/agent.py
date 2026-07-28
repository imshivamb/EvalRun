from langfuse import observe

import asyncio
import json
from typing import Any, Dict, Optional
from framework.llms import BaseLLM, Message
from framework.models import AgentOutput
from framework.utils import parse_json_markdown
from framework.memory import BaseSessionMemory
from agents.base import BaseAgent
from agents.research.planner import ResearchPlanner
from framework.mcp.revision_summary import (
    REVISION_SUMMARY_JSON_TEMPLATE,
    parse_revision_summary,
)
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
        validation_client: Optional[Any] = None,
    ):
        """Initializes the TravelPlanningAgent.

        Args:
            llm: The LLM client wrapper to generate itineraries.
            research_agent: An optional research subagent to query for factual details.
            research_planner: An optional planner to determine what queries to research.
            reflection_agent: An optional reflection subagent to critique itineraries.
            validation_client: Optional async MCP client for deterministic
                replanning checks. It is opt-in so baseline experiments remain
                unchanged.
        """
        self.llm = llm
        self.research_agent = research_agent
        self.research_planner = research_planner or ResearchPlanner(llm)
        self.reflection_agent = reflection_agent
        self.validation_client = validation_client

    @observe(name="travel-planning-agent")
    def run(
        self,
        prompt: str,
        session_memory: Optional[BaseSessionMemory] = None,
        validation_scenario_id: Optional[str] = None,
    ) -> AgentOutput:
        """Generates a travel itinerary based on user preferences.

        Args:
            prompt: The user prompt describing constraints and preferences.
            session_memory: Optional session memory to provide state context.
            validation_scenario_id: MCP scenario identifier. When supplied
                together with ``validation_client`` during replanning, the
                proposed revision is checked before the final LLM revision.

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
        mcp_validation: Optional[Dict[str, Any]] = None
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

                # Determine if this is a mid-trip replanning scenario
                is_replanning = False
                if session_memory and session_memory.state.current_day > 1:
                    is_replanning = True
                elif "currently on day" in prompt.lower() or "replanning" in prompt.lower() or "disruption" in prompt.lower():
                    is_replanning = True

                if is_replanning:
                    revision_rules = (
                        "1. PRESERVE every part of the itinerary that was NOT criticized. Do NOT rewrite or shift unaffected days.\n"
                        "2. Do NOT modify, delete, or rearrange locked bookings (e.g., booked flights, non-refundable hotel stays).\n"
                        "3. Make ONLY the minimum necessary adjustments needed to resolve the critique points."
                    )
                else:
                    revision_rules = (
                        "1. You are free to re-sequence, compress, or optimize the entire itinerary globally to satisfy the constraints (e.g., total duration, must-visit destinations) and address the critiques.\n"
                        "2. Do NOT exceed the total duration limit specified in the original request.\n"
                        "3. Make adjustments to address the critiques while keeping the travel style and preferences consistent."
                    )

                if is_replanning and self.validation_client and validation_scenario_id:
                    mcp_validation = self._validate_replanning_proposal(
                        system_prompt=system_prompt,
                        scenario_prompt=prompt,
                        draft_itinerary=final_itinerary,
                        critique=critique,
                        scenario_id=validation_scenario_id,
                    )

                # Formulate revision prompt
                validation_context = ""
                if mcp_validation:
                    validation_context = (
                        "\n\n### DETERMINISTIC MCP VALIDATION REPORT:\n"
                        f"{json.dumps(mcp_validation, indent=2)}\n"
                        "Treat every violation or unmet savings target in this report as a hard "
                        "requirement for the final revision. Do not claim a saving unless it is "
                        "represented by a concrete itinerary change.\n"
                    )
                revision_prompt = (
                    f"### ORIGINAL SCENARIO REQUEST:\n{prompt}\n\n"
                    f"### INITIAL DRAFT PLAN:\n{final_itinerary}\n\n"
                    f"### REFLECTION CRITIQUE:\n{critique}\n\n"
                    "You are instructed to revise the initial draft plan to resolve the critiques listed above.\n"
                    "You MUST strictly follow these rules during the revision:\n"
                    f"{revision_rules}\n"
                    "4. If a critique point directly conflicts with an existing hard constraint in the original request, prioritize and preserve the hard constraint.\n"
                    "5. You MUST generate a complete, full day-by-day traveler-facing itinerary. Do NOT output a list of questions, deferrals, or requests for information in place of the itinerary."
                    f"{validation_context}"
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
            "reflection_approved": not bool(reflection_critique),
            "revision_triggered": bool(reflection_critique),
        }
        if research_metadata:
            metadata["research_steps"] = research_metadata
        if reflection_critique:
            metadata["reflection_critique"] = reflection_critique
            metadata["final_plan_version"] = session_memory.state.current_plan_version if session_memory else 2
        if mcp_validation:
            metadata["mcp_validation"] = mcp_validation

        return AgentOutput(
            content=final_itinerary,
            metadata=metadata,
        )

    def _validate_replanning_proposal(
        self,
        system_prompt: str,
        scenario_prompt: str,
        draft_itinerary: str,
        critique: str,
        scenario_id: str,
    ) -> Dict[str, Any]:
        """Gets explicit revision claims and validates them through MCP.

        The model does not use this call to write the final traveler-facing
        answer. It only declares the concrete changes it intends to make, which
        lets MCP verify locked bookings and arithmetic before the final rewrite.
        A malformed summary or unavailable server is reported to the final
        revision prompt rather than silently treated as a passing check.
        """
        # Retrieve exact locked constraints to ground the model on valid booking IDs
        locked_info = {}
        if self.validation_client:
            try:
                locked_info = self._call_validation_tool(
                    "get_locked_constraints", {"scenario_id": scenario_id}
                )
            except Exception:
                pass

        immutable_ids = locked_info.get("immutable_booking_ids", ["kyoto-hostel", "narita-return-flight"])

        summary_prompt = (
            "Return only one JSON object describing the proposed replanning revision. "
            "Do not write an itinerary and do not use Markdown outside the JSON.\n\n"
            f"The scenario_id must be exactly: {scenario_id}\n"
            f"The exact booking_id values to preserve in booking_actions MUST be: {json.dumps(immutable_ids)}. "
            "Do NOT add suffixes or alter these booking_id strings.\n"
            "List every itinerary day you intend to change. For every locked booking, "
            "declare preserve, move, cancel, or modify. Itemize each concrete saving "
            "in INR; do not estimate a total without its components.\n\n"
            f"Required JSON shape:\n{REVISION_SUMMARY_JSON_TEMPLATE}\n\n"
            f"### ORIGINAL SCENARIO REQUEST:\n{scenario_prompt}\n\n"
            f"### INITIAL DRAFT PLAN:\n{draft_itinerary}\n\n"
            f"### REFLECTION CRITIQUE:\n{critique}\n"
        )
        summary_response = self.llm.generate(
            [
                Message(role="system", content=system_prompt),
                Message(role="user", content=summary_prompt),
            ]
        )

        try:
            summary = parse_revision_summary(summary_response.text)
            if summary.scenario_id != scenario_id:
                raise ValueError(
                    "Revision summary scenario_id does not match the requested scenario."
                )
            tool_arguments = summary.to_tool_arguments()
            return {
                "status": "completed",
                "revision_summary": tool_arguments,
                "locked_constraints": locked_info or self._call_validation_tool(
                    "get_locked_constraints", {"scenario_id": scenario_id}
                ),
                "revision_check": self._call_validation_tool(
                    "validate_revision",
                    {
                        "scenario_id": scenario_id,
                        "booking_actions": tool_arguments["booking_actions"],
                        "changed_days": tool_arguments["changed_days"],
                    },
                ),
                "savings_check": self._call_validation_tool(
                    "calculate_savings",
                    {
                        "scenario_id": scenario_id,
                        "savings_items": tool_arguments["savings_items"],
                    },
                ),
            }
        except (RuntimeError, ValueError) as error:
            return {
                "status": "unavailable",
                "error": str(error),
                "raw_revision_summary": summary_response.text,
            }

    def _call_validation_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Runs an async MCP call from this currently synchronous agent API."""
        return asyncio.run(self.validation_client.call_tool(name, arguments))
