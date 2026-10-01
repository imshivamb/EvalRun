"""Package a real multi-trial `evalrun run` output directory as the offline demo recording.

Usage:
    python scripts/build_demo_recording.py <run-output-dir> <scenario-path> "<command used, without keys>"

The recording keeps only what the demo replays: per-trial scores, judge
justifications, the agent output and timing. API keys never appear in run
artifacts (they are redacted at write time); the script refuses to continue if
anything that looks like a key is present.
"""

import glob
import json
import os
import re
import sys

from framework.evaluation.runner import resolve_profile
from framework.parser import parse_benchmark

OUTPUT_PATH = os.path.join("cli", "demo_data", "recorded_run.json")
SECRET_PATTERN = re.compile(r"AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z]{20,}|Bearer\s+[0-9A-Za-z._\-]{20,}")


def build(run_dir: str, scenario_path: str, command: str) -> dict:
    with open(os.path.join(run_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)

    trials = []
    for report_path in sorted(glob.glob(os.path.join(run_dir, "*_trial*_report.json"))):
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        output_path = report_path.replace("_report.json", "_itinerary.md")
        with open(output_path, encoding="utf-8") as f:
            output_text = f.read()
        trials.append({
            "benchmark_id": report["benchmark_id"],
            "benchmark_name": report["benchmark_name"],
            "overall_score": report["overall_score"],
            "passed": report["passed"],
            "dimension_scores": report["dimension_scores"],
            "run_trace": report["agent_metadata"].get("run_trace"),
            "agent_output": output_text,
        })
    if len(trials) < 2:
        raise SystemExit("A demo recording needs a run with at least two trials.")

    benchmark = parse_benchmark(scenario_path)
    profile = resolve_profile(benchmark)
    return {
        "recording_version": 1,
        "provenance": {
            "run_id": manifest["run_id"],
            "recorded_at_utc": manifest["timestamp_utc"],
            "target_model": manifest["target_model"]["model_name"],
            "judge_model": manifest["judge_model"]["model_name"],
            "base_url": manifest["target_model"]["base_url"],
            "agent": manifest["target_agent_spec"],
            "scenario": scenario_path,
            "command": command,
        },
        "pass_threshold": profile.pass_threshold,
        "trials": trials,
    }


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    recording = build(sys.argv[1], sys.argv[2], sys.argv[3])
    serialized = json.dumps(recording, indent=2, ensure_ascii=False)
    if SECRET_PATTERN.search(serialized):
        raise SystemExit("Refusing to write: the recording contains something that looks like an API key.")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(serialized + "\n")
    print(f"Wrote {OUTPUT_PATH} with {len(recording['trials'])} trials.")


if __name__ == "__main__":
    main()
