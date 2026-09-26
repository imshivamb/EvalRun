"""Harvest unique travel/support outputs from retained eval artifacts."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from framework.calibration.schema import content_sha256, make_case_id

ALLOWED_SCENARIO_IDS = frozenset(
    {
        "travel-planning-budget",
        "travel-route-optimization",
        "travel-remote-worker-timezones",
        "travel-mid-trip-replanning",
        "travel-information-gathering-uncertainty",
        "support-urgent-ticket-escalation",
    }
)

DIVERSITY_BUCKETS = {
    "travel-planning-budget": "Budget",
    "travel-route-optimization": "Route Optimization",
    "travel-remote-worker-timezones": "Remote Worker",
    "travel-mid-trip-replanning": "Replanning",
    "travel-information-gathering-uncertainty": "Information Gathering",
    "support-urgent-ticket-escalation": "Support triage",
}

SCENARIO_PROFILES = {
    "support-urgent-ticket-escalation": "support-triage",
}

SKIP_RESULT_DIR_NAMES = frozenset({"demo"})


@dataclass(frozen=True)
class HarvestedRecord:
    case_id: str
    scenario_id: str
    profile: str
    source_tag: str
    source_path: str
    generator_model: str
    harvested_judge_overall: Optional[float]
    output_text: str
    content_sha256: str
    source: str = "harvested"


def index_scenarios(scenarios_root: Path) -> Dict[str, Path]:
    """Map benchmark_id -> scenario markdown path."""
    mapping: Dict[str, Path] = {}
    if not scenarios_root.exists():
        return mapping
    for path in sorted(scenarios_root.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("benchmark_id:"):
                mapping[line.split(":", 1)[1].strip()] = path
                break
    return mapping


def harvest_records(results_root: Path, scenarios_root: Path) -> List[HarvestedRecord]:
    """Collect unique allowed-scenario outputs from itineraries and MCP JSON."""
    scenario_files = index_scenarios(scenarios_root)
    candidates: List[HarvestedRecord] = []
    if results_root.exists():
        candidates.extend(_harvest_itineraries(results_root, scenario_files))
        candidates.extend(_harvest_mcp(results_root, scenario_files))
    return _dedupe(candidates)


def _dedupe(records: List[HarvestedRecord]) -> List[HarvestedRecord]:
    seen: Dict[str, HarvestedRecord] = {}
    for record in sorted(records, key=lambda item: (item.source_path, item.case_id)):
        if record.content_sha256 not in seen:
            seen[record.content_sha256] = record
    return list(seen.values())


def _harvest_itineraries(
    results_root: Path, scenario_files: Dict[str, Path]
) -> List[HarvestedRecord]:
    records: List[HarvestedRecord] = []
    for itinerary in sorted(results_root.rglob("*_itinerary.md")):
        if _should_skip_path(itinerary, results_root):
            continue
        report_path = itinerary.with_name(
            itinerary.name.replace("_itinerary.md", "_report.json")
        )
        report = _load_json(report_path) if report_path.exists() else {}
        scenario_id = str(report.get("benchmark_id") or "")
        if scenario_id not in ALLOWED_SCENARIO_IDS:
            scenario_id = _scenario_id_from_itinerary_name(itinerary.name) or ""
        if scenario_id not in ALLOWED_SCENARIO_IDS:
            continue
        if scenario_id not in scenario_files:
            continue
        output_text = itinerary.read_text(encoding="utf-8")
        record = _make_record(
            scenario_id=scenario_id,
            profile=str(
                report.get("profile") or SCENARIO_PROFILES.get(scenario_id, "travel-agent")
            ),
            source_tag=itinerary.parent.name,
            source_path=_relative_source(itinerary, results_root),
            generator_model=str(report.get("model_name") or "unknown"),
            harvested_judge_overall=_as_float(report.get("overall_score")),
            output_text=output_text,
        )
        if record is not None:
            records.append(record)
    return records


def _harvest_mcp(
    results_root: Path, scenario_files: Dict[str, Path]
) -> List[HarvestedRecord]:
    records: List[HarvestedRecord] = []
    mcp_root = results_root / "mcp-constraint-validation"
    if not mcp_root.exists():
        return records
    for json_path in sorted(mcp_root.glob("*.json")):
        payload = _load_json(json_path)
        scenario_id = str(payload.get("benchmark") or "")
        if scenario_id not in ALLOWED_SCENARIO_IDS:
            continue
        if scenario_id not in scenario_files:
            continue
        planner = str(payload.get("planner_model") or "unknown")
        for arm in ("baseline", "mcp"):
            block = payload.get(arm)
            if not isinstance(block, dict):
                continue
            output_text = block.get("output")
            if not isinstance(output_text, str) or not output_text.strip():
                continue
            evaluation = (
                block.get("evaluation") if isinstance(block.get("evaluation"), dict) else {}
            )
            record = _make_record(
                scenario_id=scenario_id,
                profile=SCENARIO_PROFILES.get(scenario_id, "travel-agent"),
                source_tag=f"{arm}-{json_path.stem}",
                source_path=f"{_relative_source(json_path, results_root)}#{arm}",
                generator_model=planner,
                harvested_judge_overall=_as_float(evaluation.get("overall_score")),
                output_text=output_text,
            )
            if record is not None:
                records.append(record)
    return records


def _make_record(
    *,
    scenario_id: str,
    profile: str,
    source_tag: str,
    source_path: str,
    generator_model: str,
    harvested_judge_overall: Optional[float],
    output_text: str,
    source: str = "harvested",
) -> Optional[HarvestedRecord]:
    if not output_text.strip():
        return None
    digest = content_sha256(output_text)
    case_id = make_case_id(scenario_id, source_tag, digest)
    return HarvestedRecord(
        case_id=case_id,
        scenario_id=scenario_id,
        profile=profile,
        source_tag=source_tag,
        source_path=source_path,
        generator_model=generator_model,
        harvested_judge_overall=harvested_judge_overall,
        output_text=output_text,
        content_sha256=digest,
        source=source,
    )


def _scenario_id_from_itinerary_name(name: str) -> Optional[str]:
    if not name.endswith("_itinerary.md"):
        return None
    stem = name[: -len("_itinerary.md")]
    for scenario_id in sorted(ALLOWED_SCENARIO_IDS, key=len, reverse=True):
        if stem.endswith(f"_{scenario_id}"):
            return scenario_id
    return None


def _should_skip_path(path: Path, results_root: Path) -> bool:
    try:
        relative = path.relative_to(results_root)
    except ValueError:
        return False
    return any(part in SKIP_RESULT_DIR_NAMES for part in relative.parts)


def _relative_source(path: Path, results_root: Path) -> str:
    try:
        return path.relative_to(results_root.parent).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
