"""Tests for filling remaining calibration slots without calling a judge."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from framework.calibration.generate import generate_cases
from framework.calibration.harvest import DIVERSITY_BUCKETS, harvest_records
from framework.calibration.store import write_corpus


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_scenarios(root: Path) -> None:
    files = {
        "travel-agent/budget-constrained-itinerary.md": "travel-planning-budget",
        "travel-agent/multi-city-route-optimization.md": "travel-route-optimization",
        "travel-agent/remote-worker-timezones.md": "travel-remote-worker-timezones",
        "travel-agent/mid-trip-replanning.md": "travel-mid-trip-replanning",
        "travel-agent/information-gathering-uncertainty.md": "travel-information-gathering-uncertainty",
        "support-triage/urgent-ticket-escalation.md": "support-urgent-ticket-escalation",
    }
    for rel, scenario_id in files.items():
        profile = "support-triage" if scenario_id.startswith("support-") else "travel-agent"
        _write(
            root / rel,
            (
                f"---\nbenchmark_id: {scenario_id}\nprofile: {profile}\n---\n\n"
                f"# Description\n\nSeed {scenario_id}\n\n"
                f"# User Prompt\n\nPrompt for {scenario_id}\n"
            ),
        )


class TestCalibrationGenerate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.scenarios = self.temp_dir / "evals" / "scenarios"
        self.dest = self.temp_dir / "evals" / "calibration"
        self.results = self.temp_dir / "results"
        _seed_scenarios(self.scenarios)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_fills_missing_buckets_before_repeating_budget(self):
        _write(
            self.results / "live" / "gemini_travel-planning-budget_itinerary.md",
            "Harvested budget itinerary",
        )
        _write(
            self.results / "live" / "gemini_travel-planning-budget_report.json",
            json.dumps(
                {
                    "benchmark_id": "travel-planning-budget",
                    "model_name": "gemini-3.7-flash",
                    "profile": "travel-agent",
                    "overall_score": 84.0,
                }
            ),
        )
        records = harvest_records(self.results, self.scenarios)
        write_corpus(records, self.dest, scenarios_root=self.scenarios)
        calls = []

        def runner(scenario_id: str, prompt: str) -> str:
            calls.append(scenario_id)
            return f"generated unique output for {scenario_id} {len(calls)}"

        result = generate_cases(
            dest=self.dest,
            scenarios_root=self.scenarios,
            run_agent=runner,
            generator_model="gemini-3.7-flash",
            target_min=6,
            target_max=8,
        )
        self.assertEqual(result["unique_count"], 6)
        self.assertTrue(result["diversity_floor_met"])
        self.assertEqual(result["diversity_counts"]["Budget"], 1)
        for bucket in DIVERSITY_BUCKETS.values():
            self.assertGreaterEqual(result["diversity_counts"][bucket], 1)
        self.assertNotIn("travel-planning-budget", calls)
        generated = [
            case for case in result["cases"] if case["source"] == "generated"
        ]
        self.assertEqual(len(generated), 5)
        case_dir = self.dest / "cases" / generated[0]["case_id"]
        meta = json.loads((case_dir / "meta.json").read_text(encoding="utf-8"))
        self.assertIsNone(meta["harvested_judge_overall"])
        self.assertEqual(meta["source"], "generated")
        self.assertFalse((case_dir / "labels.json").exists())

    def test_duplicate_outputs_are_skipped_and_empty_bucket_is_not_padded(self):
        def runner(scenario_id: str, prompt: str) -> str:
            return "the same itinerary every time"

        result = generate_cases(
            dest=self.dest,
            scenarios_root=self.scenarios,
            run_agent=runner,
            generator_model="gemini-3.7-flash",
            target_min=6,
            target_max=8,
        )
        self.assertLess(result["unique_count"], 6)
        self.assertFalse(result["diversity_floor_met"])
        self.assertIn("travel-route-optimization", result["failed_scenarios"])
        self.assertEqual(result["diversity_counts"]["Budget"], 1)
        self.assertEqual(result["diversity_counts"]["Route Optimization"], 0)

    def test_stops_once_floor_and_minimum_are_met(self):
        n = {"count": 0}

        def runner(scenario_id: str, prompt: str) -> str:
            n["count"] += 1
            return f"unique {scenario_id} {n['count']}"

        result = generate_cases(
            dest=self.dest,
            scenarios_root=self.scenarios,
            run_agent=runner,
            generator_model="gemini-3.7-flash",
            target_min=6,
            target_max=20,
        )
        self.assertEqual(result["unique_count"], 6)
        self.assertEqual(n["count"], 6)
        self.assertTrue(result["diversity_floor_met"])


if __name__ == "__main__":
    unittest.main()
