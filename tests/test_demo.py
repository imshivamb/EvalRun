"""The offline demo replays the packaged recording of a real run, unchanged."""

import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from cli.demo import load_recording, run_demo


class TestDemoReplay(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.recording = load_recording()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_recording_carries_provenance_and_several_trials(self):
        provenance = self.recording["provenance"]
        for key in ("run_id", "recorded_at_utc", "target_model", "judge_model", "command"):
            self.assertTrue(provenance[key])
        self.assertNotIn("api-key", provenance["command"])
        self.assertGreaterEqual(len(self.recording["trials"]), 2)

    def test_demo_reports_the_recorded_scores(self):
        with redirect_stdout(StringIO()) as printed:
            self.assertEqual(run_demo(self.temp_dir), 0)

        with open(os.path.join(self.temp_dir, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        recorded_scores = [t["overall_score"] for t in self.recording["trials"]]
        stats = manifest["scenarios"][0]["statistics"]
        self.assertEqual(manifest["replayed_from"], self.recording["provenance"])
        self.assertEqual(stats["trials"], len(recorded_scores))
        self.assertAlmostEqual(stats["score_mean"], sum(recorded_scores) / len(recorded_scores))
        self.assertIn("Replaying a real recorded run", printed.getvalue())

        with open(os.path.join(self.temp_dir, "report.html"), encoding="utf-8") as f:
            report = f.read()
        self.assertIn("Trial Statistics", report)
        first_output_line = self.recording["trials"][0]["agent_output"].strip().splitlines()[0]
        self.assertIn(first_output_line[:40].replace("&", "&amp;"), report)


if __name__ == "__main__":
    unittest.main()
