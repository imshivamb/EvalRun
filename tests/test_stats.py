"""Hand-computed fixtures for interval estimates, percentiles and trial aggregation."""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from cli.formatter import format_trial_statistics
from cli.main import create_parser, run_command
from framework.evaluation.runner import BenchmarkRunner
from framework.evaluation.trials import aggregate_trials, summarize_trials
from framework.models import DimensionScore, EvaluationResult
from framework.stats import (
    mean_interval,
    percentile,
    sample_std,
    t_critical_95,
    wilson_interval,
)

SCENARIO = "evals/scenarios/travel-agent/budget-constrained-itinerary.md"


def make_result(score, passed=True, latency=None, audit=None, dims=None):
    metadata = {}
    if latency is not None:
        metadata["run_trace"] = {"latency_seconds": latency}
    if audit is not None:
        metadata["audit_gate_decision"] = audit
    return EvaluationResult(
        benchmark_id="scenario-a",
        benchmark_name="Scenario A",
        overall_score=score,
        dimension_scores=[DimensionScore(name, value, "r") for name, value in (dims or {}).items()],
        passed=passed,
        agent_metadata=metadata,
    )


class TestIntervals(unittest.TestCase):
    def test_wilson_seven_of_ten(self):
        low, high = wilson_interval(7, 10)
        self.assertAlmostEqual(low, 0.3968, places=4)
        self.assertAlmostEqual(high, 0.8922, places=4)

    def test_wilson_zero_successes_starts_at_zero(self):
        low, high = wilson_interval(0, 5)
        self.assertEqual(low, 0.0)
        self.assertAlmostEqual(high, 0.4345, places=4)

    def test_wilson_all_successes_ends_at_one(self):
        low, high = wilson_interval(5, 5)
        self.assertAlmostEqual(low, 0.5655, places=4)
        self.assertEqual(high, 1.0)

    def test_wilson_without_trials_is_none(self):
        self.assertIsNone(wilson_interval(0, 0))

    def test_wilson_rejects_impossible_counts(self):
        with self.assertRaises(ValueError):
            wilson_interval(4, 3)

    def test_t_interval_three_values(self):
        low, high = mean_interval([70.0, 75.0, 80.0])
        # mean 75, s = 5, t(2) = 4.303, half-width = 4.303 * 5 / sqrt(3) = 12.4217
        self.assertAlmostEqual(low, 62.5783, places=3)
        self.assertAlmostEqual(high, 87.4217, places=3)

    def test_t_interval_needs_two_values(self):
        self.assertIsNone(mean_interval([80.0]))

    def test_sample_std_uses_n_minus_one(self):
        self.assertAlmostEqual(sample_std([2, 4, 4, 4, 5, 5, 7, 9]), (32 / 7) ** 0.5, places=10)
        self.assertIsNone(sample_std([1.0]))

    def test_t_critical_is_conservative_between_table_rows(self):
        self.assertEqual(t_critical_95(4), 2.776)
        self.assertEqual(t_critical_95(35), 2.042)
        self.assertAlmostEqual(t_critical_95(500), 1.96, places=2)
        with self.assertRaises(ValueError):
            t_critical_95(0)


class TestPercentile(unittest.TestCase):
    def test_linear_interpolation(self):
        self.assertEqual(percentile([4, 1, 3, 2], 50), 2.5)
        self.assertAlmostEqual(percentile([1, 2, 3, 4], 95), 3.85)

    def test_single_value(self):
        self.assertEqual(percentile([5.0], 95), 5.0)

    def test_rejects_empty_and_out_of_range(self):
        with self.assertRaises(ValueError):
            percentile([], 50)
        with self.assertRaises(ValueError):
            percentile([1.0], 101)


