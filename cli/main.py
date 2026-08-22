"""Command-line interface entry point for evalrun."""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cli.formatter import format_terminal_summary, redact_credentials
from cli.resolver import resolve_agent
from framework.evaluation.runner import BenchmarkRunner
from framework.llms.openai_compatible import OpenAICompatibleLLM
from framework.models import EvaluationResult


def create_parser() -> argparse.ArgumentParser:
    """Creates the argparse parser for evalrun CLI."""
    parser = argparse.ArgumentParser(
        prog="evalrun",
        description="Local evaluation & regression testing toolkit for tool-using AI agents.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    run_parser = subparsers.add_parser("run", help="Run evaluation on a scenario or suite")

    # Mutually exclusive input selection
    input_group = run_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--scenario",
        "-s",
        type=str,
        help="Path to a single benchmark scenario markdown file (.md)",
    )
    input_group.add_argument(
        "--suite",
        type=str,
        help="Path to a suite directory containing benchmark scenario files (.md)",
    )

    # Agent configuration
    run_parser.add_argument(
        "--agent",
        "-a",
        type=str,
        required=True,
        help="Python agent import specifier (e.g. 'agents.travel:TravelPlanningAgent')",
    )

    # Target model endpoint flags
    run_parser.add_argument(
        "--model",
        "-m",
        type=str,
        required=True,
        help="Target agent model identifier (e.g. 'qwen2.5-72b-instruct', 'gpt-4o')",
    )
    run_parser.add_argument(
        "--base-url",
        type=str,
        default="https://api.openai.com/v1",
        help="OpenAI-compatible endpoint URL for target agent (e.g. 'http://localhost:8000/v1')",
    )
    run_parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for target model (defaults to OPENAI_API_KEY env or 'EMPTY')",
    )

    # Judge model endpoint flags
    run_parser.add_argument(
        "--judge-model",
        type=str,
        default=None,
        help="Judge model identifier (defaults to target --model if unspecified)",
    )
    run_parser.add_argument(
        "--judge-base-url",
        type=str,
        default=None,
        help="Judge OpenAI-compatible base URL (defaults to target --base-url if unspecified)",
    )
    run_parser.add_argument(
        "--judge-api-key",
        type=str,
        default=None,
        help="Judge API key (defaults to target --api-key if unspecified)",
    )

    # Output, Baseline & Verification flags
    run_parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Path to a baseline manifest.json file or directory from a prior run for regression comparison",
    )
    run_parser.add_argument(
        "--max-regression",
        type=float,
        default=5.0,
        help="Maximum allowed overall score drop before release is blocked (default: 5.0)",
    )
    run_parser.add_argument(
        "--max-dimension-regression",
        type=float,
        default=10.0,
        help="Maximum allowed per-dimension score drop before release is blocked (default: 10.0)",
    )
    run_parser.add_argument(
        "--ground-truth",
        type=str,
        default="ground_truth/japan_demo.json",
        help="Path to domain knowledge base JSON for factual claim verification",
    )
    run_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./eval_results",
        help="Output directory path for reports, traces, and manifest",
    )

    return parser


