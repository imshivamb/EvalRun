"""Verification demo script for multi-agent TravelPlanningAgent & ResearchPlanner collaboration.

Run this to inspect the exact questions generated, facts gathered, and final itinerary.
"""

import os
import sys
from framework.llms.openai import OpenAILLM
from agents.travel import TravelPlanningAgent
from agents.research import ResearchAgent, ResearchPlanner
from framework import parse_benchmark

def load_env_file():
    """Manually parses .env file if it exists to avoid python-dotenv dependency."""
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ[key] = val

def main():
    load_env_file()
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print("Error: Please set NVIDIA_API_KEY to run the demo.")
        sys.exit(1)

    # Optional Langfuse environment check
    lf_public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    lf_secret = os.environ.get("LANGFUSE_SECRET_KEY")
    if lf_public and lf_secret:
        print(f"Langfuse environment detected. Tracing is ACTIVE (Base URL: {os.environ.get('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com')})")
    else:
        print("Langfuse environment keys not found. Langfuse library will run in mock/disabled state.")

    # 1. Initialize LLMs
    print("Initializing LLMs...")
    agent_llm = OpenAILLM(
        model_name="meta/llama-3.1-8b-instruct",
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=60.0
    )

    # 2. Instantiate collaborative components
    print("Instantiating agent hierarchy...")
    research_agent = ResearchAgent(agent_llm)
    research_planner = ResearchPlanner(agent_llm)
    planner_agent = TravelPlanningAgent(
        llm=agent_llm,
        research_agent=research_agent,
        research_planner=research_planner
    )

    # 3. Load Scenario 2 (Multi-city Route Optimization)
    filepath = "evals/scenarios/travel-agent/multi-city-route-optimization.md"
    print(f"Loading scenario: {filepath}...")
    benchmark = parse_benchmark(filepath)

    # 4. Run the multi-agent planning pipeline
    print("\nRunning multi-agent pipeline...")
    output = planner_agent.run(benchmark.prompt)

    # 5. Output findings
    print("\n==================== EVALUATION OUTPUTS ====================")
    print("\n[A] Planned Research Queries:")
    steps = output.metadata.get("research_steps", [])
    for idx, step in enumerate(steps, 1):
        print(f"  {idx}. Query: '{step['query']}' (Resolved by {step['researcher']})")

    print("\n[B] Final Itinerary Preview (First 500 chars):")
    print("-" * 60)
    print(output.content[:500] + "...")
    print("-" * 60)
    print("============================================================")

if __name__ == "__main__":
    main()
