"""Write a frozen unlabeled calibration corpus to disk."""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from framework.calibration.harvest import (
    DIVERSITY_BUCKETS,
    HarvestedRecord,
    index_scenarios,
)


def write_corpus(
    records: Iterable[HarvestedRecord],
    dest: Path,
    scenarios_root: Path,
) -> Dict[str, Any]:
    """Persist harvested cases and return the written manifest."""
    dest = Path(dest)
    cases_root = dest / "cases"
    cases_root.mkdir(parents=True, exist_ok=True)
    scenario_files = index_scenarios(scenarios_root)
    for record in records:
        scenario_path = scenario_files.get(record.scenario_id)
        if scenario_path is None:
            raise FileNotFoundError(
                f"No scenario markdown mapped for {record.scenario_id}"
            )
        case_dir = cases_root / record.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "scenario.md").write_text(
            scenario_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (case_dir / "output.md").write_text(record.output_text, encoding="utf-8")
        meta = {
            "case_id": record.case_id,
            "scenario_id": record.scenario_id,
            "profile": record.profile,
            "source": record.source,
            "source_path": record.source_path,
            "generator_model": record.generator_model,
            "harvested_judge_overall": record.harvested_judge_overall,
            "content_sha256": record.content_sha256,
        }
        (case_dir / "meta.json").write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8"
        )

    return rebuild_manifest(dest)


def rebuild_manifest(dest: Path) -> Dict[str, Any]:
    """Rebuild manifest.json from case directories currently on disk."""
    dest = Path(dest)
    diversity_counts = {bucket: 0 for bucket in DIVERSITY_BUCKETS.values()}
    cases: List[Dict[str, Any]] = []
    cases_root = dest / "cases"
    if cases_root.exists():
        for case_dir in sorted(path for path in cases_root.iterdir() if path.is_dir()):
            meta_path = case_dir / "meta.json"
            if not meta_path.exists():
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            scenario_id = str(meta.get("scenario_id") or "")
            bucket = DIVERSITY_BUCKETS.get(scenario_id)
            if bucket:
                diversity_counts[bucket] += 1
            cases.append(
                {
                    "case_id": str(meta.get("case_id") or case_dir.name),
                    "scenario_id": scenario_id,
                    "source": str(meta.get("source") or "harvested"),
                    "labels_complete": (case_dir / "labels.json").exists(),
                }
            )
    unique_count = len(cases)
    diversity_floor_met = all(count >= 1 for count in diversity_counts.values())
    manifest = {
        "unique_count": unique_count,
        "diversity_floor_met": diversity_floor_met,
        "diversity_counts": diversity_counts,
        "cases": cases,
    }
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def build_manifest(dest: Path, records: Iterable[HarvestedRecord]) -> Dict[str, Any]:
    diversity_counts = {bucket: 0 for bucket in DIVERSITY_BUCKETS.values()}
    cases: List[Dict[str, Any]] = []
    for record in sorted(records, key=lambda item: item.case_id):
        bucket = DIVERSITY_BUCKETS.get(record.scenario_id)
        if bucket:
            diversity_counts[bucket] += 1
        labels_path = dest / "cases" / record.case_id / "labels.json"
        cases.append(
            {
                "case_id": record.case_id,
                "scenario_id": record.scenario_id,
                "source": record.source,
                "labels_complete": labels_path.exists(),
            }
        )
    unique_count = len(cases)
    diversity_floor_met = all(count >= 1 for count in diversity_counts.values())
    return {
        "unique_count": unique_count,
        "diversity_floor_met": diversity_floor_met,
        "diversity_counts": diversity_counts,
        "cases": cases,
    }
