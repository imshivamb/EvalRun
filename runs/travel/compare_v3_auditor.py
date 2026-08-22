"""Controlled comparison of v1 (Planner), v2 (Reflection), and v3 (Independent Budget Auditor Gate).

Evaluates travel itineraries across arms to measure:
- Release gate decision accuracy (PASS / BLOCK)
- Latent violation capture delta
- Planning quality & personalization stability
- Auditor latency overhead

Usage:
    PYTHONPATH=. .venv/bin/python runs/travel/compare_v3_auditor.py
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from agents.reflection import ReflectionAgent
from agents.travel import TravelPlanningAgent
from agents.auditor import IndependentBudgetAuditor
from framework.evaluation.runner import BenchmarkRunner
from framework.llms.gemini import GeminiLLM
from framework.llms.openai import OpenAILLM


SCENARIOS = [
    "evals/scenarios/travel-agent/budget-constrained-itinerary.md",
    "evals/scenarios/travel-agent/mid-trip-replanning.md",
]
RESULTS_PATH = "results/multi-model-benchmarks/v3_auditor_comparison.json"


def load_env():
    """Loads development variables from .env file."""
    if not os.path.exists(".env"):
        return
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ[key.strip()] = val.strip().strip('"').strip("'")


def create_llm(model_name: str, timeout: float = 180.0):
    """Factory creating LLM client instance."""
    if "gemini" in model_name.lower():
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        return GeminiLLM(model_name=model_name, api_key=api_key)
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        return OpenAILLM(model_name=model_name, api_key=api_key, timeout=timeout)


def main():
    load_env()
    model_name = os.environ.get("PLANNER_MODEL") or os.environ.get("GEMINI_MODEL") or "models/gemini-3.1-pro-preview"
    judge_model = os.environ.get("EVAL_JUDGE_MODEL", model_name)

    print("==================================================")
    print("RUNNING V1 vs V2 vs V3 INDEPENDENT AUDITOR GATE BENCHMARK")
    print(f"Planner Model: {model_name}")
    print(f"Judge Model:   {judge_model}")
    print("==================================================\n")

    planner_llm = create_llm(model_name)
    judge_llm = create_llm(judge_model)
    auditor_llm = create_llm(model_name)

    auditor = IndependentBudgetAuditor(llm=auditor_llm, max_retries=2)

    # Instantiate Agent Arms
    v1_agent = TravelPlanningAgent(llm=planner_llm, reflection_agent=None)
    v2_agent = TravelPlanningAgent(llm=planner_llm, reflection_agent=ReflectionAgent(planner_llm))
    v3_agent = TravelPlanningAgent(llm=planner_llm, reflection_agent=ReflectionAgent(planner_llm))

    comparison_results = []

    for scenario_path in SCENARIOS:
        print(f"\n--- Scenario: {os.path.basename(scenario_path)} ---")

        # 1. Run v1 (Planner Only)
        print(">>> Running v1 (Planner Only)...")
        runner_v1 = BenchmarkRunner(agent=v1_agent, judge_llm=judge_llm, output_dir="scratch/v1")
        res_v1 = runner_v1.run(scenario_path)

        # 2. Run v2 (Planner + Self-Reflection)
        print(">>> Running v2 (Planner + Reflection)...")
        runner_v2 = BenchmarkRunner(agent=v2_agent, judge_llm=judge_llm, output_dir="scratch/v2")
        res_v2 = runner_v2.run(scenario_path)

        # 3. Run v3 (Planner + Self-Reflection + Independent Auditor Gate)
        print(">>> Running v3 (Planner + Reflection + Independent Auditor Gate)...")
        t0 = time.time()
        runner_v3 = BenchmarkRunner(
            agent=v3_agent,
            judge_llm=judge_llm,
            auditor=auditor,
            output_dir="scratch/v3",
        )
        res_v3 = runner_v3.run(scenario_path)
        v3_latency = time.time() - t0

        # The evaluator's dimension reason is not the auditor gate decision.
        # Read the persisted agent metadata so the comparison report records
        # the independent PASS/BLOCK result explicitly.
        model_slug = model_name.replace("/", "_").replace(".", "_")
        v3_report_path = None
        for candidate in Path("scratch/v3").glob(f"{model_slug}_*_report.json"):
            candidate_data = json.loads(candidate.read_text(encoding="utf-8"))
            if candidate_data.get("benchmark_name") == res_v3.benchmark_name:
                v3_report_path = candidate
                break
        if v3_report_path is None:
            raise FileNotFoundError(
                f"Could not locate the v3 report for {res_v3.benchmark_name}"
            )
        v3_report = json.loads(v3_report_path.read_text(encoding="utf-8"))
        v3_metadata = v3_report.get("agent_metadata", {})
        audit_report = v3_metadata.get("audit_report", {})

        comparison_results.append({
            "scenario": os.path.basename(scenario_path),
            "v1": {
                "overall_score": res_v1.overall_score,
                "passed": res_v1.passed,
            },
            "v2": {
                "overall_score": res_v2.overall_score,
                "passed": res_v2.passed,
            },
            "v3": {
                "overall_score": res_v3.overall_score,
                "passed": res_v3.passed,
                "evaluator_score": res_v3.overall_score,
                "evaluator_passed": res_v3.passed,
                "auditor_gate_decision": v3_metadata.get("audit_gate_decision", "UNKNOWN"),
                "auditor_status": audit_report.get("status", "UNKNOWN"),
                "auditor_violations": audit_report.get("violations", []),
                "audit_latency_seconds": round(v3_latency, 2),
            },
        })

    # Save summary json
    output_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "planner_model": model_name,
        "judge_model": judge_model,
        "scenarios": comparison_results,
    }

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print(f"\n==================================================")
    print(f"COMPARE V1 vs V2 vs V3 COMPLETE")
    print(f"Results saved to: {RESULTS_PATH}")
    print(f"==================================================")


if __name__ == "__main__":
    main()
