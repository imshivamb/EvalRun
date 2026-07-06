"""Orchestration script to run a travel agent evaluation experiment using a real LLM.

To run this experiment:
    PYTHONPATH=. python3 runs/travel/run_benchmark.py
"""

import os
import sys
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
    VerificationStatus,
    TRAVEL_PROFILE,
    CONSTRAINT_SATISFACTION,
    PLANNING_QUALITY,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    ADAPTABILITY,
)
from framework.llms.openai import OpenAILLM
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


def print_report(result, report, agent_output):
    """Prints a structured visual console evaluation report."""
    print("\n==================== EVALUATION REPORT ====================")
    print(f"Benchmark Scenario: {result.benchmark_name} ({result.benchmark_id})")
    print(f"Applied Profile:    {TRAVEL_PROFILE.name}")
    print(f"Overall Score:      {result.overall_score:.2f} / 100")
    print(
        f"Pass Status:        {'PASS' if result.passed else 'FAIL'} (Threshold: {TRAVEL_PROFILE.pass_threshold})"
    )

    print("\n---------------- GENERATED ITINERARY ----------------")
    print(agent_output.content)
    print("-----------------------------------------------------")

    print("\nExtracted Claims & Verifications")
    print("-----------------------------------------------------------")
    for ev in report.evidence:
        status_symbol = "✓" if ev.status == VerificationStatus.VERIFIED else "✗"
        print(
            f"{status_symbol} {ev.claim.subject} -> {ev.claim.predicate}: "
            f"claimed '{ev.claim.value}' (Expected: '{ev.expected_value or 'N/A'}')"
        )
    print("-----------------------------------------------------------")
    print("Verification Summary")
    print(f"- Verified:  {report.verified_count}")
    print(f"- Refuted:   {report.refuted_count}")
    print(f"- Unknown:   {report.unknown_count}")
    print(f"- Not Found: {report.not_found_count}")
    print("-----------------------------------------------------------")

    print("\nDimension Breakdown:")
    for ds in result.dimension_scores:
        weight = TRAVEL_PROFILE.weights[ds.dimension]
        print(f"\n- {ds.dimension} (Weight: {weight}%)")
        print(f"  Score:  {ds.score}")
        print(f"  Reason: {ds.reason}")
    print("===========================================================")


def main():
    # Load env variables from .env
    load_env_file()

    # 1. Ingest Travel Agent Benchmark Scenario
    filepath = "evals/scenarios/travel-agent/budget-constrained-itinerary.md"
    try:
        benchmark = parse_benchmark(filepath)
    except Exception as e:
        print(f"Error parsing scenario: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Setup Real LLM (OpenAI-compatible) using NVIDIA MiniMax endpoint
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print("Error: NVIDIA_API_KEY is not set in environment or .env file.", file=sys.stderr)
        sys.exit(1)

    model_name = "meta/llama-3.1-8b-instruct"
    llm = OpenAILLM(
        model_name=model_name,
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=120.0,
    )

    # 3. Create Travel Planning Agent
    agent = TravelPlanningAgent(llm)

    # 4. Generate the itinerary from benchmark user prompt
    print(f"Executing TravelPlanningAgent on the real model ({model_name}) to plan trip...")
    try:
        agent_output = agent.run(benchmark.prompt)
    except Exception as e:
        print(f"Failed to generate travel itinerary: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Initialize the verification pipeline using Dependency Injection
    verifier = LocalKnowledgeBaseVerifier("ground_truth/japan_demo.json")
    extractor = ClaimExtractor(llm)
    pipeline = VerificationPipeline(extractor, verifier)

    # 6. Setup the evaluation engine with evaluators
    evaluators = {
        CONSTRAINT_SATISFACTION: ConstraintEvaluator(llm),
        PLANNING_QUALITY: PlanningQualityEvaluator(llm),
        INFORMATION_ACCURACY: InformationAccuracyEvaluator(llm, pipeline),
        PERSONALIZATION: PersonalizationEvaluator(llm),
        ADAPTABILITY: AdaptabilityEvaluator(llm),
    }
    engine = EvaluationEngine(evaluators=evaluators)

    # 7. Evaluate the itinerary
    print(f"Running evaluation engine judges over the itinerary using {model_name}...")
    try:
        result = engine.evaluate(benchmark, agent_output, TRAVEL_PROFILE)
    except Exception as e:
        print(f"Evaluation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 8. Extract verifier report for print presentation layout
    print("Running claim extractor and verification pipeline...")
    try:
        report = pipeline.run(agent_output)
    except Exception as e:
        print(f"Verification pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 9. Print final report
    print_report(result, report, agent_output)


if __name__ == "__main__":
    main()
