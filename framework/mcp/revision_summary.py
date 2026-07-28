"""Structured, LLM-produced claims for deterministic revision validation.

The travel itinerary remains free-form text for the traveler.  Before a
replanning revision is accepted, the model must also provide this small JSON
summary of the claims that a deterministic tool can verify.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from framework.utils import parse_json_markdown


@dataclass(frozen=True)
class BookingAction:
    """A declared treatment of one booking in a proposed itinerary revision."""

    booking_id: str
    action: str


@dataclass(frozen=True)
class SavingsItem:
    """One concrete cost-saving substitution claimed by the proposed revision."""

    label: str
    amount_inr: float


@dataclass(frozen=True)
class RevisionSummary:
    """The complete deterministic-validation contract for a replanning draft."""

    scenario_id: str
    changed_days: List[int]
    booking_actions: List[BookingAction]
    savings_items: List[SavingsItem]

    def to_tool_arguments(self) -> Dict[str, Any]:
        """Returns JSON-compatible arguments for the validation MCP tools."""
        return {
            "scenario_id": self.scenario_id,
            "booking_actions": [asdict(action) for action in self.booking_actions],
            "changed_days": self.changed_days,
            "savings_items": [asdict(item) for item in self.savings_items],
        }


REVISION_SUMMARY_JSON_TEMPLATE = """{
  "scenario_id": "travel-mid-trip-replanning",
  "changed_days": [13, 19, 22],
  "booking_actions": [
    {"booking_id": "kyoto-hostel", "action": "preserve"},
    {"booking_id": "narita-return-flight", "action": "preserve"}
  ],
  "savings_items": [
    {"label": "Kyoto-to-Tokyo night bus instead of Shinkansen", "amount_inr": 12000}
  ]
}"""


def parse_revision_summary(text: str) -> RevisionSummary:
    """Parses and validates the JSON contract emitted by an LLM.

    This parser intentionally rejects incomplete or ambiguous declarations. A
    model must explicitly state every field before its proposal can be passed
    to the deterministic MCP tools.
    """
    payload = parse_json_markdown(text)
    if not isinstance(payload, dict):
        raise ValueError("Revision summary must be a JSON object.")

    scenario_id = payload.get("scenario_id")
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ValueError("Revision summary requires a non-empty scenario_id.")

    changed_days = payload.get("changed_days")
    if not isinstance(changed_days, list) or not all(
        isinstance(day, int) and not isinstance(day, bool) for day in changed_days
    ):
        raise ValueError("changed_days must be a list of integer day numbers.")

    raw_booking_actions = payload.get("booking_actions")
    if not isinstance(raw_booking_actions, list):
        raise ValueError("booking_actions must be a list.")
    booking_actions = []
    for item in raw_booking_actions:
        if not isinstance(item, dict):
            raise ValueError("Each booking action must be an object.")
        booking_id = item.get("booking_id")
        action = item.get("action")
        if not isinstance(booking_id, str) or not booking_id.strip():
            raise ValueError("Each booking action requires a non-empty booking_id.")
        if action not in {"preserve", "move", "cancel", "modify"}:
            raise ValueError("Each booking action must be preserve, move, cancel, or modify.")
        booking_actions.append(BookingAction(booking_id=booking_id, action=action))

    raw_savings_items = payload.get("savings_items")
    if not isinstance(raw_savings_items, list):
        raise ValueError("savings_items must be a list.")
    savings_items = []
    for item in raw_savings_items:
        if not isinstance(item, dict):
            raise ValueError("Each savings item must be an object.")
        label = item.get("label")
        amount_inr = item.get("amount_inr")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Each savings item requires a non-empty label.")
        if (
            not isinstance(amount_inr, (int, float))
            or isinstance(amount_inr, bool)
            or amount_inr < 0
        ):
            raise ValueError("Each savings amount_inr must be a non-negative number.")
        savings_items.append(SavingsItem(label=label, amount_inr=float(amount_inr)))

    return RevisionSummary(
        scenario_id=scenario_id,
        changed_days=changed_days,
        booking_actions=booking_actions,
        savings_items=savings_items,
    )