def run_command(args: argparse.Namespace) -> int:
    """Executes the 'run' command. Returns CLI exit code (0 = all passed, 1 = eval failure, 2 = runtime error)."""
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    judge_model_name = args.judge_model or args.model
    judge_base_url = args.judge_base_url or args.base_url
    judge_api_key = args.judge_api_key or args.api_key

    # Instantiate Model Endpoints
    try:
        target_llm = OpenAICompatibleLLM(
            model_name=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
        )
        judge_llm = OpenAICompatibleLLM(
            model_name=judge_model_name,
            base_url=judge_base_url,
            api_key=judge_api_key,
        )
    except Exception as e:
        print(f"Error initializing model endpoint client: {e}", file=sys.stderr)
        return 2

    # Instantiate Target Agent
    try:
        agent_instance = resolve_agent(args.agent, target_llm)
    except Exception as e:
        print(f"Error resolving agent specifier '{args.agent}': {e}", file=sys.stderr)
        return 2

    # Create BenchmarkRunner
    try:
        runner = BenchmarkRunner(
            agent=agent_instance,
            judge_llm=judge_llm,
            output_dir=str(output_dir),
            local_verifier_path=args.ground_truth,
        )
    except Exception as e:
        print(f"Error creating BenchmarkRunner: {e}", file=sys.stderr)
        return 2

    # Collect Scenario Files
    scenario_files: List[str] = []
    if args.scenario:
        if not os.path.exists(args.scenario):
            print(f"Error: Scenario file '{args.scenario}' does not exist.", file=sys.stderr)
            return 2
        scenario_files.append(args.scenario)
    elif args.suite:
        if not os.path.exists(args.suite) or not os.path.isdir(args.suite):
            print(f"Error: Suite directory '{args.suite}' does not exist or is not a folder.", file=sys.stderr)
            return 2
        for fn in sorted(os.listdir(args.suite)):
            if fn.endswith(".md"):
                scenario_files.append(os.path.join(args.suite, fn))

    if not scenario_files:
        print("Error: No markdown scenario files (.md) found to evaluate.", file=sys.stderr)
        return 2

    # Execute Scenario Runs
    results: List[EvaluationResult] = []
    evaluation_passed = True

    for scenario_file in scenario_files:
        try:
            res = runner.run(scenario_file)
            results.append(res)
            if not res.passed:
                evaluation_passed = False
            gate = getattr(res, "agent_metadata", {}).get("audit_gate_decision")
            if gate and gate != "PASS":
                evaluation_passed = False
        except Exception as e:
            print(f"Error evaluating scenario '{scenario_file}': {e}", file=sys.stderr)
            return 2

    # Prepare Manifest with Redacted Credentials
    run_id = f"evalrun-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    # Optional Baseline Regression Comparison
    regression_report_dict = None
    if args.baseline:
        try:
            from framework.regression import load_baseline_manifest, compare_runs
            baseline_data = load_baseline_manifest(args.baseline)
            reg_report = compare_runs(
                candidate_results=results,
                baseline_data=baseline_data,
                max_overall_drop=args.max_regression,
                max_dim_drop=args.max_dimension_regression,
                candidate_run_id=run_id,
            )
            regression_report_dict = reg_report.to_dict()

            if reg_report.release_blocked:
                evaluation_passed = False

            reg_report_path = output_dir / "regression_report.json"
            with open(reg_report_path, "w", encoding="utf-8") as f:
                json.dump(redact_credentials(regression_report_dict), f, indent=2)

        except Exception as e:
            print(f"Error performing baseline regression comparison: {e}", file=sys.stderr)
            return 2

    # Scenarios summary list for manifest
    scenarios_summary = []
    for res in results:
        meta = getattr(res, "agent_metadata", {})
        scenarios_summary.append({
            "scenario_id": res.benchmark_id,
            "scenario_name": res.benchmark_name,
            "overall_score": res.overall_score,
            "passed": res.passed,
            "audit_gate_decision": meta.get("audit_gate_decision", "PASS"),
            "report_path": f"{getattr(getattr(runner.agent, 'llm', None), 'model_name', 'unknown').replace('/', '_').replace('.', '_')}_{res.benchmark_id}_report.json",
            "dimension_scores": {ds.dimension: ds.score for ds in res.dimension_scores},
        })

    manifest = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_agent_spec": args.agent,
        "target_model": {
            "model_name": args.model,
            "base_url": args.base_url,
            "api_key": args.api_key,
        },
        "judge_model": {
            "model_name": judge_model_name,
            "base_url": judge_base_url,
            "api_key": judge_api_key,
        },
        "ground_truth_path": args.ground_truth,
        "output_dir": str(output_dir),
        "total_scenarios": len(results),
        "overall_passed": evaluation_passed,
        "baseline_path": args.baseline,
        "scenarios": scenarios_summary,
    }

    redacted_manifest = redact_credentials(manifest)
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(redacted_manifest, f, indent=2)

    # Generate Local HTML Report
    try:
        from cli.html_reporter import generate_html_report
        generate_html_report(results, redacted_manifest, str(output_dir), regression_report=regression_report_dict)
    except Exception as e:
        print(f"Warning: Failed to generate HTML report: {e}", file=sys.stderr)

    # Render Terminal Summary
    terminal_report = format_terminal_summary(results, redacted_manifest, regression_report=regression_report_dict)
    print(terminal_report)

    return 0 if evaluation_passed else 1


def main(argv: Optional[List[str]] = None) -> None:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        exit_code = run_command(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
