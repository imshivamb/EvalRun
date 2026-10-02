"""A deliberately weakened travel agent for checking that the regression gate catches a real drop.

It calls the real model, but its instructions tell it to skip budget arithmetic
and keep the plan to a few lines. The quality drop it causes is real, and it is
scored by the real judge, so a baseline comparison against the full
TravelPlanningAgent exercises the gate on a genuine regression.

Run from the repository root so the module is importable:

    PYTHONPATH=. evalrun run --agent examples.regression_check.weakened_travel_agent:WeakenedTravelAgent ...
"""

from agents.base import BaseAgent
from framework.llms import BaseLLM, Message
from framework.models import AgentOutput

WEAKENED_SYSTEM_PROMPT = """You are a travel assistant in a hurry.
Answer in at most five short lines. Do not add up costs, do not check the budget,
and do not give a day-by-day plan; just name a few places to visit.
"""


class WeakenedTravelAgent(BaseAgent):
    """Real model, deliberately degraded instructions."""

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def run(self, prompt: str) -> AgentOutput:
        response = self.llm.generate(
            [
                Message(role="system", content=WEAKENED_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ]
        )
        return AgentOutput(
            content=response.text,
            metadata={"agent": self.__class__.__name__, "llm": type(self.llm).__name__},
        )
