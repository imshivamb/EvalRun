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
    EvaluationEngine,
    ConstraintEvaluator,
    PlanningQualityEvaluator,
    PersonalizationEvaluator,
    AdaptabilityEvaluator,
    InformationAccuracyEvaluator,
    LocalKnowledgeBaseVerifier,
    ClaimExtractor,
    VerificationPipeline,
    TRAVEL_PROFILE,
    TRAVEL_ROUTE_OPTIMIZATION_PROFILE,
    TRAVEL_REMOTE_WORKER_TIMEZONES_PROFILE,
    TRAVEL_MID_TRIP_REPLANNING_PROFILE,
    TRAVEL_INFORMATION_GATHERING_UNCERTAINTY_PROFILE,
    CONSTRAINT_SATISFACTION,
    PLANNING_QUALITY,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    ADAPTABILITY,
)
from framework.llms.openai import OpenAILLM
from framework.llms.gemini import GeminiLLM
from agents.travel import TravelPlanningAgent


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
    try:
        benchmark = parse_benchmark(filepath)
        print(f"Loaded benchmark: {benchmark.name}")
    except Exception as e:
        print(f"Error parsing scenario: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve profile dynamically
    if benchmark.profile == "travel-route-optimization":
        profile_obj = TRAVEL_ROUTE_OPTIMIZATION_PROFILE
    elif benchmark.profile == "travel-remote-worker-timezones":
        profile_obj = TRAVEL_REMOTE_WORKER_TIMEZONES_PROFILE
    elif benchmark.profile == "travel-mid-trip-replanning":
        profile_obj = TRAVEL_MID_TRIP_REPLANNING_PROFILE
    elif benchmark.profile == "travel-information-gathering-uncertainty":
        profile_obj = TRAVEL_INFORMATION_GATHERING_UNCERTAINTY_PROFILE
    else:
        profile_obj = TRAVEL_PROFILE
    print(f"Using evaluation profile: {profile_obj.name}")

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

    # 3. Setup Verification Subsystem using the Reference Judge
    verifier = LocalKnowledgeBaseVerifier("ground_truth/japan_demo.json")
    extractor = ClaimExtractor(judge_llm)
    pipeline = VerificationPipeline(extractor, verifier)

    # 4. Setup Evaluation Engine with Reference Judge Evaluators
    evaluators = {
        CONSTRAINT_SATISFACTION: ConstraintEvaluator(judge_llm),
        PLANNING_QUALITY: PlanningQualityEvaluator(judge_llm),
        INFORMATION_ACCURACY: InformationAccuracyEvaluator(judge_llm, pipeline),
        PERSONALIZATION: PersonalizationEvaluator(judge_llm),
        ADAPTABILITY: AdaptabilityEvaluator(judge_llm),
    }
    engine = EvaluationEngine(evaluators=evaluators)

    # 5. List target agent models to test
    target_models = [
        "meta/llama-3.1-8b-instruct",
        "models/gemini-3.1-pro-preview",
    ]

    results_table: List[Dict[str, Any]] = []

    # 6. Execute loop
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
        agent = TravelPlanningAgent(agent_llm)

        # Generate trip itinerary
        print(f"1. Generating itinerary using {model_name}...")
        try:
            agent_output = agent.run(benchmark.prompt)
            # Save generated itinerary to scratch folder
            os.makedirs("scratch", exist_ok=True)
            safe_name = model_name.replace("/", "_").replace(".", "_")
            itinerary_path = f"scratch/{safe_name}_{benchmark.benchmark_id}_itinerary.md"
            with open(itinerary_path, "w", encoding="utf-8") as f:
                f.write(agent_output.content)
            print(f"Saved itinerary to {itinerary_path}")
        except Exception as e:
            print(f"FAILED to plan itinerary with {model_name}: {e}")
            continue

        # Evaluate itinerary using reference judges
        print("2. Running reference judges to evaluate planned itinerary...")
        try:
            eval_result = engine.evaluate(benchmark, agent_output, profile_obj)
            print("Evaluation successful.")
        except Exception as e:
            print(f"FAILED to evaluate output for {model_name}: {e}")
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

    # 7. Print Comparative Markdown Table
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
