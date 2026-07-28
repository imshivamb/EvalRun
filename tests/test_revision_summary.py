"""Tests for the structured revision-summary contract."""

import unittest

from framework.mcp.revision_summary import parse_revision_summary


class TestRevisionSummary(unittest.TestCase):
    def test_parses_json_markdown_and_formats_tool_arguments(self):
        summary = parse_revision_summary(
            """```json
            {
              "scenario_id": "travel-mid-trip-replanning",
              "changed_days": [13, 19, 22],
              "booking_actions": [
                {"booking_id": "kyoto-hostel", "action": "preserve"},
                {"booking_id": "narita-return-flight", "action": "preserve"}
              ],
              "savings_items": [
                {"label": "Night bus", "amount_inr": 12000}
              ]
            }
            ```"""
        )

        self.assertEqual(summary.scenario_id, "travel-mid-trip-replanning")
        self.assertEqual(summary.changed_days, [13, 19, 22])
        self.assertEqual(
            summary.to_tool_arguments()["booking_actions"][0],
            {"booking_id": "kyoto-hostel", "action": "preserve"},
        )
        self.assertEqual(summary.to_tool_arguments()["savings_items"][0]["amount_inr"], 12000.0)

    def test_rejects_missing_or_ambiguous_fields(self):
        with self.assertRaisesRegex(ValueError, "changed_days"):
            parse_revision_summary(
                '{"scenario_id": "travel-mid-trip-replanning", "booking_actions": [], "savings_items": []}'
            )

        with self.assertRaisesRegex(ValueError, "booking action must be"):
            parse_revision_summary(
                '{"scenario_id": "travel-mid-trip-replanning", "changed_days": [], '
                '"booking_actions": [{"booking_id": "kyoto-hostel", "action": "leave alone"}], '
                '"savings_items": []}'
            )

        with self.assertRaisesRegex(ValueError, "amount_inr"):
            parse_revision_summary(
                '{"scenario_id": "travel-mid-trip-replanning", "changed_days": [], '
                '"booking_actions": [], "savings_items": [{"label": "Bus", "amount_inr": -1}]}'
            )


if __name__ == "__main__":
    unittest.main()
