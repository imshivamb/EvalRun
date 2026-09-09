"""Guards that published benchmark numbers match the committed evidence artifact."""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "docs" / "evidence" / "canonical-results.json"
COMPARISON_PATH = REPO_ROOT / "results" / "multi-model-benchmarks" / "comparison.md"
MCP_FINDINGS_PATH = REPO_ROOT / "results" / "mcp-constraint-validation" / "mcp-validation-findings.md"
AUDITOR_FINDINGS_PATH = REPO_ROOT / "results" / "independent-auditor" / "auditor-validation-findings.md"


class TestCanonicalEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.comparison = COMPARISON_PATH.read_text(encoding="utf-8")
        cls.mcp_findings = MCP_FINDINGS_PATH.read_text(encoding="utf-8")
        cls.auditor_findings = AUDITOR_FINDINGS_PATH.read_text(encoding="utf-8")

    def test_auditor_specificity_is_disclosed(self):
        sensitivity = self.evidence["auditor_sensitivity"]
        self.assertEqual(sensitivity["true_positive"], 18)
        self.assertEqual(sensitivity["false_positive"], 2)
        self.assertEqual(sensitivity["true_negative"], 0)
        self.assertEqual(sensitivity["false_negative"], 0)
        self.assertEqual(sensitivity["specificity_pct"], 0.0)
        self.assertEqual(sensitivity["recall_pct"], 100.0)

    def test_five_scenario_suite_is_gemini_only(self):
        models = self.evidence["five_scenario_regression"]["models"]
        self.assertEqual(set(models), {"Gemini 3.1 Pro", "Gemini 3.5 Flash"})
        pro = models["Gemini 3.1 Pro"]["scores"]
        self.assertEqual(pro["Budget"]["v1"], 84.0)
        self.assertEqual(pro["Remote Worker"]["v2"], 93.1)
        flash_replan = models["Gemini 3.5 Flash"]["scores"]["Replanning"]
        self.assertEqual(flash_replan["status"], "missing_or_failed_run")

    def test_mcp_audits_match_published_overall_scores(self):
        by_model = {run["model"]: run for run in self.evidence["mcp_replanning_audits"]["runs"]}
        self.assertAlmostEqual(by_model["GPT-5.6 Terra"]["v2_overall"], 86.4)
        self.assertAlmostEqual(by_model["GPT-5.6 Terra"]["v21_overall"], 87.3)
        self.assertAlmostEqual(by_model["Gemini 3.1 Pro"]["v21_overall"], 99.0)
        self.assertAlmostEqual(
            by_model["Gemini 3.1 Pro"]["v21_dimensions"]["Information Accuracy"],
            95.0,
        )
        self.assertAlmostEqual(
            by_model["Gemini 3.5 Flash"]["v21_dimensions"]["Information Accuracy"],
            100.0,
        )

    def test_published_markdown_does_not_use_local_file_urls(self):
        self.assertNotIn("file:///", self.comparison)
        self.assertNotIn("file:///", self.mcp_findings)
        self.assertNotIn("file:///", self.auditor_findings)
        self.assertNotIn("meta/llama-3.1-8b-instruct", self.comparison)
        self.assertIn("not published here", self.comparison)
        self.assertIn("docs/evidence/canonical-results.json", self.comparison)
        self.assertIn("100.00 | 95.00 | -5.00", self.mcp_findings)
        self.assertIn("85.00 | 100.00 | +15.00", self.mcp_findings)


if __name__ == "__main__":
    unittest.main()
