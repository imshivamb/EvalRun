"""Tests for deterministic travel constraint validation tools."""

import asyncio
import unittest

from framework.mcp.constraints import (
    MID_TRIP_REPLANNING_SCENARIO,
    calculate_savings,
    get_locked_constraints,
    validate_revision,
)
from framework.mcp.client import TravelValidationMCPClient
from framework.mcp.server import mcp


class TestTravelConstraintTools(unittest.TestCase):
    """Verifies validation logic separately from LLM behavior."""

    def test_get_locked_constraints(self):
        constraints = get_locked_constraints(MID_TRIP_REPLANNING_SCENARIO)

        self.assertEqual(constraints["required_savings_inr"], 20000.0)
        self.assertEqual(
            constraints["immutable_booking_ids"],
            ["kyoto-hostel", "narita-return-flight"],
        )

    def test_validate_revision_accepts_preserved_bookings(self):
        result = validate_revision(
            MID_TRIP_REPLANNING_SCENARIO,
            booking_actions=[
                {"booking_id": "kyoto-hostel", "action": "preserve"},
                {"booking_id": "narita-return-flight", "action": "preserve"},
            ],
            changed_days=[13, 19, 22],
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["violations"], [])

    def test_validate_revision_rejects_moved_or_undeclared_booking(self):
        result = validate_revision(
            MID_TRIP_REPLANNING_SCENARIO,
            booking_actions=[
                {"booking_id": "kyoto-hostel", "action": "move"},
            ],
            changed_days=[13],
        )

        self.assertFalse(result["valid"])
        self.assertEqual(len(result["violations"]), 2)
        self.assertIn("kyoto-hostel", result["violations"][0])
        self.assertIn("narita-return-flight", result["violations"][1])

    def test_calculate_savings_requires_valid_items_and_target(self):
        result = calculate_savings(
            MID_TRIP_REPLANNING_SCENARIO,
            savings_items=[
                {"label": "Night bus", "amount_inr": 12000},
                {"label": "Cheaper Tokyo hostel", "amount_inr": 8000},
            ],
        )

        self.assertTrue(result["target_met"])
        self.assertEqual(result["total_savings_inr"], 20000.0)
        self.assertEqual(result["remaining_gap_inr"], 0.0)

    def test_calculate_savings_rejects_invalid_items(self):
        result = calculate_savings(
            MID_TRIP_REPLANNING_SCENARIO,
            savings_items=[
                {"label": "Night bus", "amount_inr": 12000},
                {"label": "", "amount_inr": 8000},
            ],
        )

        self.assertFalse(result["target_met"])
        self.assertEqual(len(result["invalid_items"]), 1)

    def test_server_exposes_three_tools(self):
        tools = asyncio.run(mcp.list_tools())
        self.assertEqual(
            {tool.name for tool in tools},
            {"get_locked_constraints", "validate_revision", "calculate_savings"},
        )

    def test_client_discovers_and_calls_server_tool(self):
        async def run_client_check():
            client = TravelValidationMCPClient()
            tools = await client.list_tools()
            result = await client.call_tool(
                "calculate_savings",
                {
                    "scenario_id": MID_TRIP_REPLANNING_SCENARIO,
                    "savings_items": [
                        {"label": "Night bus", "amount_inr": 20000},
                    ],
                },
            )
            return tools, result

        tools, result = asyncio.run(run_client_check())
        self.assertEqual(
            set(tools),
            {"get_locked_constraints", "validate_revision", "calculate_savings"},
        )
        self.assertTrue(result["target_met"])


if __name__ == "__main__":
    unittest.main()
