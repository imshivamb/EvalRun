"""Research planner for generating travel fact queries to research."""

from framework.llms import BaseLLM, Message
from framework.utils import parse_json_markdown

from langfuse import observe


class ResearchPlanner:
    """Decides what factual details need to be researched based on a user's travel request."""

    def __init__(self, llm: BaseLLM):
        """Initializes the ResearchPlanner.

        Args:
            llm: The LLM client wrapper to use for generating queries.
        """
        self.llm = llm

    @observe(name="research-planner")
    def plan_queries(self, prompt: str) -> list[str]:
        """Generates up to 3 factual queries to guide research.

        Args:
            prompt: The user request/scenario prompt.

        Returns:
            A list of query strings.
        """
        system_instruction = (
            "You are a helpful travel planning assistant.\n"
            "Given the user's travel request, identify up to 3 critical factual questions "
            "(e.g., transit times between cities, lodging prices, attraction opening hours or closures, "
            "seasonal forecasts) that should be researched first to make the itinerary realistic.\n"
            "Respond ONLY with a valid JSON list of query strings (e.g., [\"Kyoto to Tokyo train duration\", \"Shinjuku Gyoen opening hours\"]). "
            "If no specific factual research is required, respond with []."
        )
        messages = [
            Message(role="system", content=system_instruction),
            Message(role="user", content=prompt),
        ]
        
        queries = []
        try:
            response = self.llm.generate(messages)
            parsed = parse_json_markdown(response.text)
            if isinstance(parsed, list):
                queries = [str(q) for q in parsed]
        except Exception:
            pass

        return queries
