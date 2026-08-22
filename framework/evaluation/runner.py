"""Benchmark runner for orchestrating end-to-end agent evaluation pipelines."""

import inspect
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from framework.core import RunTrace
from framework.models import AgentOutput, Benchmark, EvaluationResult
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
        auditor: Any = None,
    ):
        """Initializes the BenchmarkRunner.

        Args:
            agent: The agent under test (must expose a run(prompt: str) method returning AgentOutput).
            judge_llm: The reference judge LLM client.
            local_verifier_path: Path to the local database file for factual verification.
            output_dir: Folder to store reports and itineraries.
            auditor: Optional IndependentBudgetAuditor instance for v3 read-only gate checks.
        """
        self.agent = agent
        self.judge_llm = judge_llm
        self.local_verifier_path = local_verifier_path
        self.output_dir = output_dir
        self.auditor = auditor

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

        # 3. Execute agent with RunTrace instrumentation
        t0 = time.time()
        start_time = datetime.now(timezone.utc)
        run_kwargs = {}
        run_parameters = inspect.signature(self.agent.run).parameters
        if "planning_mode" in run_parameters:
            run_kwargs["planning_mode"] = "closed_world_evaluation"
        if "validation_scenario_id" in run_parameters:
            run_kwargs["validation_scenario_id"] = benchmark.benchmark_id

        agent_output = None
        status = "success"
        err_msg = None

        try:
            agent_output = self.agent.run(benchmark.prompt, **run_kwargs)

            # 4. Optional v3 Independent Budget Auditor Gate Pass
            if self.auditor is not None:
                audit_report = self.auditor.audit(
                    scenario_prompt=benchmark.prompt,
                    itinerary_content=agent_output.content,
                )
                agent_output.metadata["audit_report"] = audit_report.to_dict()
                agent_output.metadata["audit_gate_decision"] = audit_report.status

            # 5. Evaluate using the engine
            result = self.engine.evaluate(benchmark, agent_output, profile)

            latency = time.time() - t0
            finished_time = datetime.now(timezone.utc)

            # 6. Record RunTrace metadata
            llm_obj = getattr(self.agent, "llm", None)
            raw_usage = getattr(llm_obj, "last_token_usage", None) if llm_obj else None
            token_usage = raw_usage if isinstance(raw_usage, dict) else None

            trace = RunTrace(
                trace_id=f"tr-{uuid.uuid4().hex[:8]}",
                scenario_id=benchmark.benchmark_id,
                agent_id=getattr(self.agent, "agent_name", self.agent.__class__.__name__),
                model_name=getattr(llm_obj, "model_name", "unknown") if llm_obj else "unknown",
                started_at_utc=start_time.isoformat(),
                finished_at_utc=finished_time.isoformat(),
                latency_seconds=round(latency, 2),
                status="success",
                error=None,
                token_usage=token_usage,
                metadata=agent_output.metadata,
            )
            agent_output.metadata["run_trace"] = {
                "trace_id": trace.trace_id,
                "started_at_utc": trace.started_at_utc,
                "finished_at_utc": trace.finished_at_utc,
                "latency_seconds": trace.latency_seconds,
                "status": trace.status,
                "token_usage": trace.token_usage,
            }

            # 7. Save reports and outputs
            self._save_execution_files(benchmark, agent_output, result, profile)
            return result

        except Exception as e:
            latency = time.time() - t0
            finished_time = datetime.now(timezone.utc)
            status = "timeout" if isinstance(e, (TimeoutError, TimeoutError)) or "timeout" in str(e).lower() else "error"
            err_msg = str(e)

            llm_obj = getattr(self.agent, "llm", None)
            raw_usage = getattr(llm_obj, "last_token_usage", None) if llm_obj else None
            token_usage = raw_usage if isinstance(raw_usage, dict) else None

            agent_name = getattr(self.agent, "agent_name", None) or self.agent.__class__.__name__
            model_name = getattr(llm_obj, "model_name", "unknown") if llm_obj and hasattr(llm_obj, "model_name") else "unknown"

            trace = RunTrace(
                trace_id=f"tr-{uuid.uuid4().hex[:8]}",
                scenario_id=benchmark.benchmark_id,
                agent_id=str(agent_name),
                model_name=str(model_name),
                started_at_utc=start_time.isoformat(),
                finished_at_utc=finished_time.isoformat(),
                latency_seconds=round(latency, 2),
                status=status,
                error=err_msg,
                token_usage=token_usage,
            )

            # Persist error trace metadata file
            self._save_error_trace_file(benchmark, trace)
            raise

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
            "agent_metadata": agent_output.metadata,
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
            f.write(f"- **Overall Score**: **{result.overall_score:.2f} / 100**\n")
            f.write(f"- **Outcome**: {'✅ PASSED' if result.passed else '❌ FAILED'}\n\n")

            # Render Auditor Gate metadata section if present
            if "audit_report" in agent_output.metadata:
                audit = agent_output.metadata["audit_report"]
                f.write(f"## Independent Auditor Gate Report\n\n")
                f.write(f"- **Gate Decision**: `{'PASS' if audit.get('passed') else 'BLOCK'}`\n")
                f.write(f"- **Audit Score**: {audit.get('audit_score', 0.0):.2f} / 100\n")
                f.write(f"- **Audit Confidence**: {audit.get('audit_confidence', 0.0):.2f}\n")
                f.write(f"- **Reasoning Summary**: {audit.get('reasoning_summary', 'N/A')}\n\n")
                if audit.get("violations"):
                    f.write("### Detected Budget Violations\n\n")
                    for v in audit["violations"]:
                        f.write(f"- **{v['violation_type']}**: {v['description']} (Est. Discrepancy: ₹{v.get('estimated_discrepancy_inr', 0.0):,.2f})\n")
                    f.write("\n")

            # Render MCP metadata trace section if present
            if "mcp_validation" in agent_output.metadata:
                mcp = agent_output.metadata["mcp_validation"]
                f.write(f"## MCP Validation Trace\n\n")
                f.write(f"- **Status**: `{mcp.get('status', 'unknown')}`\n")
                f.write(f"- **Locked-Booking Check**: `{'valid' if mcp.get('locked_valid') else 'invalid'}`\n")
                f.write(f"- **Savings Check**: ₹{mcp.get('savings_realized_inr', 0):,} verified (target: ₹{mcp.get('target_savings_inr', 0):,})\n\n")

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

    def _save_error_trace_file(self, benchmark: Benchmark, trace: RunTrace) -> None:
        """Persists an error/timeout trace JSON record when an evaluation fails."""
        os.makedirs(self.output_dir, exist_ok=True)
        model_name = trace.model_name.replace("/", "_").replace(".", "_")
        json_path = os.path.join(self.output_dir, f"{model_name}_{benchmark.benchmark_id}_error_trace.json")
        trace_data = {
            "trace_id": trace.trace_id,
            "scenario_id": trace.scenario_id,
            "agent_id": trace.agent_id,
            "model_name": trace.model_name,
            "started_at_utc": trace.started_at_utc,
            "finished_at_utc": trace.finished_at_utc,
            "latency_seconds": trace.latency_seconds,
            "status": trace.status,
            "error": trace.error,
            "token_usage": trace.token_usage,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2)
