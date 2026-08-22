"""Example demonstrating programmatic Python SDK usage with evalrun."""

import os
from framework import evaluate, compare


def run_sdk_demo():
    print("1. Running evaluation programmatically via Python SDK...")
    
    results = evaluate(
        scenario="evals/scenarios/travel-agent/budget-constrained-itinerary.md",
        agent="agents.travel:TravelPlanningAgent",
        model="qwen2.5-72b-instruct",
        base_url="http://localhost:8000/v1",
        api_key="EMPTY",
        judge_model="gpt-5.6-terra",
        output_dir="./eval_results/sdk_demo_run",
    )

    for res in results:
        print(f"Scenario: {res.benchmark_name}")
        print(f"Overall Score: {res.overall_score:.2f} / 100")
        print(f"Evaluator Passed: {res.passed}")
        gate = getattr(res, "agent_metadata", {}).get("audit_gate_decision", "PASS")
        print(f"Auditor Gate: {gate}")

    # Optional: Compare against a prior baseline run directory
    baseline_dir = "./eval_results/baseline_run"
    if os.path.exists(baseline_dir):
        print("\n2. Comparing candidate results against baseline...")
        report = compare(
            candidate_results=results,
            baseline=baseline_dir,
            max_regression=5.0,
        )
        print(f"Regression Detected: {report.regression_detected}")
        print(f"Release Blocked: {report.release_blocked}")


if __name__ == "__main__":
    run_sdk_demo()
