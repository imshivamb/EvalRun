"""Run the controlled v2 versus v2.1 MCP replanning experiment.

Both configurations use the same planner model, reflection model, scenario,
session state, and judge model. v2.1 alone receives deterministic MCP feedback
between reflection and its final revision.

Usage:
    PYTHONPATH=. .venv/bin/python runs/travel/compare_mcp_replanning.py
    PLANNER_MODEL=models/gemini-3.1-pro-preview MCP_RESULTS_PATH=results/mcp-constraint-validation/mcp-replanning-gemini-3-1-pro.json PYTHONPATH=. .venv/bin/python runs/travel/compare_mcp_replanning.py
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from agents.reflection import ReflectionAgent
from agents.travel import CurrentTripState, TravelPlanningAgent, TravelSessionMemory
from framework import (
    ADAPTABILITY,
    CONSTRAINT_SATISFACTION,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    PLANNING_QUALITY,
    ClaimExtractor,
    ConstraintEvaluator,
    EvaluationEngine,
    InformationAccuracyEvaluator,
    LocalKnowledgeBaseVerifier,
    PlanningQualityEvaluator,
    PersonalizationEvaluator,
    AdaptabilityEvaluator,
    TRAVEL_MID_TRIP_REPLANNING_PROFILE,
    VerificationPipeline,
    parse_benchmark,
)
from framework.llms.openai import OpenAILLM
from framework.llms.gemini import GeminiLLM
from framework.mcp.client import TravelValidationMCPClient


SCENARIO_PATH = "evals/scenarios/travel-agent/mid-trip-replanning.md"
DEFAULT_RESULTS_PATH = "results/mcp-constraint-validation/mcp-replanning-gpt-5-6-terra.json"


def load_env_file():
    """Loads local development variables without adding another dependency."""
    if not os.path.exists(".env"):
        return
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


def create_llm(model_name: str, timeout: float = 180.0):
    """Factory creating appropriate LLM client instance for OpenAI, Gemini, or NVIDIA NIM."""
    if "gemini" in model_name.lower():
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
        return GeminiLLM(model_name=model_name, api_key=api_key)
    elif "llama" in model_name.lower() or "nvidia" in model_name.lower():
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY is not set in environment or .env file.")
        return OpenAILLM(
            model_name=model_name,
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            timeout=timeout,
        )
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment or .env file.")
        return OpenAILLM(model_name=model_name, api_key=api_key, timeout=timeout)


def create_engine(judge_llm):
    """Creates the unchanged evaluation pipeline used for both configurations."""
    verifier = LocalKnowledgeBaseVerifier("ground_truth/japan_demo.json")
    pipeline = VerificationPipeline(ClaimExtractor(judge_llm), verifier)
    return EvaluationEngine(
        {
            CONSTRAINT_SATISFACTION: ConstraintEvaluator(judge_llm),
            PLANNING_QUALITY: PlanningQualityEvaluator(judge_llm),
            INFORMATION_ACCURACY: InformationAccuracyEvaluator(judge_llm, pipeline),
            PERSONALIZATION: PersonalizationEvaluator(judge_llm),
            ADAPTABILITY: AdaptabilityEvaluator(judge_llm),
        }
    )


def fresh_replanning_memory():
    """Returns the same Day 12 state for each side of the comparison."""
    return TravelSessionMemory(
        session_id="mcp-replanning-eval",
        state=CurrentTripState(current_day=12),
    )


def serialise_result(result):
    return {
        "overall_score": result.overall_score,
        "passed": result.passed,
        "dimension_scores": {
            score.dimension: {"score": score.score, "reason": score.reason}
            for score in result.dimension_scores
        },
    }


def run_configuration(name, agent, benchmark, engine, use_mcp):
    """Generates and evaluates one side of the controlled comparison."""
    output = agent.run(
        benchmark.prompt,
        session_memory=fresh_replanning_memory(),
        validation_scenario_id=benchmark.benchmark_id if use_mcp else None,
        planning_mode="closed_world_evaluation",
    )
    result = engine.evaluate(benchmark, output, TRAVEL_MID_TRIP_REPLANNING_PROFILE)
    return {
        "configuration": name,
        "output": output.content,
        "agent_metadata": output.metadata,
        "evaluation": serialise_result(result),
    }


def main():
    load_env_file()
    
    # Model configuration
    model_name = os.environ.get("PLANNER_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-5.6-terra"
    judge_model = os.environ.get("EVAL_JUDGE_MODEL", model_name)
    
    # Target results path
    sanitized_model = model_name.replace("models/", "").replace(".", "-").replace("/", "-").replace("_", "-")
    default_path = f"results/mcp-constraint-validation/mcp-replanning-{sanitized_model}.json"
    results_path = Path(os.environ.get("MCP_RESULTS_PATH", default_path))
    
    try:
        planner_llm = create_llm(model_name=model_name, timeout=180.0)
        judge_llm = create_llm(model_name=judge_model, timeout=180.0)
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    benchmark = parse_benchmark(SCENARIO_PATH)
    engine = create_engine(judge_llm)

    baseline_agent = TravelPlanningAgent(
        llm=planner_llm,
        reflection_agent=ReflectionAgent(planner_llm),
    )
    mcp_agent = TravelPlanningAgent(
        llm=planner_llm,
        reflection_agent=ReflectionAgent(planner_llm),
        validation_client=TravelValidationMCPClient(),
    )

    print(f"Running v2 baseline with {model_name}...")
    baseline = run_configuration("v2_planner_reflection", baseline_agent, benchmark, engine, False)
    print(f"Running v2.1 MCP validation with {model_name}...")
    mcp = run_configuration("v2_1_planner_reflection_mcp", mcp_agent, benchmark, engine, True)

    deltas = {
        "overall_score": mcp["evaluation"]["overall_score"] - baseline["evaluation"]["overall_score"],
    }
    for dimension, score in mcp["evaluation"]["dimension_scores"].items():
        deltas[dimension] = score["score"] - baseline["evaluation"]["dimension_scores"][dimension]["score"]

    report = {
        "experiment": "mcp-replanning-v2-vs-v2.1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": benchmark.benchmark_id,
        "planner_model": model_name,
        "judge_model": judge_model,
        "control": "same scenario, Day 12 session state, planner model, reflection model, and judge; MCP feedback is the sole intended intervention",
        "baseline": baseline,
        "mcp": mcp,
        "deltas": deltas,
    }
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nControlled comparison complete")
    print(f"Model:        {model_name}")
    print(f"v2 overall:   {baseline['evaluation']['overall_score']:.2f}")
    print(f"v2.1 overall: {mcp['evaluation']['overall_score']:.2f}")
    print(f"Delta:        {deltas['overall_score']:+.2f}")
    print(f"Saved raw outputs and scores to {results_path}")


if __name__ == "__main__":
    main()
