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

    # Configuration file flag
    run_parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to a JSON or TOML run configuration file",
    )

    # Mutually exclusive input selection
    input_group = run_parser.add_mutually_exclusive_group(required=False)
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
        default=None,
        help="Python agent import specifier (e.g. 'agents.travel:TravelPlanningAgent')",
    )

    # Target model endpoint flags
    run_parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Target agent model identifier (e.g. 'qwen2.5-72b-instruct', 'gpt-5.6-terra')",
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
        default=None,
        help="Maximum allowed overall score drop before release is blocked (default: 5.0)",
    )
    run_parser.add_argument(
        "--max-dimension-regression",
        type=float,
        default=None,
        help="Maximum allowed per-dimension score drop before release is blocked (default: 10.0)",
    )
    run_parser.add_argument(
        "--ground-truth",
        type=str,
        default=None,
        help="Path to domain knowledge base JSON for factual claim verification",
    )
    run_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output directory path for reports, traces, and manifest",
    )
    # UI Subcommand
    ui_parser = subparsers.add_parser("ui", help="Start guided local UI web server")
    ui_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address for local UI server (default: 127.0.0.1)")
    ui_parser.add_argument("--port", type=int, default=8501, help="Port number for local UI server (default: 8501)")

    demo_parser = subparsers.add_parser("demo", help="Run an offline demo without an API key")
    demo_parser.add_argument("--output", type=str, default="results/demo", help="Directory for demo artifacts")

    return parser


def run_command(args: argparse.Namespace) -> int:
    """Executes the 'run' command. Returns CLI exit code (0 = all passed, 1 = eval failure, 2 = runtime error)."""
    # Load config file if provided
    if getattr(args, "config", None):
        cfg_path = Path(args.config)
        if not cfg_path.exists():
            print(f"Error: Configuration file '{args.config}' not found.", file=sys.stderr)
            return 2
        try:
            if cfg_path.suffix == ".json":
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
            elif cfg_path.suffix == ".toml":
                if sys.version_info >= (3, 11):
                    import tomllib
                    with open(cfg_path, "rb") as f:
                        cfg_data = tomllib.load(f)
                else:
                    import toml
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg_data = toml.load(f)
            else:
                print(f"Error: Unsupported config format '{cfg_path.suffix}'. Use .json or .toml", file=sys.stderr)
                return 2

            for k, v in cfg_data.items():
                if getattr(args, k, None) is None:
                    setattr(args, k, v)
        except Exception as e:
            print(f"Error loading configuration file '{args.config}': {e}", file=sys.stderr)
            return 2

    # Set fallback defaults for optional flags if still None
    args.base_url = args.base_url or "https://api.openai.com/v1"
    args.ground_truth = args.ground_truth or "ground_truth/japan_demo.json"
    args.output = args.output or "./eval_results"
    args.max_regression = 5.0 if args.max_regression is None else args.max_regression
    args.max_dimension_regression = 10.0 if args.max_dimension_regression is None else args.max_dimension_regression

    if not getattr(args, "scenario", None) and not getattr(args, "suite", None):
        print("Error: Either --scenario or --suite or a valid config file specifying input is required.", file=sys.stderr)
        return 2

    if not getattr(args, "agent", None):
        print("Error: --agent specifier is required.", file=sys.stderr)
        return 2

    if not getattr(args, "model", None):
        print("Error: --model identifier is required.", file=sys.stderr)
        return 2
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

    # Instantiate BenchmarkRunner
    runner = BenchmarkRunner(
        agent=agent_instance,
        judge_llm=judge_llm,
        local_verifier_path=args.ground_truth,
        output_dir=str(output_dir),
    )

    # Gather Scenario Files
    scenario_files: List[Path] = []
    if args.scenario:
        scenario_file = Path(args.scenario)
        if not scenario_file.exists():
            print(f"Error: Scenario file '{args.scenario}' does not exist.", file=sys.stderr)
            return 2
        scenario_files.append(scenario_file)
    elif args.suite:
        suite_dir = Path(args.suite)
        if not suite_dir.exists() or not suite_dir.is_dir():
            print(f"Error: Suite directory '{args.suite}' does not exist or is not a directory.", file=sys.stderr)
            return 2
        scenario_files = sorted(list(suite_dir.glob("*.md")))
        if not scenario_files:
            print(f"Error: No benchmark scenario markdown files (.md) found in suite directory '{args.suite}'.", file=sys.stderr)
            return 2

    # Execute Evaluation Pipeline
    results: List[EvaluationResult] = []
    for s_file in scenario_files:
        try:
            res = runner.run(str(s_file))
            results.append(res)
        except Exception as e:
            print(f"Error executing evaluation for scenario '{s_file}': {e}", file=sys.stderr)
            return 2

    # Determine Baseline Comparison & 3-Tier Release Gate Outcomes
    evaluation_passed = all(r.passed for r in results)
    regression_report_dict = None

    if args.baseline:
        try:
            from framework.regression import load_baseline_manifest, compare_runs
            baseline_data = load_baseline_manifest(args.baseline)
            candidate_run_id = f"evalrun-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
            reg_report = compare_runs(
                candidate_results=results,
                baseline_data=baseline_data,
                max_overall_drop=args.max_regression,
                max_dim_drop=args.max_dimension_regression,
                candidate_run_id=candidate_run_id,
            )
            regression_report_dict = reg_report.to_dict()

            # Save standalone regression_report.json
            reg_path = output_dir / "regression_report.json"
            with open(reg_path, "w", encoding="utf-8") as f:
                json.dump(redact_credentials(regression_report_dict), f, indent=2)

            if reg_report.release_blocked:
                evaluation_passed = False
        except Exception as e:
            print(f"Error performing baseline regression comparison: {e}", file=sys.stderr)
            return 2

    # Verify Independent Auditor Gate Decisions
    for r in results:
        gate_decision = getattr(r, "agent_metadata", {}).get("audit_gate_decision", "PASS")
        if gate_decision == "BLOCK":
            evaluation_passed = False

    # Save Run Manifest
    scenarios_summary = []
    for r in results:
        scenarios_summary.append({
            "scenario_id": r.benchmark_id,
            "scenario_name": r.benchmark_name,
            "overall_score": r.overall_score,
            "passed": r.passed,
            "audit_gate_decision": getattr(r, "agent_metadata", {}).get("audit_gate_decision", "PASS"),
            "report_path": f"{getattr(runner.agent, 'llm', runner.agent).__class__.__name__.lower()}_{r.benchmark_id}_report.json",
        })

    manifest = {
        "run_id": f"evalrun-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_agent_spec": args.agent,
        "target_model": {
            "model_name": args.model,
            "base_url": args.base_url,
            "api_key": "[REDACTED]" if args.api_key else "ENVIRONMENT_OR_EMPTY",
        },
        "judge_model": {
            "model_name": judge_model_name,
            "base_url": judge_base_url,
            "api_key": "[REDACTED]" if judge_api_key else "ENVIRONMENT_OR_EMPTY",
        },
        "baseline_path": args.baseline,
        "ground_truth_path": args.ground_truth,
        "output_dir": str(output_dir),
        "total_scenarios": len(results),
        "overall_passed": evaluation_passed,
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
    elif args.command == "ui":
        from ui.server import run_ui_server
        server = run_ui_server(host=args.host, port=args.port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down local UI server.")
            server.server_close()
            sys.exit(0)
    elif args.command == "demo":
        from cli.demo import run_demo
        sys.exit(run_demo(output_dir=args.output))
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
