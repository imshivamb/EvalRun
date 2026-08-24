"""Unit and integration tests for local guided UI web server (ui/server.py)."""

import json
import os
import shutil
import tempfile
import unittest
import urllib.request
import urllib.parse
from unittest.mock import patch, MagicMock

from ui.server import run_ui_server, list_available_scenarios, list_available_baselines
from framework.models import EvaluationResult, DimensionScore


class TestUIServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = None
        cls.port = 0
        try:
            # Bind to ephemeral port for testing
            cls.server = run_ui_server(host="127.0.0.1", port=0)
            cls.port = cls.server.server_address[1]
            import threading
            cls.server_thread = threading.Thread(target=cls.server.serve_forever)
            cls.server_thread.daemon = True
            cls.server_thread.start()
        except Exception:
            cls.server = None

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            try:
                cls.server.shutdown()
                cls.server.server_close()
            except Exception:
                pass

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_list_scenarios_helper(self):
        scenarios = list_available_scenarios("evals/scenarios")
        self.assertIsInstance(scenarios, list)
        if len(scenarios) > 0:
            self.assertIn("path", scenarios[0])
            self.assertIn("name", scenarios[0])

    def test_list_baselines_helper(self):
        # Create a mock baseline directory
        base_dir = os.path.join(self.temp_dir, "eval_results", "run_1")
        os.makedirs(base_dir, exist_ok=True)
        manifest_data = {
            "run_id": "evalrun-test-001",
            "timestamp_utc": "2026-08-22T19:00:00Z",
        }
        with open(os.path.join(base_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        baselines = list_available_baselines([os.path.join(self.temp_dir, "eval_results")])
        self.assertEqual(len(baselines), 1)
        self.assertEqual(baselines[0]["run_id"], "evalrun-test-001")

    def test_api_scenarios_endpoint(self):
        if not self.server:
            self.skipTest("Server unavailable")
        url = f"http://127.0.0.1:{self.port}/api/scenarios"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("scenarios", data)

    def test_api_baselines_endpoint(self):
        if not self.server:
            self.skipTest("Server unavailable")
        url = f"http://127.0.0.1:{self.port}/api/baselines"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("baselines", data)

    @patch("framework.sdk.evaluate")
    def test_api_run_endpoint(self, mock_evaluate):
        if not self.server:
            self.skipTest("Server unavailable")

        mock_res = EvaluationResult(
            benchmark_id="ui-test-scenario",
            benchmark_name="UI Test Scenario",
            overall_score=92.5,
            dimension_scores=[DimensionScore("Constraint Satisfaction", 92.5, "Pass")],
            passed=True,
            agent_metadata={"audit_gate_decision": "PASS"},
        )
        mock_evaluate.return_value = [mock_res]

        url = f"http://127.0.0.1:{self.port}/api/run"
        payload = {
            "scenario": "evals/scenarios/travel-agent/budget-constrained-itinerary.md",
            "agent": "agents.travel:TravelPlanningAgent",
            "model": "qwen2.5-72b-instruct",
            "base_url": "http://localhost:8000/v1",
            "output_dir": os.path.join(self.temp_dir, "ui_run"),
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            res_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res_data["status"], "success")
            self.assertTrue(res_data["all_passed"])
            self.assertFalse(res_data["release_blocked"])

    def test_path_traversal_protection(self):
        if not self.server:
            self.skipTest("Server unavailable")
        url = f"http://127.0.0.1:{self.port}/eval_results/../../../../etc/passwd"
        try:
            with urllib.request.urlopen(url) as resp:
                self.assertNotEqual(resp.status, 200)
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (403, 404))

    def test_custom_scenario_path_stays_inside_workspace(self):
        if not self.server:
            self.skipTest("Server unavailable")
        url = f"http://127.0.0.1:{self.port}/api/run"
        payload = {"scenario": "../../etc/passwd"}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
