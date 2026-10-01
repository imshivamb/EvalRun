"""Offline, zero-credential EvalRun demo that replays a real recorded run.

The scores, judge justifications, agent outputs and timings come from a real
multi-trial run (see ``cli/demo_data/recorded_run.json`` for its provenance).
Nothing is contacted and nothing is invented; the demo re-renders that run
through the same aggregation and report code a live run uses.
"""

import json
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any, Dict

from cli.formatter import format_terminal_summary
from cli.html_reporter import generate_html_report
from framework.evaluation.trials import aggregate_trials
from framework.models import DimensionScore, EvaluationResult


def load_recording() -> Dict[str, Any]:
    """Loads the packaged recording of a real evaluation run."""
    data = resources.files("cli").joinpath("demo_data", "recorded_run.json").read_text(encoding="utf-8")
    return json.loads(data)


def _trial_result(trial: Dict[str, Any]) -> EvaluationResult:
    return EvaluationResult(
        benchmark_id=trial["benchmark_id"],
        benchmark_name=trial["benchmark_name"],
        overall_score=trial["overall_score"],
        dimension_scores=[
            DimensionScore(d["dimension"], d["score"], d["reason"]) for d in trial["dimension_scores"]
        ],
        passed=trial["passed"],
        agent_metadata={"run_trace": trial["run_trace"], "raw_content": trial["agent_output"]},
    )


def run_demo(output_dir: str = "results/demo") -> int:
    """Re-renders a real recorded run without contacting a model endpoint."""
    recording = load_recording()
    provenance = recording["provenance"]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = aggregate_trials(
        [_trial_result(t) for t in recording["trials"]], recording["pass_threshold"]
    )
    result.agent_metadata["recorded_run"] = provenance

    manifest = {
        "run_id": f"evalrun-demo-replay-of-{provenance['run_id']}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "replayed_from": provenance,
        "target_agent_spec": provenance["agent"],
        "target_model": {"model_name": provenance["target_model"], "base_url": provenance["base_url"]},
        "judge_model": {"model_name": provenance["judge_model"], "base_url": provenance["base_url"]},
        "output_dir": str(out),
        "total_scenarios": 1,
        "trials_per_scenario": result.statistics.trials,
        "overall_passed": result.passed,
        "scenarios": [{
            "scenario_id": result.benchmark_id,
            "scenario_name": result.benchmark_name,
            "overall_score": result.overall_score,
            "passed": result.passed,
            "statistics": result.statistics.to_dict(),
        }],
    }
    with open(out / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    generate_html_report([result], manifest, str(out))

    print(
        f"Replaying a real recorded run: {provenance['target_model']} agent and judge, "
        f"{result.statistics.trials} trials, recorded {provenance['recorded_at_utc'][:10]}.\n"
        "No model endpoint is contacted. Recorded with:\n"
        f"  {provenance['command']}\n"
    )
    print(format_terminal_summary([result], manifest))
    print(f"\nOffline demo artifacts: {out.resolve()}")
    return 0
