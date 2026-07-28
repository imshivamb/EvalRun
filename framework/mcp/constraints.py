"""Deterministic constraint checks used by the travel validation MCP server."""

from copy import deepcopy
from typing import Any, Dict, List


MID_TRIP_REPLANNING_SCENARIO = "travel-mid-trip-replanning"

_SCENARIO_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    MID_TRIP_REPLANNING_SCENARIO: {
        "scenario_id": MID_TRIP_REPLANNING_SCENARIO,
        "immutable_booking_ids": ["kyoto-hostel", "narita-return-flight"],
        "locked_bookings": [
            {
                "booking_id": "kyoto-hostel",
                "description": "Kyoto hostel stay on Days 15–18",
                "start_day": 15,
                "end_day": 18,
                "reason": "Pre-paid and non-refundable",
            },
            {
                "booking_id": "narita-return-flight",
                "description": "Return flight from Narita on Day 28",
                "start_day": 28,
                "end_day": 28,
                "reason": "Non-changeable",
            },
        ],
        "required_savings_inr": 20000.0,
        "revision_start_day": 13,
    }
}


def get_locked_constraints(scenario_id: str) -> Dict[str, Any]:
    """Returns immutable bookings and numeric targets for a supported scenario."""
    try:
        return deepcopy(_SCENARIO_CONSTRAINTS[scenario_id])
    except KeyError as error:
        raise ValueError(f"Unsupported scenario: '{scenario_id}'") from error


def validate_revision(
    scenario_id: str,
    booking_actions: List[Dict[str, str]],
    changed_days: List[int],
) -> Dict[str, Any]:
    """Checks whether a proposed revision changes an immutable booking.

    ``booking_actions`` must include one entry for each locked booking with an
    action of ``preserve``, ``move``, ``cancel``, or ``modify``. The function
    intentionally validates only explicit, deterministic assertions; the LLM
    remains responsible for itinerary quality and travel judgment.
    """
    constraints = get_locked_constraints(scenario_id)
    immutable_ids = constraints["immutable_booking_ids"]
    actions_by_booking = {
        action.get("booking_id"): action.get("action")
        for action in booking_actions
        if action.get("booking_id")
    }
    violations = []

    for booking_id in immutable_ids:
        action = actions_by_booking.get(booking_id)
        if action is None:
            violations.append(
                f"No preservation assertion was supplied for locked booking '{booking_id}'."
            )
        elif action != "preserve":
            violations.append(
                f"Locked booking '{booking_id}' must be preserved, not '{action}'."
            )

    invalid_days = [
        day
        for day in changed_days
        if not isinstance(day, int) or day < constraints["revision_start_day"]
    ]
    if invalid_days:
        violations.append(
            "A replanning revision cannot modify days before Day "
            f"{constraints['revision_start_day']}: {invalid_days}."
        )

    return {
        "valid": not violations,
        "violations": violations,
        "immutable_booking_ids": immutable_ids,
        "changed_days": changed_days,
    }


def calculate_savings(
    scenario_id: str, savings_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Totals explicit savings items against the scenario's required reduction."""
    constraints = get_locked_constraints(scenario_id)
    normalized_items = []
    invalid_items = []

    for item in savings_items:
        label = str(item.get("label", "")).strip()
        try:
            amount_inr = float(item["amount_inr"])
        except (KeyError, TypeError, ValueError):
            invalid_items.append(item)
            continue
        if not label or amount_inr < 0:
            invalid_items.append(item)
            continue
        normalized_items.append({"label": label, "amount_inr": amount_inr})

    total_savings_inr = sum(item["amount_inr"] for item in normalized_items)
    target_savings_inr = constraints["required_savings_inr"]
    remaining_gap_inr = max(target_savings_inr - total_savings_inr, 0.0)

    return {
        "target_savings_inr": target_savings_inr,
        "total_savings_inr": total_savings_inr,
        "remaining_gap_inr": remaining_gap_inr,
        "target_met": not invalid_items and remaining_gap_inr == 0.0,
        "accepted_items": normalized_items,
        "invalid_items": invalid_items,
    }
