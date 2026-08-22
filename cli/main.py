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

    # Output & Verification flags
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
        except Exception as e:
            print(f"Error evaluating scenario '{scenario_file}': {e}", file=sys.stderr)
            return 2

    # Prepare Manifest with Redacted Credentials
    run_id = f"evalrun-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
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
    }

    redacted_manifest = redact_credentials(manifest)
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(redacted_manifest, f, indent=2)

    # Render Terminal Summary
    terminal_report = format_terminal_summary(results, redacted_manifest)
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
