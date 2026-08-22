"""Baseline manifest and report loader for regression comparison."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def load_baseline_manifest(path_str: str) -> Dict[str, Any]:
    """Loads baseline manifest and per-scenario evaluation reports.

    Args:
        path_str: Path to a baseline directory containing manifest.json or path to manifest.json file.

    Returns:
        A dictionary structured as:
        {
            "manifest": dict,
            "scenarios": {
                "<scenario_id>": {
                    "scenario_id": str,
                    "scenario_name": str,
                    "overall_score": float,
                    "passed": bool,
                    "audit_gate_decision": str,
                    "dimension_scores": { "<dim_name>": float },
                    "report_path": str,
                    "itinerary_path": str
                }
            }
        }

    Raises:
        FileNotFoundError: If baseline manifest file or directory does not exist.
        ValueError: If manifest format is invalid.
    """
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Baseline path '{path_str}' does not exist.")

    if path.is_dir():
        manifest_file = path / "manifest.json"
        base_dir = path
    else:
        manifest_file = path
        base_dir = path.parent

    if not manifest_file.exists():
        raise FileNotFoundError(f"Baseline manifest file '{manifest_file}' not found.")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    scenarios_by_id: Dict[str, Dict[str, Any]] = {}

    # 1. First parse scenarios array if present in manifest.json
    if "scenarios" in manifest_data and isinstance(manifest_data["scenarios"], list):
        for item in manifest_data["scenarios"]:
            s_id = item.get("scenario_id") or item.get("benchmark_id")
            if not s_id:
                continue

            dim_scores = item.get("dimension_scores", {})
            if isinstance(dim_scores, list):
                # Convert list of {dimension, score} dicts to dict
                dim_scores = {d["dimension"]: d["score"] for d in dim_scores if "dimension" in d and "score" in d}

            scenarios_by_id[s_id] = {
                "scenario_id": s_id,
                "scenario_name": item.get("scenario_name") or item.get("name") or s_id,
                "overall_score": float(item.get("overall_score", 0.0)),
                "passed": bool(item.get("passed", False)),
                "audit_gate_decision": item.get("audit_gate_decision") or item.get("auditor_gate") or "PASS",
                "dimension_scores": dim_scores,
                "report_path": item.get("report_path", ""),
                "itinerary_path": item.get("itinerary_path", ""),
            }

    # 2. Also scan base_dir for any *_report.json files to supplement detailed dimension scores
    if base_dir.exists() and base_dir.is_dir():
        for fname in os.listdir(base_dir):
            if fname.endswith("_report.json") and fname != "manifest.json" and fname != "regression_report.json":
                report_filepath = base_dir / fname
                try:
                    with open(report_filepath, "r", encoding="utf-8") as f:
                        rep = json.load(f)
                    s_id = rep.get("benchmark_id") or rep.get("scenario_id")
                    if not s_id:
                        continue

                    dim_scores = {}
                    for ds in rep.get("dimension_scores", []):
                        if isinstance(ds, dict) and "dimension" in ds and "score" in ds:
                            dim_scores[ds["dimension"]] = float(ds["score"])

                    agent_meta = rep.get("agent_metadata", {})
                    audit_gate = agent_meta.get("audit_gate_decision", "PASS")

                    scenarios_by_id[s_id] = {
                        "scenario_id": s_id,
                        "scenario_name": rep.get("benchmark_name") or rep.get("scenario_name") or s_id,
                        "overall_score": float(rep.get("overall_score", 0.0)),
                        "passed": bool(rep.get("passed", False)),
                        "audit_gate_decision": audit_gate,
                        "dimension_scores": dim_scores,
                        "report_path": fname,
                        "itinerary_path": rep.get("itinerary_path", ""),
                    }
                except Exception:
                    pass

    return {
        "manifest": manifest_data,
        "scenarios": scenarios_by_id,
    }
