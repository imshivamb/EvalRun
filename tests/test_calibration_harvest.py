"""Tests for harvesting unique calibration cases from retained eval outputs."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from framework.calibration.harvest import harvest_records
from framework.calibration.schema import content_sha256
from framework.calibration.store import write_corpus


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _itinerary_report(
    results_root: Path,
    run_name: str,
    scenario_id: str,
    output: str,
    overall: float,
    model_name: str = "gemini-3.7-flash",
    profile: str = "travel-agent",
) -> None:
    slug = model_name.replace(".", "_")
    stem = results_root / run_name / f"{slug}_{scenario_id}"
    _write(stem.with_name(stem.name + "_itinerary.md"), output)
    _write_json(
        stem.with_name(stem.name + "_report.json"),
        {
            "benchmark_id": scenario_id,
            "benchmark_name": scenario_id,
            "model_name": model_name,
            "profile": profile,
            "overall_score": overall,
        },
    )


class TestCalibrationHarvest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.results = self.temp_dir / "results"
        self.scenarios = self.temp_dir / "evals" / "scenarios"
        self.dest = self.temp_dir / "evals" / "calibration"
        scenario_md = (
            "---\n"
            "benchmark_id: travel-planning-budget\n"
            "profile: travel-agent\n"
            "---\n\n"
            "# Budget scenario\n"
        )
        _write(
            self.scenarios / "travel-agent" / "budget-constrained-itinerary.md",
            scenario_md,
        )
        _write(
            self.scenarios / "travel-agent" / "mid-trip-replanning.md",
            "---\nbenchmark_id: travel-mid-trip-replanning\nprofile: travel-agent\n---\n\n# Replan\n",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_identical_itineraries_collapse_to_one_record(self):
        text = "Day 1: Seoul hostel\n\nDay 2: Tokyo"
        _itinerary_report(self.results, "live-a", "travel-planning-budget", text, 84.0)
        _itinerary_report(
            self.results,
            "live-b",
            "travel-planning-budget",
            "Day 1: Seoul hostel\nDay 2: Tokyo\n",
            90.0,
        )
        records = harvest_records(self.results, self.scenarios)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].content_sha256, content_sha256(text))
        self.assertEqual(records[0].harvested_judge_overall, 84.0)

    def test_distinct_texts_are_both_kept(self):
        _itinerary_report(
            self.results, "run-a", "travel-planning-budget", "Plan alpha unique", 80.0
        )
        _itinerary_report(
            self.results, "run-b", "travel-planning-budget", "Plan beta unique", 70.0
        )
        records = harvest_records(self.results, self.scenarios)
        outputs = {record.output_text for record in records}
        self.assertEqual(outputs, {"Plan alpha unique", "Plan beta unique"})

    def test_write_corpus_stores_judge_score_in_meta_not_labels(self):
        _itinerary_report(
            self.results, "live-gemini-001", "travel-planning-budget", "Unique plan C", 84.0
        )
        records = harvest_records(self.results, self.scenarios)
        manifest = write_corpus(records, self.dest, scenarios_root=self.scenarios)
        self.assertEqual(manifest["unique_count"], 1)
        self.assertEqual(manifest["diversity_counts"]["Budget"], 1)
        self.assertEqual(manifest["diversity_counts"]["Support triage"], 0)
        self.assertFalse(manifest["diversity_floor_met"])

        case_id = records[0].case_id
        case_dir = self.dest / "cases" / case_id
        meta = json.loads((case_dir / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["harvested_judge_overall"], 84.0)
        self.assertEqual(meta["source"], "harvested")
        self.assertFalse((case_dir / "labels.json").exists())
        self.assertTrue((case_dir / "output.md").exists())
        self.assertTrue((case_dir / "scenario.md").exists())
        self.assertFalse(manifest["cases"][0]["labels_complete"])

    def test_mcp_baseline_and_mcp_outputs_are_harvested(self):
        payload = {
            "benchmark": "travel-mid-trip-replanning",
            "planner_model": "models/gemini-3.5-flash",
            "baseline": {
                "output": "Baseline replanning itinerary unique text",
                "evaluation": {"overall_score": 91.0},
            },
            "mcp": {
                "output": "MCP replanning itinerary unique text",
                "evaluation": {"overall_score": 94.0},
            },
        }
        _write_json(
            self.results / "mcp-constraint-validation" / "mcp-replanning-gemini-3-5-flash.json",
            payload,
        )
        records = harvest_records(self.results, self.scenarios)
        self.assertEqual(len(records), 2)
        scenarios = {record.scenario_id for record in records}
        self.assertEqual(scenarios, {"travel-mid-trip-replanning"})
        texts = {record.output_text for record in records}
        self.assertEqual(
            texts,
            {
                "Baseline replanning itinerary unique text",
                "MCP replanning itinerary unique text",
            },
        )

    def test_custom_and_unknown_scenarios_are_skipped(self):
        _itinerary_report(
            self.results, "custom", "custom-weekend-tokyo", "Tokyo weekend plan", 88.0
        )
        records = harvest_records(self.results, self.scenarios)
        self.assertEqual(records, [])


if __name__ == "__main__":
    unittest.main()
