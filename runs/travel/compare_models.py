"""Multi-model comparison experiment runner.

Executes a travel benchmark against several agent LLMs under a constant reference judge.
To run:
    PYTHONPATH=. python3 runs/travel/compare_models.py
"""

import os
import sys
from typing import Dict, List, Any
from framework import (
    parse_benchmark,
    BenchmarkRunner,
    CONSTRAINT_SATISFACTION,
    PLANNING_QUALITY,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    ADAPTABILITY,
)
from framework.llms.openai import OpenAILLM
from framework.llms.gemini import GeminiLLM
from agents.travel import TravelPlanningAgent
from agents.research import ResearchAgent, ResearchPlanner


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
    # Load env variables from .env
    load_env_file()

    # 1. Ingest Travel Agent Benchmark Scenario
    filepath = "evals/scenarios/travel-agent/information-gathering-uncertainty.md"
    if len(sys.argv) > 1:
        filepath = sys.argv[1]

    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print("Error: NVIDIA_API_KEY is not set in environment or .env file.", file=sys.stderr)
        sys.exit(1)

    # 2. Setup Reference Judge LLM (Keep constant for fair evaluations)
    judge_model = "meta/llama-3.1-8b-instruct"
    print(f"Initializing reference judge model: {judge_model}...")
    judge_llm = OpenAILLM(
        model_name=judge_model,
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=120.0,
    )

    # 3. List target agent models to test
    target_models = [
        "meta/llama-3.1-8b-instruct",
        "models/gemini-3.1-pro-preview",
    ]

    results_table: List[Dict[str, Any]] = []

    # 4. Execute loop
    for model_name in target_models:
        print(f"\n==================================================")
        print(f"Evaluating Agent Model: {model_name}")
        print(f"==================================================")

        # Instantiate agent under test dynamically based on provider type
        if "gemini" in model_name:
            gemini_key = os.environ.get("GEMINI_API_KEY")
            if not gemini_key:
                print(f"FAILED: GEMINI_API_KEY is not set but needed for {model_name}.", file=sys.stderr)
                continue
            agent_llm = GeminiLLM(
                model_name=model_name,
                api_key=gemini_key,
            )
        else:
            agent_llm = OpenAILLM(
                model_name=model_name,
                api_key=api_key,
                base_url="https://integrate.api.nvidia.com/v1",
                timeout=30.0,
                max_retries=0,
            )
        research_agent = ResearchAgent(agent_llm)
        research_planner = ResearchPlanner(agent_llm)
        agent = TravelPlanningAgent(
            llm=agent_llm,
            research_agent=research_agent,
            research_planner=research_planner
        )

        # 5. Initialize BenchmarkRunner and run pipeline
        runner = BenchmarkRunner(
            agent=agent,
            judge_llm=judge_llm,
            local_verifier_path="ground_truth/japan_demo.json",
            output_dir="scratch",
        )

        try:
            eval_result = runner.run(filepath)
            print("Evaluation successful.")
        except Exception as e:
            print(f"FAILED to run evaluation for {model_name}: {e}")
            continue

        # Map scores to table
        scores = {ds.dimension: ds.score for ds in eval_result.dimension_scores}
        row = {
            "Model": model_name,
            "Overall": eval_result.overall_score,
            "Constraint": scores.get(CONSTRAINT_SATISFACTION, 0.0),
            "Planning": scores.get(PLANNING_QUALITY, 0.0),
            "Accuracy": scores.get(INFORMATION_ACCURACY, 0.0),
            "Personalization": scores.get(PERSONALIZATION, 0.0),
            "Adaptability": scores.get(ADAPTABILITY, 0.0),
        }
        results_table.append(row)

    # 6. Print Comparative Markdown Table
    print("\n\n==================== COMPARATIVE MODEL REPORT ====================")
    print("| Model | Overall | Constraint | Planning | Accuracy | Personalization | Adaptability |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for row in results_table:
        print(
            f"| {row['Model']} "
            f"| {row['Overall']:.2f} "
            f"| {row['Constraint']:.1f} "
            f"| {row['Planning']:.1f} "
            f"| {row['Accuracy']:.1f} "
            f"| {row['Personalization']:.1f} "
            f"| {row['Adaptability']:.1f} |"
        )
    print("==================================================================\n")


if __name__ == "__main__":
    main()
