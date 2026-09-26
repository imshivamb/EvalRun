"""Thin CLI wrappers for calibration harvest, generate, and blinded labeling."""

import inspect
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any, Callable, Dict

from framework.calibration.generate import generate_cases
from framework.calibration.harvest import harvest_records
from framework.calibration.label_server import (
    CorpusIncompleteError,
    run_label_server,
)
from framework.calibration.store import write_corpus

SUPPORT_AGENT_SPEC = "agents.support:SupportTriageAgent"
TRAVEL_AGENT_SPEC = "agents.travel:TravelPlanningAgent"


def harvest_calibration_command(args: Namespace) -> int:
    """Write unique unlabeled cases from retained eval artifacts."""
    results_root = Path(args.results)
    scenarios_root = Path(args.scenarios)
    dest = Path(args.output)
    if not results_root.exists():
        print(f"Error: results directory '{results_root}' does not exist.", file=sys.stderr)
        return 2
    if not scenarios_root.exists():
        print(f"Error: scenarios directory '{scenarios_root}' does not exist.", file=sys.stderr)
        return 2
    records = harvest_records(results_root, scenarios_root)
    manifest = write_corpus(records, dest, scenarios_root=scenarios_root)
    print(f"[evalrun] Harvested {manifest['unique_count']} unique calibration cases.")
    print(f"[evalrun] Diversity counts: {manifest['diversity_counts']}")
    print(f"[evalrun] Diversity floor met: {manifest['diversity_floor_met']}")
    print(f"[evalrun] Wrote {dest / 'manifest.json'}")
    if manifest["unique_count"] < 40 or not manifest["diversity_floor_met"]:
        print(
            "[evalrun] Corpus is below the 40-case / diversity-floor gate. "
            "Generate remaining Gemini slots before labeling for the published claim.",
            file=sys.stderr,
        )
    return 0


def generate_calibration_command(args: Namespace) -> int:
    """Run agents to append unique unlabeled cases. Never runs the judge."""
    dest = Path(args.dir)
    scenarios_root = Path(args.scenarios)
    if not scenarios_root.exists():
        print(f"Error: scenarios directory '{scenarios_root}' does not exist.", file=sys.stderr)
        return 2
    # Imported here to avoid a cli.main -> calibration -> resolver -> framework.sdk cycle.
    from cli.resolver import resolve_agent
    from framework.llms.openai_compatible import OpenAICompatibleLLM

    try:
        llm = OpenAICompatibleLLM(
            model_name=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
        )
    except Exception as exc:
        print(f"Error initializing generator model: {exc}", file=sys.stderr)
        return 2
    run_agent = _agent_runner(llm, resolve_agent)
    result = generate_cases(
        dest=dest,
        scenarios_root=scenarios_root,
        run_agent=run_agent,
        generator_model=args.model,
    )
    print(f"[evalrun] Unique calibration cases: {result['unique_count']}")
    print(f"[evalrun] Diversity counts: {result['diversity_counts']}")
    print(f"[evalrun] Diversity floor met: {result['diversity_floor_met']}")
    if result.get("failed_scenarios"):
        print(
            f"[evalrun] Generation failed for: {result['failed_scenarios']}",
            file=sys.stderr,
        )
    if result["unique_count"] < 40 or not result["diversity_floor_met"]:
        print(
            "[evalrun] Corpus is still below the 40-case / diversity-floor gate. "
            "Do not pad with extra Budget runs.",
            file=sys.stderr,
        )
        return 2
    print("[evalrun] Corpus is ready for blinded labeling.")
    return 0


def _agent_runner(llm: Any, resolve_agent: Callable[..., Any]) -> Callable[[str, str], str]:
    cache: Dict[str, object] = {}

    def run_agent(scenario_id: str, prompt: str) -> str:
        spec = (
            SUPPORT_AGENT_SPEC
            if scenario_id.startswith("support-")
            else TRAVEL_AGENT_SPEC
        )
        if spec not in cache:
            cache[spec] = resolve_agent(spec, llm)
        agent = cache[spec]
        kwargs = {}
        if "planning_mode" in inspect.signature(agent.run).parameters:
            kwargs["planning_mode"] = "closed_world_evaluation"
        output = agent.run(prompt, **kwargs)
        return getattr(output, "content", str(output))

    return run_agent


def label_calibration_command(args: Namespace) -> int:
    """Serve a localhost labeling page that never reads meta.json."""
    try:
        server = run_label_server(
            corpus_dir=Path(args.dir),
            host=getattr(args, "host", "127.0.0.1"),
            port=int(args.port),
            allow_incomplete_corpus=bool(getattr(args, "allow_incomplete_corpus", False)),
        )
    except CorpusIncompleteError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down calibration label helper.")
        server.server_close()
    return 0