class TestTrialAggregation(unittest.TestCase):
    def setUp(self):
        self.trials = [
            make_result(70.0, passed=False, latency=1.0, dims={"Planning Quality": 60.0}),
            make_result(75.0, passed=True, latency=2.0, dims={"Planning Quality": 70.0}),
            make_result(80.0, passed=True, latency=3.0, dims={"Planning Quality": 80.0}),
        ]

    def test_summary_matches_hand_computation(self):
        stats = summarize_trials(self.trials)
        self.assertEqual((stats.trials, stats.passes), (3, 2))
        self.assertAlmostEqual(stats.pass_rate, 2 / 3)
        low, high = stats.pass_rate_interval
        self.assertAlmostEqual(low, 0.2077, places=4)
        self.assertAlmostEqual(high, 0.9385, places=4)
        self.assertEqual(stats.score_mean, 75.0)
        self.assertAlmostEqual(stats.score_interval[0], 62.5783, places=3)
        self.assertEqual(stats.dimension_means, {"Planning Quality": 70.0})
        self.assertEqual(stats.latency_p50_seconds, 2.0)
        self.assertAlmostEqual(stats.latency_p95_seconds, 2.9)

    def test_score_interval_is_clipped_to_scale(self):
        stats = summarize_trials([make_result(99.0), make_result(100.0)])
        self.assertEqual(stats.score_interval[1], 100.0)

    def test_aggregate_passes_on_mean_score(self):
        aggregated = aggregate_trials(self.trials, pass_threshold=75.0)
        self.assertTrue(aggregated.passed)
        self.assertEqual(aggregated.overall_score, 75.0)
        self.assertEqual(len(aggregated.trial_results), 3)
        self.assertEqual(aggregated.agent_metadata["trials"], 3)
        self.assertFalse(aggregate_trials(self.trials, pass_threshold=75.1).passed)

    def test_any_auditor_block_blocks_the_aggregate(self):
        trials = [make_result(90.0, audit="PASS"), make_result(90.0, audit="BLOCK")]
        aggregated = aggregate_trials(trials, pass_threshold=75.0)
        self.assertEqual(aggregated.agent_metadata["audit_gate_decision"], "BLOCK")

    def test_statistics_serialize_to_json(self):
        payload = summarize_trials(self.trials).to_dict()
        self.assertEqual(json.loads(json.dumps(payload))["passes"], 2)

    def test_terminal_line_shows_pass_rate_interval(self):
        aggregated = aggregate_trials(self.trials, pass_threshold=75.0)
        lines = format_trial_statistics([aggregated])
        self.assertIn("pass 2/3 67% [21-94]", lines[1])
        self.assertIn("score 75.0 [62.6-87.4]", lines[1])
        self.assertIn("p50 2.00s p95 2.90s", lines[1])

    def test_single_trial_prints_no_statistics_block(self):
        result = make_result(80.0)
        result.statistics = summarize_trials([result])
        self.assertEqual(format_trial_statistics([result]), [])


class TestRunnerTrials(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        agent = MagicMock()
        agent.llm.model_name = "test-model"
        self.runner = BenchmarkRunner(agent, MagicMock(), output_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_one_trial_runs_once_and_attaches_statistics(self):
        with patch.object(self.runner, "run", return_value=make_result(80.0)) as run:
            result = self.runner.run_trials(SCENARIO, 1)
        run.assert_called_once_with(SCENARIO)
        self.assertEqual(result.statistics.trials, 1)
        self.assertEqual(result.trial_results, [])

    def test_several_trials_are_numbered_and_aggregated(self):
        outcomes = [make_result(70.0), make_result(80.0), make_result(90.0)]
        with patch.object(self.runner, "run", side_effect=outcomes) as run:
            result = self.runner.run_trials(SCENARIO, 3)
        self.assertEqual(
            [call.kwargs["trial_index"] for call in run.call_args_list], [1, 2, 3]
        )
        self.assertEqual(result.overall_score, 80.0)
        self.assertEqual(result.statistics.trials, 3)
        summaries = [f for f in os.listdir(self.temp_dir) if f.endswith("_report.json")]
        self.assertEqual(len(summaries), 1)

    def test_failed_trial_raises(self):
        with patch.object(self.runner, "run", side_effect=[make_result(80.0), RuntimeError("down")]):
            with self.assertRaises(RuntimeError):
                self.runner.run_trials(SCENARIO, 2)

    def test_rejects_zero_trials(self):
        with self.assertRaises(ValueError):
            self.runner.run_trials(SCENARIO, 0)


class TestTrialsFlag(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _args(self, *extra):
        return create_parser().parse_args([
            "run", "--scenario", SCENARIO, "--agent", "tests.test_cli:DummyAgentClass",
            "--model", "m", "--output", self.temp_dir, *extra,
        ])

    def test_zero_trials_is_a_configuration_error(self):
        self.assertEqual(run_command(self._args("--trials", "0")), 2)

    @patch("cli.main.BenchmarkRunner")
    @patch("cli.main.OpenAICompatibleLLM")
    def test_trials_reach_the_runner_and_manifest(self, _llm, runner_class):
        aggregated = aggregate_trials([make_result(80.0), make_result(90.0)], pass_threshold=75.0)
        runner_class.return_value.run_trials.return_value = aggregated
        self.assertEqual(run_command(self._args("--trials", "2")), 0)
        runner_class.return_value.run_trials.assert_called_once_with(SCENARIO, 2)
        with open(os.path.join(self.temp_dir, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["trials_per_scenario"], 2)
        self.assertEqual(manifest["scenarios"][0]["statistics"]["trials"], 2)


if __name__ == "__main__":
    unittest.main()
