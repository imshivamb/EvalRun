from langfuse import observe

from framework.llms import BaseLLM, Message
from framework.models import AgentOutput
from agents.base import BaseAgent
from .prompts import RESEARCH_SYSTEM_PROMPT


class ResearchAgent(BaseAgent):
    """A travel research assistant agent designed to retrieve factual answers."""

    def __init__(self, llm: BaseLLM):
        """Initializes the ResearchAgent.

        Args:
            llm: The LLM client wrapper to use for reasoning and answering questions.
        """
        self.llm = llm

    @observe(name="research-agent")
    def run(self, prompt: str) -> AgentOutput:
        """Runs the research agent to answer a specific factual query.

        Args:
            prompt: The specific question/query (e.g. transit time, price, schedule).

        Returns:
            An AgentOutput containing the research answer.
        """
        messages = [
            Message(role="system", content=RESEARCH_SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ]

        response = self.llm.generate(messages)

        metadata = {
            "agent": self.__class__.__name__,
            "llm": type(self.llm).__name__,
        }

        return AgentOutput(
            content=response.text,
            metadata=metadata,
        )
