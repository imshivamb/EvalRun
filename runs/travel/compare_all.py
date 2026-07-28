"""v1 (Planner only) vs v2 (Planner + Reflection) multi-model comparison suite.

Runs evaluations on both Llama 3.1 8B and Gemini 1.5 Pro to compare cross-model generalization.
To run:
    PYTHONPATH=. python3 runs/travel/compare_all.py
"""

import os
import sys
from typing import Dict, List, Any
from framework import parse_benchmark, BenchmarkRunner
from framework.llms.openai import OpenAILLM
from framework.llms.gemini import GeminiLLM
from agents.travel import TravelPlanningAgent
from agents.research import ResearchAgent, ResearchPlanner
from agents.reflection import ReflectionAgent
from framework.mcp.client import TravelValidationMCPClient

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
    api_key_nv = os.environ.get("NVIDIA_API_KEY")
    api_key_gemini = os.environ.get("GEMINI_API_KEY")

    if not api_key_nv:
        print("Error: NVIDIA_API_KEY is not set in environment or .env file.", file=sys.stderr)
        sys.exit(1)
    if not api_key_gemini:
        print("Error: GEMINI_API_KEY is not set in environment or .env file.", file=sys.stderr)
        sys.exit(1)

    # 1. Setup Reference Judge LLM (Keep constant for fair evaluations)
    judge_model = "meta/llama-3.1-8b-instruct"
    print(f"Initializing reference judge model: {judge_model}...")
    judge_llm = OpenAILLM(
        model_name=judge_model,
        api_key=api_key_nv,
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=120.0,
    )

    # Scenarios to run
    scenarios = [
        ("Budget", "evals/scenarios/travel-agent/budget-constrained-itinerary.md"),
        ("Route Optimization", "evals/scenarios/travel-agent/multi-city-route-optimization.md"),
        ("Remote Worker", "evals/scenarios/travel-agent/remote-worker-timezones.md"),
        ("Replanning", "evals/scenarios/travel-agent/mid-trip-replanning.md"),
        ("Information Gathering", "evals/scenarios/travel-agent/information-gathering-uncertainty.md"),
    ]

    # Models to compare. Keep the historical Llama baseline as the small open-model
    # stress case, then compare it with two Gemini tiers and OpenAI's balanced GPT tier.
    target_models = [
        ("Llama 3.1 8B", "meta/llama-3.1-8b-instruct", "nvidia"),
        ("Gemini 3.1 Pro", "models/gemini-3.1-pro-preview", "gemini"),
        ("Gemini 3.5 Flash", "models/gemini-3.5-flash", "gemini"),
        ("GPT-5.6 Terra", os.environ.get("OPENAI_MODEL", "gpt-5.6-terra"), "openai"),
    ]
    selected_models = {
        label.strip()
        for label in os.environ.get("BENCHMARK_MODELS", "").split(",")
        if label.strip()
    }
    if selected_models:
        target_models = [
            model for model in target_models if model[0] in selected_models
        ]
        if not target_models:
            print("Error: BENCHMARK_MODELS did not match a configured model.", file=sys.stderr)
            sys.exit(1)

    all_results = {}

    for label, model_name, provider in target_models:
        print(f"\n==================================================")
        print(f"EVALUATING MODEL: {label} ({model_name})")
        print(f"==================================================")

        # Setup agent LLM instance
        if provider == "gemini":
            agent_llm = GeminiLLM(model_name=model_name, api_key=api_key_gemini)
        elif provider == "nvidia":
            agent_llm = OpenAILLM(
                model_name=model_name,
                api_key=api_key_nv,
                base_url="https://integrate.api.nvidia.com/v1",
                timeout=60.0,
            )
        elif provider == "openai":
            openai_key = os.environ.get("OPENAI_API_KEY")
            if not openai_key:
                print(f"FAILED: OPENAI_API_KEY is not set but needed for {model_name}.", file=sys.stderr)
                continue
            agent_llm = OpenAILLM(
                model_name=model_name,
                api_key=openai_key,
                timeout=120.0,
            )
        else:
            print(f"FAILED: Unsupported provider '{provider}'.", file=sys.stderr)
            continue

        # Setup subagents
        research_agent = ResearchAgent(agent_llm)
        research_planner = ResearchPlanner(agent_llm)
        reflection_agent = ReflectionAgent(agent_llm)

        model_results = []

        for name, filepath in scenarios:
            print(f"\n--- Scenario: {name} ({filepath}) ---")

            # ---------------- Run v1 (Planner Only) ----------------
            print(f">>> Running v1 (Planner Only) for {label}...")
            agent_v1 = TravelPlanningAgent(
                llm=agent_llm,
                research_agent=research_agent,
                research_planner=research_planner,
                reflection_agent=None
            )
            runner_v1 = BenchmarkRunner(
                agent=agent_v1,
                judge_llm=judge_llm,
                local_verifier_path="ground_truth/japan_demo.json",
                output_dir=f"scratch/{provider}/v1",
            )
            try:
                result_v1 = runner_v1.run(filepath)
                score_v1 = result_v1.overall_score
                print(f"v1 Score: {score_v1:.2f}")
            except Exception as e:
                print(f"FAILED to run v1 for {label}: {e}")
                score_v1 = 0.0

            # ---------------- Run v2 (Planner + Reflection + MCP) ----------------
            print(f">>> Running v2 (Planner + Reflection + MCP) for {label}...")
            agent_v2 = TravelPlanningAgent(
                llm=agent_llm,
                research_agent=research_agent,
                research_planner=research_planner,
                reflection_agent=reflection_agent,
                validation_client=TravelValidationMCPClient(),
            )
            runner_v2 = BenchmarkRunner(
                agent=agent_v2,
                judge_llm=judge_llm,
                local_verifier_path="ground_truth/japan_demo.json",
                output_dir=f"scratch/{provider}/v2",
            )
            try:
                result_v2 = runner_v2.run(filepath)
                score_v2 = result_v2.overall_score
                print(f"v2 Score: {score_v2:.2f}")
            except Exception as e:
                print(f"FAILED to run v2 for {label}: {e}")
                score_v2 = 0.0

            delta = score_v2 - score_v1
            model_results.append({
                "scenario": name,
                "v1": score_v1,
                "v2": score_v2,
                "delta": delta
            })

        all_results[label] = model_results

    # 4. Print Consolidated Markdown Comparison Report
    print("\n\n==================== CONSOLIDATED MULTI-MODEL REPORT ====================")
    for label, results in all_results.items():
        print(f"\n### Model: {label}")
        print("| Scenario | Planner Only (v1) | Planner + Reflection (v2) | Delta |")
        print("| :--- | :---: | :---: | :---: |")
        for r in results:
            sign = "+" if r['delta'] >= 0 else ""
            print(f"| {r['scenario']} | {r['v1']:.2f} | {r['v2']:.2f} | {sign}{r['delta']:.2f} |")
    print("============================================================================\n")

    # 5. Export results to JSON for dashboard generator
    import json
    export_data = {
        "framework_version": "v2",
        "planner": "TravelPlanningAgent",
        "research_agent": "Enabled",
        "reflection_agent": "Enabled",
        "scenarios_evaluated": [name for name, _ in scenarios],
        "models": {}
    }
    for label, model_name, provider in target_models:
        results = all_results.get(label, [])
        scenario_scores = {}
        for r in results:
            scenario_scores[r["scenario"]] = {
                "v1": r["v1"],
                "v2": r["v2"]
            }
        export_data["models"][label] = {
            "provider": provider,
            "model_id": model_name,
            "scenarios": scenario_scores
        }
    results_path = os.environ.get("BENCHMARK_RESULTS_PATH", "results/week4/results.json")
    os.makedirs(os.path.dirname(results_path) or ".", exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(export_data, f, indent=2)
    print(f"Saved results to {results_path}")

if __name__ == "__main__":
    main()
