"""Local stdio MCP server for travel-planning constraint validation."""

from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from framework.mcp.constraints import (
    calculate_savings as calculate_savings_check,
    get_locked_constraints as get_locked_constraints_check,
    validate_revision as validate_revision_check,
)


mcp = FastMCP(
    "Travel Constraint Validation",
    instructions=(
        "Use these tools to verify explicit locked-booking constraints and "
        "cost-saving arithmetic for travel itinerary revisions."
    ),
    json_response=True,
)


@mcp.tool()
def get_locked_constraints(scenario_id: str) -> Dict[str, Any]:
    """Get immutable bookings and savings targets for a benchmark scenario."""
    return get_locked_constraints_check(scenario_id)


@mcp.tool()
def validate_revision(
    scenario_id: str,
    booking_actions: List[Dict[str, str]],
    changed_days: List[int],
) -> Dict[str, Any]:
    """Check whether a revision preserves every locked booking."""
    return validate_revision_check(scenario_id, booking_actions, changed_days)


@mcp.tool()
def calculate_savings(
    scenario_id: str, savings_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Calculate explicit INR savings against a scenario's required reduction."""
    return calculate_savings_check(scenario_id, savings_items)


if __name__ == "__main__":
    mcp.run()
