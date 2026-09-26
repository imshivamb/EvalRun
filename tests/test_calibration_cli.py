"""CLI and blinded label-helper tests for the calibration prelude."""

import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from cli.calibration import harvest_calibration_command
from cli.main import create_parser
from framework.calibration.harvest import harvest_records
from framework.calibration.label_server import run_label_server
from framework.calibration.schema import TRAVEL_AND_SUPPORT_DIMENSIONS
from framework.calibration.store import write_corpus

DECISIONS = {
    "release": "approve",
    "hard_failure": "no",
    "policy_violation": "no",
    "needs_human_review": "no",
    "primary_failure_category": "none",
    "rater_confidence": "certain",
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class TestCalibrationCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.results = self.temp_dir / "results"
        self.scenarios = self.temp_dir / "evals" / "scenarios"
        self.dest = self.temp_dir / "evals" / "calibration"
        _write(
            self.scenarios / "travel-agent" / "budget-constrained-itinerary.md",
            "---\nbenchmark_id: travel-planning-budget\nprofile: travel-agent\n---\n\n# Budget\n",
        )
        run_dir = self.results / "live-gemini-001"
        stem = run_dir / "gemini-3_7-flash_travel-planning-budget"
        _write(stem.with_name(stem.name + "_itinerary.md"), "Secret-free itinerary body")
        _write_json(
            stem.with_name(stem.name + "_report.json"),
            {
                "benchmark_id": "travel-planning-budget",
                "model_name": "gemini-3.7-flash",
                "profile": "travel-agent",
                "overall_score": 84.0,
            },
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_harvest_calibration_cli_writes_manifest(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "harvest-calibration",
                "--results",
                str(self.results),
                "--scenarios",
                str(self.scenarios),
                "--output",
                str(self.dest),
            ]
        )
        code = harvest_calibration_command(args)
        self.assertEqual(code, 0)
        manifest = json.loads((self.dest / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["unique_count"], 1)
        self.assertEqual(len(manifest["cases"]), 1)
        case_id = manifest["cases"][0]["case_id"]
        meta = json.loads(
            (self.dest / "cases" / case_id / "meta.json").read_text(encoding="utf-8")
        )
        self.assertEqual(meta["harvested_judge_overall"], 84.0)


class TestCalibrationLabelHelper(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.results = self.temp_dir / "results"
        self.scenarios = self.temp_dir / "evals" / "scenarios"
        self.dest = self.temp_dir / "evals" / "calibration"
        _write(
            self.scenarios / "travel-agent" / "budget-constrained-itinerary.md",
            "---\nbenchmark_id: travel-planning-budget\nprofile: travel-agent\n---\n\n# Budget prompt\n",
        )
        run_dir = self.results / "live-gemini-001"
        stem = run_dir / "gemini-3_7-flash_travel-planning-budget"
        _write(stem.with_name(stem.name + "_itinerary.md"), "Rater-visible itinerary only")
        _write_json(
            stem.with_name(stem.name + "_report.json"),
            {
                "benchmark_id": "travel-planning-budget",
                "model_name": "gemini-3.7-flash",
                "profile": "travel-agent",
                "overall_score": 84.0,
            },
        )
        records = harvest_records(self.results, self.scenarios)
        write_corpus(records, self.dest, scenarios_root=self.scenarios)
        self.case_id = records[0].case_id
        self.server = run_label_server(
            corpus_dir=self.dest,
            host="127.0.0.1",
            port=0,
            allow_incomplete_corpus=True,
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.temp_dir)

    def _session_token(self) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/session") as resp:
            return json.loads(resp.read().decode("utf-8"))["token"]

    def test_case_get_hides_harvested_judge_score(self):
        url = f"http://127.0.0.1:{self.port}/api/case/{self.case_id}"
        with urllib.request.urlopen(url) as resp:
            body = resp.read().decode("utf-8")
        self.assertNotIn("harvested_judge_overall", body)
        self.assertNotIn("84.0", body)
        payload = json.loads(body)
        self.assertIn("Budget prompt", payload["scenario"])
        self.assertIn("Rater-visible itinerary only", payload["output"])
        self.assertNotIn("meta", payload)

    def test_post_rejects_non_step_five_score(self):
        token = self._session_token()
        scores = {name: 80 for name in TRAVEL_AND_SUPPORT_DIMENSIONS}
        scores["Planning Quality"] = 73
        payload = json.dumps(
            {
                "case_id": self.case_id,
                "rater_id": "shivam",
                "schema_version": 2,
                "scale": "0-100-step-5",
                "scores": scores,
                "decisions": DECISIONS,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/label",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-EvalRun-UI-Token": token,
            },
        )
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(req)
        self.assertEqual(raised.exception.code, 400)
        self.assertFalse((self.dest / "cases" / self.case_id / "labels.json").exists())

    def test_post_writes_labels_json(self):
        token = self._session_token()
        scores = {name: 70 for name in TRAVEL_AND_SUPPORT_DIMENSIONS}
        payload = json.dumps(
            {
                "case_id": self.case_id,
                "rater_id": "shivam",
                "schema_version": 2,
                "scale": "0-100-step-5",
                "scores": scores,
                "decisions": DECISIONS,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/label",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-EvalRun-UI-Token": token,
            },
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
        labels = json.loads(
            (self.dest / "cases" / self.case_id / "labels.json").read_text(encoding="utf-8")
        )
        self.assertEqual(labels["scores"]["Planning Quality"], 70)
        self.assertEqual(labels["rater_id"], "shivam")
        self.assertEqual(labels["schema_version"], 2)
        self.assertEqual(labels["decisions"], DECISIONS)
        manifest = json.loads((self.dest / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["cases"][0]["labels_complete"])


if __name__ == "__main__":
    unittest.main()
