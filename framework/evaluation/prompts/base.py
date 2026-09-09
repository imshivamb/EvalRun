"""Base template components and helpers for building evaluation prompts."""

from typing import List
from framework.models import AgentOutput, Benchmark
from framework.llms import Message

# Standard JSON schema instructions enforced across all LLM judges
JSON_RESPONSE_SCHEMA = (
    "Return a JSON object containing exactly these fields:\n"
    "{\n"
    '  "score": <integer from 0 to 100 representing the grade>,\n'
    '  "reason": "<detailed justification detailing your assessment>"\n'
    "}\n"
    "Do not include any markdown syntax, explanations, or code blocks outside the JSON."
)


def build_llm_judge_prompt(
    system_objective: str,
    criteria_rubric: str,
    benchmark: Benchmark,
    output: AgentOutput,
) -> List[Message]:
    """Universal prompt builder for LLM judges.

    Ensures consistent formatting and JSON output constraints.

    Args:
        system_objective: The role and primary mission of the judge.
        criteria_rubric: Rubric details specific to the evaluation dimension.
        benchmark: The benchmark scenario details.
        output: The agent response output.

    Returns:
        A list of chat Message structures.
    """
    system_instruction = (
        f"{system_objective}\n\n"
        f"### Rubric / Criteria:\n{criteria_rubric}\n\n"
        f"{JSON_RESPONSE_SCHEMA}"
    )

    user_prompt = (
        f"Benchmark Name: {benchmark.name}\n"
        f"Benchmark Description: {benchmark.description}\n\n"
        f"### User Request:\n{benchmark.prompt}\n\n"
        f"### Scenario Constraints:\n{benchmark.constraints}\n\n"
        f"### Pass Criteria:\n{benchmark.pass_criteria}\n\n"
        f"### Failure Conditions:\n{benchmark.failure_conditions}\n\n"
        f"### Agent Output To Evaluate:\n{output.content}\n"
    )

    return [
        Message(role="system", content=system_instruction),
        Message(role="user", content=user_prompt),
    ]
