"""Offline, zero-credential EvalRun product demonstration."""

import json
from datetime import datetime, timezone
from pathlib import Path

from cli.formatter import format_terminal_summary
from cli.html_reporter import generate_html_report
from framework.models import DimensionScore, EvaluationResult


def run_demo(output_dir: str = "results/demo") -> int:
    """Create a deterministic sample report without contacting a model endpoint."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = EvaluationResult(
        benchmark_id="evalrun-demo-scenario",
        benchmark_name="EvalRun Offline Demo",
        overall_score=88.0,
        dimension_scores=[
            DimensionScore("Constraint Satisfaction", 90.0, "All demo constraints were satisfied."),
            DimensionScore("Planning Quality", 86.0, "The demo output is coherent and complete."),
        ],
        passed=True,
        agent_metadata={"demo": True, "audit_gate_decision": "PASS"},
    )
    manifest = {
        "run_id": "evalrun-offline-demo",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_agent_spec": "built-in offline demo",
        "target_model": {"model_name": "offline-demo", "base_url": "local", "api_key": "EMPTY"},
        "judge_model": {"model_name": "offline-demo", "base_url": "local", "api_key": "EMPTY"},
        "output_dir": str(out),
        "total_scenarios": 1,
        "overall_passed": True,
        "scenarios": [{"scenario_id": result.benchmark_id, "scenario_name": result.benchmark_name,
                       "overall_score": result.overall_score, "passed": result.passed,
                       "audit_gate_decision": "PASS"}],
    }
    with open(out / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    with open(out / "evalrun-demo-output.txt", "w", encoding="utf-8") as handle:
        handle.write("This is a deterministic offline preview. No model endpoint was contacted.\n")
    generate_html_report([result], manifest, str(out))
    print(format_terminal_summary([result], manifest))
    print(f"\nOffline demo artifacts: {out.resolve()}")
    return 0
