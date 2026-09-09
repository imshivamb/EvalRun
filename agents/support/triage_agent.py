"""Customer-support triage agent used by the second-domain benchmark."""

from agents.base import BaseAgent
from framework.llms import BaseLLM, Message
from framework.models import AgentOutput
from framework.observability import observe


SUPPORT_TRIAGE_SYSTEM_PROMPT = """You are a production customer-support triage agent.

Read the ticket carefully and return a concise, structured triage decision. Include:
1. priority and the SLA deadline;
2. issue category and a one-sentence evidence-based summary;
3. immediate containment or next action;
4. the exact escalation destination and timing;
5. a safe, empathetic customer-facing response.

Do not invent a root cause, promise an unsupported resolution time, expose secrets,
or downgrade a high-impact production incident. Separate facts from hypotheses.
"""


class SupportTriageAgent(BaseAgent):
    """Thin adapter that gives any BaseLLM the support-triage agent contract."""

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    @observe(name="support-triage-agent")
    def run(self, prompt: str) -> AgentOutput:
        response = self.llm.generate(
            [
                Message(role="system", content=SUPPORT_TRIAGE_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ]
        )
        return AgentOutput(
            content=response.text,
            metadata={
                "agent": self.__class__.__name__,
                "llm": type(self.llm).__name__,
                "domain": "support-triage",
            },
        )
