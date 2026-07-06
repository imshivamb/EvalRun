"""Demo script verifying the closed-loop reflection & revision pipeline.

Executes TravelPlanningAgent with ReflectionAgent enabled to trigger revision.
"""

import os
import sys
from framework.llms.openai import OpenAILLM
from agents.travel import TravelPlanningAgent, TravelSessionMemory, UserPreferences
from agents.research import ResearchAgent, ResearchPlanner
from agents.reflection import ReflectionAgent
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

    print("Initializing LLMs...")
    agent_llm = OpenAILLM(
        model_name="meta/llama-3.1-8b-instruct",
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=60.0
    )

    print("Instantiating multi-agent collaboration...")
    research_agent = ResearchAgent(agent_llm)
    research_planner = ResearchPlanner(agent_llm)
    reflection_agent = ReflectionAgent(agent_llm)
    
    # Enable reflection agent on planner agent
    planner_agent = TravelPlanningAgent(
        llm=agent_llm,
        research_agent=research_agent,
        research_planner=research_planner,
        reflection_agent=reflection_agent
    )

    # 1. Initialize Travel Session Memory
    pref = UserPreferences(interests=["museums", "digital art"], travel_style="relaxed")
    session_memory = TravelSessionMemory(session_id="verify_loop_session", preferences=pref)

    # 2. Load Scenario 2
    filepath = "evals/scenarios/travel-agent/multi-city-route-optimization.md"
    print(f"Loading scenario: {filepath}...")
    benchmark = parse_benchmark(filepath)

    # 3. Run the multi-agent pipeline
    print("\nRunning multi-agent pipeline with reflection loop enabled...")
    output = planner_agent.run(benchmark.prompt, session_memory=session_memory)

    print("\n==================== CLOSED-LOOP OUTPUTS ====================")
    critique = output.metadata.get("reflection_critique")
    if critique:
        print("\n[A] Reflection Critique Received:")
        print("-" * 60)
        print(critique)
        print("-" * 60)
        print(f"\n[B] Revision Triggered (Final Plan Version: {output.metadata.get('final_plan_version')})")
    else:
        print("\n[A] Reflection Critique: ITINERARY APPROVED (No revision needed)")

    print("\n[C] Final Itinerary Preview (First 500 chars):")
    print("-" * 60)
    print(output.content[:500] + "...")
    print("-" * 60)
    print("=============================================================")

if __name__ == "__main__":
    main()
