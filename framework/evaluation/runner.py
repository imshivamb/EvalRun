"""Benchmark runner for orchestrating end-to-end agent evaluation pipelines."""

import os
import sys
import json
from typing import Dict, Any
from framework.models import Benchmark, AgentOutput, EvaluationResult
from framework.parser import parse_benchmark
from framework.profiles import PROFILE_REGISTRY, TRAVEL_PROFILE
from framework.evaluation.engine import EvaluationEngine
from framework.evaluation.dimensions import (
    CONSTRAINT_SATISFACTION,
    PLANNING_QUALITY,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    ADAPTABILITY,
)
from framework.evaluation.evaluators import (
    ConstraintEvaluator,
    PlanningQualityEvaluator,
    InformationAccuracyEvaluator,
    PersonalizationEvaluator,
    AdaptabilityEvaluator,
)
from framework.verification.extractor import ClaimExtractor
from framework.verification.local import LocalKnowledgeBaseVerifier
from framework.verification.pipeline import VerificationPipeline


class BenchmarkRunner:
    """Automates the entire evaluation pipeline for a given agent under test.

    Orchestrates benchmark ingestion, profile lookup, agent execution, evaluation via LLM judges,
    and report generation.
    """

    def __init__(
        self,
        agent,
        judge_llm,
        local_verifier_path: str = "ground_truth/japan_demo.json",
        output_dir: str = "scratch",
    ):
        """Initializes the BenchmarkRunner.

        Args:
            agent: The agent under test (must expose a run(prompt: str) method returning AgentOutput).
            judge_llm: The reference judge LLM client.
            local_verifier_path: Path to the local database file for factual verification.
            output_dir: Folder to store reports and itineraries.
        """
        self.agent = agent
        self.judge_llm = judge_llm
        self.local_verifier_path = local_verifier_path
        self.output_dir = output_dir

        # Initialize the verification pipeline
        self.verifier = LocalKnowledgeBaseVerifier(local_verifier_path)
        self.extractor = ClaimExtractor(judge_llm)
        self.pipeline = VerificationPipeline(self.extractor, self.verifier)

        # Initialize the evaluation engine
        evaluators = {
            CONSTRAINT_SATISFACTION: ConstraintEvaluator(judge_llm),
            PLANNING_QUALITY: PlanningQualityEvaluator(judge_llm),
            INFORMATION_ACCURACY: InformationAccuracyEvaluator(judge_llm, self.pipeline),
            PERSONALIZATION: PersonalizationEvaluator(judge_llm),
            ADAPTABILITY: AdaptabilityEvaluator(judge_llm),
        }
        self.engine = EvaluationEngine(evaluators=evaluators)

    def run(self, filepath: str) -> EvaluationResult:
        """Runs the complete evaluation pipeline for a single benchmark file.

        Args:
            filepath: Path to the benchmark markdown file.

        Returns:
            The final EvaluationResult containing overall and dimension scores.
        """
        # 1. Parse scenario file
        benchmark = parse_benchmark(filepath)

        # 2. Resolve evaluation profile
        profile = PROFILE_REGISTRY.get(benchmark.profile, TRAVEL_PROFILE)

        # 3. Execute agent
        agent_output = self.agent.run(benchmark.prompt)

        # 4. Evaluate using the engine
        result = self.engine.evaluate(benchmark, agent_output, profile)

        # 5. Save reports and outputs
        self._save_execution_files(benchmark, agent_output, result, profile)

        return result

    def run_directory(self, dirpath: str) -> Dict[str, EvaluationResult]:
        """Runs evaluations for all benchmark files in the specified directory.

        Args:
            dirpath: Path to the folder containing benchmark markdown files.

        Returns:
            A dictionary mapping benchmark ID to the EvaluationResult.
        """
        results = {}
        for filename in sorted(os.listdir(dirpath)):
            if filename.endswith(".md"):
                filepath = os.path.join(dirpath, filename)
                try:
                    result = self.run(filepath)
                    results[result.benchmark_id] = result
                except Exception as e:
                    print(f"Error evaluating benchmark '{filename}': {e}", file=sys.stderr)
        return results

    def _save_execution_files(
        self,
        benchmark: Benchmark,
        agent_output: AgentOutput,
        result: EvaluationResult,
        profile: Any,
    ):
        """Helper to serialize agent output, JSON data reports, and Markdown summaries."""
        os.makedirs(self.output_dir, exist_ok=True)
        agent_name = getattr(self.agent, "llm", self.agent).__class__.__name__.lower()
        if hasattr(self.agent, "llm") and hasattr(self.agent.llm, "model_name"):
            model_slug = self.agent.llm.model_name.replace("/", "_").replace(".", "_")
        else:
            model_slug = agent_name

        base_name = f"{model_slug}_{benchmark.benchmark_id}"

        # 1. Save Raw Agent Output/Itinerary
        itinerary_path = os.path.join(self.output_dir, f"{base_name}_itinerary.md")
        with open(itinerary_path, "w", encoding="utf-8") as f:
            f.write(agent_output.content)

        # 2. Save Detailed JSON Report
        report_data = {
            "benchmark_id": result.benchmark_id,
            "benchmark_name": result.benchmark_name,
            "agent_model": getattr(self.agent, "llm", self.agent).__class__.__name__,
            "model_name": getattr(getattr(self.agent, "llm", None), "model_name", "unknown"),
            "profile": profile.name,
            "overall_score": result.overall_score,
            "passed": result.passed,
            "dimension_scores": [
                {
                    "dimension": ds.dimension,
                    "score": ds.score,
                    "reason": ds.reason,
                }
                for ds in result.dimension_scores
            ],
        }
        json_path = os.path.join(self.output_dir, f"{base_name}_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # 3. Save Summary Markdown Report
        markdown_path = os.path.join(self.output_dir, f"{base_name}_report.md")
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(f"# Evaluation Summary Report\n\n")
            f.write(f"- **Benchmark**: {result.benchmark_name} (`{result.benchmark_id}`)\n")
            f.write(f"- **Agent Model**: {report_data['model_name']}\n")
            f.write(f"- **Evaluation Profile**: `{profile.name}`\n")
            f.write(f"- **Status**: {'🔴 FAIL' if not result.passed else '🟢 PASS'}\n")
            f.write(f"- **Overall Score**: **{result.overall_score:.2f}** (Threshold: {profile.pass_threshold:.1f})\n\n")
            f.write(f"## Dimension Breakdown\n\n")
            f.write(f"| Dimension | Score | Weight |\n")
            f.write(f"| :--- | :---: | :---: |\n")
            for ds in result.dimension_scores:
                weight = profile.weights.get(ds.dimension, 0.0)
                f.write(f"| {ds.dimension} | {ds.score:.1f} | {weight:.1f}% |\n")
            f.write(f"\n## Reasoning Details\n\n")
            for ds in result.dimension_scores:
                f.write(f"### {ds.dimension} (Score: {ds.score:.1f})\n\n")
                f.write(f"{ds.reason}\n\n")
