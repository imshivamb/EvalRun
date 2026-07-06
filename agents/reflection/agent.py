"""Reflection agent implementation for auditing and critiquing planned itineraries."""

from typing import Optional
from langfuse import observe
from framework.llms import BaseLLM, Message
from framework.models import AgentOutput
from framework.memory import BaseSessionMemory
from agents.base import BaseAgent
from .prompts import REFLECTION_SYSTEM_PROMPT


class ReflectionAgent(BaseAgent):
    """An agent that critiques travel itineraries against traveler preferences and constraints."""

    def __init__(self, llm: BaseLLM):
        """Initializes the ReflectionAgent.

        Args:
            llm: The LLM client wrapper to use for auditing the itinerary.
        """
        self.llm = llm

    @observe(name="reflection-agent")
    def run(self, prompt: str) -> AgentOutput:
        """Fallback wrapper to satisfy BaseAgent abstract interface.

        Args:
            prompt: A combined text containing request details and itinerary to critique.

        Returns:
            An AgentOutput containing the critique text.
        """
        messages = [
            Message(role="system", content=REFLECTION_SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ]
        response = self.llm.generate(messages)

        return AgentOutput(
            content=response.text,
            metadata={
                "agent": self.__class__.__name__,
                "llm": type(self.llm).__name__,
            },
        )

    def reflect(
        self,
        prompt: str,
        itinerary: str,
        session_memory: Optional[BaseSessionMemory] = None,
    ) -> AgentOutput:
        """Audits a travel plan and returns structured critiques.

        Args:
            prompt: The original user travel request/scenario prompt.
            itinerary: The draft itinerary to evaluate.
            session_memory: Optional active session memory context.

        Returns:
            An AgentOutput containing critiques or 'ITINERARY APPROVED'.
        """
        memory_str = ""
        if session_memory:
            memory_str = (
                "### CURRENT TRAVELER SESSION STATE:\n"
                f"{session_memory.to_yaml()}\n"
                "==================================================\n\n"
            )

        user_content = (
            f"{memory_str}"
            f"### ORIGINAL USER PROMPT:\n{prompt}\n\n"
            f"### DRAFT ITINERARY TO AUDIT:\n{itinerary}\n"
        )

        return self.run(user_content)
