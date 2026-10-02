"""Hand-computed fixtures for the statistical regression gate and its power analysis."""

import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from cli.main import create_parser
from cli.power import power_command
from framework.evaluation.trials import aggregate_trials
from framework.models import DimensionScore, EvaluationResult
from framework.regression import compare_runs
from framework.stats import (
    gate_power,
    minimum_detectable_drop,
    trials_for_power,
    welch_interval,
)


def trial(score, dims=None):
    return EvaluationResult(
        benchmark_id="s1",
        benchmark_name="Scenario One",
        overall_score=score,
        dimension_scores=[DimensionScore(k, v, "r") for k, v in (dims or {"Quality": score}).items()],
        passed=True,
    )


def candidate(scores):
    return aggregate_trials([trial(s) for s in scores], pass_threshold=0.0)


def baseline(scores):
    stats = candidate(scores).statistics.to_dict()
    return {
        "manifest": {"run_id": "base"},
        "scenarios": {
            "s1": {
                "scenario_name": "Scenario One",
                "overall_score": stats["score_mean"],
                "dimension_scores": {"Quality": stats["score_mean"]},
                "statistics": stats,
            }
        },
    }


class TestWelchInterval(unittest.TestCase):
    def test_noisy_drop_interval_contains_zero(self):
        # means 82 vs 74, s = 2 and 4, se = 2.582, df = 2.94 -> 2, t = 4.303
        difference, low, high = welch_interval([80, 82, 84], [70, 74, 78])
        self.assertEqual(difference, -8.0)
        self.assertAlmostEqual(low, -19.110, places=3)
        self.assertAlmostEqual(high, 3.110, places=3)

    def test_consistent_drop_interval_excludes_zero(self):
        # means 82 vs 71, s = 2 and 1, se = 1.291, df = 2.94 -> 2, t = 4.303
        difference, low, high = welch_interval([80, 82, 84], [70, 71, 72])
        self.assertEqual(difference, -11.0)
        self.assertAlmostEqual(low, -16.555, places=3)
        self.assertAlmostEqual(high, -5.445, places=3)

    def test_needs_two_values_per_side(self):
        self.assertIsNone(welch_interval([80], [70, 71]))

    def test_identical_scores_give_a_point_interval(self):
        self.assertEqual(welch_interval([90, 90], [85, 85]), (-5.0, -5.0, -5.0))


class TestGatePower(unittest.TestCase):
    def test_trials_needed_for_eight_point_drop(self):
        # sigma 4, threshold 5: n = 4 gives power 0.649, n = 5 gives 0.804
        self.assertAlmostEqual(gate_power(4, 8, 5, 4), 0.649, places=3)
        self.assertAlmostEqual(gate_power(4, 8, 5, 5), 0.804, places=3)
        self.assertEqual(trials_for_power(4, 8, 5), 5)

    def test_minimum_detectable_drop(self):
        # max(5, 2.306 * 2.530) + 0.8416 * 2.530 = 5.834 + 2.129
        self.assertAlmostEqual(minimum_detectable_drop(4, 5, 5), 7.963, places=3)

    def test_drop_within_threshold_is_unreachable(self):
        self.assertIsNone(trials_for_power(4, 5, 5))
        self.assertLessEqual(gate_power(4, 5, 5, 200), 0.5)


class TestStatisticalComparison(unittest.TestCase):
    def test_noisy_drop_beyond_threshold_does_not_block(self):
        report = compare_runs([candidate([70, 74, 78])], baseline([80, 82, 84]),
                              max_overall_drop=5, max_dim_drop=5, regression_mode="statistical")
        self.assertFalse(report.release_blocked)
        self.assertEqual(report.to_dict()["scenarios"][0]["overall_delta_interval"], [-19.11, 3.11])

    def test_consistent_drop_blocks(self):
        report = compare_runs([candidate([70, 71, 72])], baseline([80, 82, 84]),
                              max_overall_drop=5, max_dim_drop=5, regression_mode="statistical")
        self.assertTrue(report.release_blocked)
        self.assertEqual(report.scenario_comparisons[0].status, "REGRESSED")

    def test_simple_mode_blocks_the_same_noisy_drop(self):
        report = compare_runs([candidate([70, 74, 78])], baseline([80, 82, 84]),
                              max_overall_drop=5, max_dim_drop=5)
        self.assertTrue(report.release_blocked)
        self.assertEqual(report.regression_mode, "simple")

    def test_refuses_single_trial_runs(self):
        with self.assertRaises(ValueError):
            compare_runs([candidate([70, 71])], baseline([80]), regression_mode="statistical")

    def test_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            compare_runs([candidate([70, 71])], baseline([80, 81]), regression_mode="vibes")


class TestPowerCommand(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _run(self, *argv):
        args = create_parser().parse_args(["power", *argv])
        with redirect_stdout(StringIO()) as out:
            code = power_command(args)
        return code, out.getvalue()

    def test_std_reports_hand_computed_values(self):
        code, out = self._run("--std", "4", "--drop", "8", "--trials", "5")
        self.assertEqual(code, 0)
        self.assertIn("8.0", out)
        self.assertRegex(out, r"\|\s+5\s*$|\|\s+5\n")

    def test_baseline_without_trials_is_an_error(self):
        manifest = {"run_id": "b", "scenarios": [{"scenario_id": "s1", "overall_score": 80.0}]}
        path = os.path.join(self.temp_dir, "manifest.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        code, _ = self._run("--baseline", path, "--drop", "8")
        self.assertEqual(code, 2)

    def test_baseline_trials_supply_the_noise(self):
        stats = candidate([80, 82, 84]).statistics.to_dict()
        manifest = {"run_id": "b", "scenarios": [
            {"scenario_id": "s1", "scenario_name": "Scenario One", "overall_score": 82.0, "statistics": stats}
        ]}
        path = os.path.join(self.temp_dir, "manifest.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        code, out = self._run("--baseline", path, "--drop", "8")
        self.assertEqual(code, 0)
        self.assertIn("Scenario One", out)
        self.assertIn("2.00", out)


if __name__ == "__main__":
    unittest.main()
