"""Tests for calibration corpus hashing and human-label validation."""

import unittest

from framework.calibration.schema import (
    LABEL_SCHEMA_VERSION,
    TRAVEL_AND_SUPPORT_DIMENSIONS,
    content_sha256,
    make_case_id,
    normalize_output_text,
    validate_labels,
)


def _approve_decisions():
    return {
        "release": "approve",
        "hard_failure": "no",
        "policy_violation": "no",
        "needs_human_review": "no",
        "primary_failure_category": "none",
        "rater_confidence": "certain",
    }


def _valid_payload():
    return {
        "case_id": "x",
        "rater_id": "shivam",
        "schema_version": LABEL_SCHEMA_VERSION,
        "scale": "0-100-step-5",
        "scores": {name: 70 for name in TRAVEL_AND_SUPPORT_DIMENSIONS},
        "decisions": _approve_decisions(),
    }


class TestCalibrationSchema(unittest.TestCase):
    def test_normalize_collapses_whitespace_and_newlines(self):
        left = normalize_output_text("Hello\n\n  world  \n")
        right = normalize_output_text("Hello\n world\n")
        self.assertEqual(left, right)
        self.assertEqual(left, "Hello world")

    def test_content_hash_is_stable_for_normalized_duplicates(self):
        first = content_sha256("Plan A\n\n")
        second = content_sha256("Plan A\n")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_case_id_uses_short_hash(self):
        digest = "abcdef1234567890" * 4
        case_id = make_case_id("travel-planning-budget", "live-gemini-001", digest)
        self.assertEqual(case_id, "travel-planning-budget__live-gemini-001__abcdef12")

    def test_validate_labels_rejects_non_step_five_and_out_of_range(self):
        payload = _valid_payload()
        payload["scores"]["Planning Quality"] = 73
        errors = validate_labels(payload)
        self.assertTrue(any("Planning Quality" in err and "73" in err for err in errors))

        payload["scores"]["Planning Quality"] = 101
        errors = validate_labels(payload)
        self.assertTrue(any("101" in err for err in errors))

    def test_validate_labels_rejects_missing_dimension(self):
        payload = _valid_payload()
        del payload["scores"]["Adaptability"]
        errors = validate_labels(payload)
        self.assertTrue(any("Adaptability" in err for err in errors))

    def test_validate_labels_accepts_step_five_grid(self):
        payload = _valid_payload()
        payload["labeled_at_utc"] = "2026-09-13T00:00:00Z"
        payload["notes"] = {}
        self.assertEqual(validate_labels(payload), [])

    def test_validate_labels_rejects_missing_schema_version(self):
        payload = _valid_payload()
        del payload["schema_version"]
        errors = validate_labels(payload)
        self.assertTrue(any("schema_version" in err for err in errors))

    def test_validate_labels_rejects_missing_or_unknown_decision(self):
        payload = _valid_payload()
        del payload["decisions"]["needs_human_review"]
        payload["decisions"]["release"] = "maybe"
        errors = validate_labels(payload)
        self.assertTrue(any("needs_human_review" in err for err in errors))
        self.assertTrue(any("release" in err and "maybe" in err for err in errors))

    def test_validate_labels_requires_decisions_object(self):
        payload = _valid_payload()
        del payload["decisions"]
        errors = validate_labels(payload)
        self.assertIn("decisions must be an object", errors)

    def test_validate_labels_rejects_approve_with_hard_failure_or_policy_violation(self):
        payload = _valid_payload()
        payload["decisions"]["hard_failure"] = "yes"
        payload["decisions"]["policy_violation"] = "yes"
        errors = validate_labels(payload)
        self.assertTrue(any("hard_failure" in err for err in errors))
        self.assertTrue(any("policy_violation" in err for err in errors))

    def test_validate_labels_rejects_block_without_failure_category(self):
        payload = _valid_payload()
        payload["decisions"]["release"] = "block"
        errors = validate_labels(payload)
        self.assertTrue(any("primary_failure_category" in err for err in errors))

        payload["decisions"]["primary_failure_category"] = "constraint_violation"
        self.assertEqual(validate_labels(payload), [])


if __name__ == "__main__":
    unittest.main()
