"""Unit tests for baseline manifest loader and regression comparator engine."""

import json
import os
import shutil
import tempfile
import unittest

from framework.models import EvaluationResult, DimensionScore
from framework.regression import load_baseline_manifest, compare_runs, RegressionReport


class TestRegressionEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Create mock baseline files in temp_dir
        self.manifest_data = {
            "run_id": "baseline-run-001",
            "framework_version": "0.4.0",
            "scenarios": [
                {
                    "scenario_id": "budget-constrained-itinerary",
                    "scenario_name": "Budget Constrained Itinerary",
                    "overall_score": 90.0,
                    "passed": True,
                    "audit_gate_decision": "PASS",
                    "dimension_scores": {
                        "Constraint Satisfaction": 95.0,
                        "Planning Quality": 85.0,
                    },
                },
                {
                    "scenario_id": "urgent-ticket-escalation",
                    "scenario_name": "Urgent Ticket Escalation",
                    "overall_score": 88.0,
                    "passed": True,
                    "audit_gate_decision": "PASS",
                    "dimension_scores": {
                        "SLA Compliance": 90.0,
                        "Escalation Correctness": 86.0,
                    },
                },
            ],
        }

        self.manifest_file = os.path.join(self.temp_dir, "manifest.json")
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(self.manifest_data, f, indent=2)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_load_baseline_manifest_directory_and_file(self):
        # Test loading from directory
        baseline1 = load_baseline_manifest(self.temp_dir)
        self.assertIn("scenarios", baseline1)
        self.assertIn("budget-constrained-itinerary", baseline1["scenarios"])

        # Test loading from file
        baseline2 = load_baseline_manifest(self.manifest_file)
        self.assertEqual(baseline2["manifest"]["run_id"], "baseline-run-001")
        self.assertIn("urgent-ticket-escalation", baseline2["scenarios"])

    def test_compare_runs_no_regression(self):
        baseline_data = load_baseline_manifest(self.manifest_file)

        # Candidate with improved scores
        cand_results = [
            EvaluationResult(
                benchmark_id="budget-constrained-itinerary",
                benchmark_name="Budget Constrained Itinerary",
                overall_score=92.0,
                dimension_scores=[
                    DimensionScore("Constraint Satisfaction", 95.0, "Excellent"),
                    DimensionScore("Planning Quality", 89.0, "Better"),
                ],
                passed=True,
                agent_metadata={"audit_gate_decision": "PASS"},
            ),
            EvaluationResult(
                benchmark_id="urgent-ticket-escalation",
                benchmark_name="Urgent Ticket Escalation",
                overall_score=88.0,
                dimension_scores=[
                    DimensionScore("SLA Compliance", 90.0, "Great"),
                    DimensionScore("Escalation Correctness", 86.0, "Correct"),
                ],
                passed=True,
                agent_metadata={"audit_gate_decision": "PASS"},
            ),
        ]

        report = compare_runs(cand_results, baseline_data, max_overall_drop=5.0, max_dim_drop=10.0)
        self.assertFalse(report.regression_detected)
        self.assertFalse(report.release_blocked)
        self.assertEqual(len(report.scenario_comparisons), 2)
        self.assertEqual(report.scenario_comparisons[0].overall_delta, 2.0)

    def test_compare_runs_overall_regression_detected(self):
        baseline_data = load_baseline_manifest(self.manifest_file)

        # Candidate with dropped overall score (-10 points)
        cand_results = [
            EvaluationResult(
                benchmark_id="budget-constrained-itinerary",
                benchmark_name="Budget Constrained Itinerary",
                overall_score=79.0,  # Drop of 11.0 (from 90.0)
                dimension_scores=[
                    DimensionScore("Constraint Satisfaction", 80.0, "Okay"),
                    DimensionScore("Planning Quality", 78.0, "Lower"),
                ],
                passed=True,
                agent_metadata={"audit_gate_decision": "PASS"},
            ),
            EvaluationResult(
                benchmark_id="urgent-ticket-escalation",
                benchmark_name="Urgent Ticket Escalation",
                overall_score=88.0,
                dimension_scores=[
                    DimensionScore("SLA Compliance", 90.0, "Great"),
                    DimensionScore("Escalation Correctness", 86.0, "Correct"),
                ],
                passed=True,
                agent_metadata={"audit_gate_decision": "PASS"},
            ),
        ]

        report = compare_runs(cand_results, baseline_data, max_overall_drop=5.0)
        self.assertTrue(report.regression_detected)
        self.assertTrue(report.release_blocked)

        sc_comp = [c for c in report.scenario_comparisons if c.scenario_id == "budget-constrained-itinerary"][0]
        self.assertTrue(sc_comp.is_regression)
        self.assertEqual(sc_comp.overall_delta, -11.0)
        self.assertEqual(sc_comp.status, "REGRESSED")

    def test_compare_runs_missing_scenario_in_candidate(self):
        baseline_data = load_baseline_manifest(self.manifest_file)

        # Candidate missing 'urgent-ticket-escalation'
        cand_results = [
            EvaluationResult(
                benchmark_id="budget-constrained-itinerary",
                benchmark_name="Budget Constrained Itinerary",
                overall_score=90.0,
                dimension_scores=[],
                passed=True,
                agent_metadata={"audit_gate_decision": "PASS"},
            )
        ]

        report = compare_runs(cand_results, baseline_data)
        self.assertTrue(report.regression_detected)
        self.assertTrue(report.release_blocked)

        missing = [c for c in report.scenario_comparisons if c.scenario_id == "urgent-ticket-escalation"][0]
        self.assertEqual(missing.status, "MISSING_IN_CANDIDATE")
        self.assertTrue(missing.is_regression)

    def test_compare_runs_new_candidate_scenario(self):
        baseline_data = load_baseline_manifest(self.manifest_file)

        # Candidate includes a new scenario not in baseline
        cand_results = [
            EvaluationResult(
                benchmark_id="budget-constrained-itinerary",
                benchmark_name="Budget Constrained Itinerary",
                overall_score=90.0,
                dimension_scores=[],
                passed=True,
                agent_metadata={"audit_gate_decision": "PASS"},
            ),
            EvaluationResult(
                benchmark_id="urgent-ticket-escalation",
                benchmark_name="Urgent Ticket Escalation",
                overall_score=88.0,
                dimension_scores=[],
                passed=True,
                agent_metadata={"audit_gate_decision": "PASS"},
            ),
            EvaluationResult(
                benchmark_id="new-feature-scenario",
                benchmark_name="New Feature Scenario",
                overall_score=85.0,
                dimension_scores=[],
                passed=True,
                agent_metadata={"audit_gate_decision": "PASS"},
            ),
        ]

        report = compare_runs(cand_results, baseline_data)
        self.assertFalse(report.regression_detected)
        self.assertFalse(report.release_blocked)

        new_sc = [c for c in report.scenario_comparisons if c.scenario_id == "new-feature-scenario"][0]
        self.assertIn("NEW", new_sc.status)
        self.assertFalse(new_sc.is_regression)


if __name__ == "__main__":
    unittest.main()
