"""Public Python SDK API for programmatic agent evaluation and regression testing."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from framework.core.adapters import PythonAgentAdapter, HttpAgentAdapter, CliAgentAdapter
from framework.evaluation.runner import BenchmarkRunner
from framework.llms.openai_compatible import OpenAICompatibleLLM
from framework.models import EvaluationResult
from framework.regression import load_baseline_manifest, compare_runs, RegressionReport
from cli.resolver import resolve_agent


def evaluate(
    scenario: str,
    agent: str,
    model: str,
    base_url: str = "https://api.openai.com/v1",
    api_key: Optional[str] = None,
    judge_model: Optional[str] = None,
    judge_base_url: Optional[str] = None,
    judge_api_key: Optional[str] = None,
    ground_truth: str = "ground_truth/japan_demo.json",
    output_dir: str = "./eval_results",
) -> List[EvaluationResult]:
    """Programmatically runs agent evaluation on a scenario or suite directory.

    Args:
        scenario: Path to a scenario file (.md) or suite directory.
        agent: Agent specifier string ('module:Class' or 'module:factory').
        model: Target agent model name.
        base_url: Target agent model OpenAI-compatible base URL.
        api_key: Target agent API key.
        judge_model: Judge model name (defaults to target model).
        judge_base_url: Judge base URL (defaults to target base_url).
        judge_api_key: Judge API key (defaults to target api_key).
        ground_truth: Ground truth knowledge base path.
        output_dir: Target output directory for evaluation artifacts.

    Returns:
        List of EvaluationResult objects.
    """
    target_api_key = api_key or os.getenv("OPENAI_API_KEY", "EMPTY")
    judge_model_name = judge_model or model
    j_base_url = judge_base_url or base_url
    j_api_key = judge_api_key or target_api_key

    # Initialize Target LLM
    target_llm = OpenAICompatibleLLM(
        model_name=model,
        base_url=base_url,
        api_key=target_api_key,
    )

    # Initialize Judge LLM
    judge_llm = OpenAICompatibleLLM(
        model_name=judge_model_name,
        base_url=j_base_url,
        api_key=j_api_key,
    )

    # Resolve target agent
    resolved_agent = resolve_agent(agent, target_llm)

    # Instantiate BenchmarkRunner
    runner = BenchmarkRunner(
        agent=resolved_agent,
        judge_llm=judge_llm,
        ground_truth_path=ground_truth,
    )

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    scenario_path = Path(scenario)
    results: List[EvaluationResult] = []

    if scenario_path.is_dir():
        for fname in os.listdir(scenario_path):
            if fname.endswith(".md") or fname.endswith(".json"):
                s_file = scenario_path / fname
                try:
                    res = runner.run(str(s_file))
                    results.append(res)
                except Exception as e:
                    print(f"Warning: Failed to evaluate scenario '{s_file}': {e}")
    else:
        res = runner.run(str(scenario_path))
        results.append(res)

    return results


def compare(
    candidate_results: List[EvaluationResult],
    baseline: str,
    max_regression: float = 5.0,
    max_dimension_regression: float = 10.0,
    candidate_run_id: str = "candidate-run",
) -> RegressionReport:
    """Programmatically compares candidate evaluation results against a baseline.

    Args:
        candidate_results: List of candidate EvaluationResult objects.
        baseline: Path to baseline directory or manifest.json file.
        max_regression: Maximum allowed overall score drop before release blocked.
        max_dimension_regression: Maximum allowed per-dimension score drop before release blocked.
        candidate_run_id: Identifier for candidate run.

    Returns:
        A RegressionReport object.
    """
    baseline_data = load_baseline_manifest(baseline)
    return compare_runs(
        candidate_results=candidate_results,
        baseline_data=baseline_data,
        max_overall_drop=max_regression,
        max_dim_drop=max_dimension_regression,
        candidate_run_id=candidate_run_id,
    )
