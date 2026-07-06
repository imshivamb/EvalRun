"""Travel-specific session memory implementation."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import yaml
import json
from framework.memory import BaseSessionMemory


@dataclass
class Booking:
    """Represents a structured locked booking."""
    booking_id: str
    booking_type: str  # e.g., "flight", "hotel", "activity", "train"
    location: str
    start_day: int
    end_day: int
    refundable: bool = True
    notes: str = ""


@dataclass
class RemoteWorkSchedule:
    """Represents a remote work commitment and timezone constraints."""
    timezone: str = "UTC"
    availability_start: str = "09:00"
    availability_end: str = "17:00"
    meeting_start: str = ""
    meeting_end: str = ""
    flexible_hours: int = 0


@dataclass
class UserPreferences:
    """Represents purely static user profiling and travel preferences."""
    interests: List[str] = field(default_factory=list)
    travel_style: str = "balanced"
    accommodation_preference: str = "hotel"
    walking_tolerance: str = "moderate"


@dataclass
class TripConstraints:
    """Represents hard trip limits, schedules, and locked bookings."""
    total_budget: float = 0.0
    duration_days: int = 1
    destinations: List[str] = field(default_factory=list)
    remote_work_schedule: Optional[RemoteWorkSchedule] = None
    locked_bookings: List[Booking] = field(default_factory=list)
    hard_constraints: List[str] = field(default_factory=list)


@dataclass
class CurrentTripState:
    """Tracks active planning state and execution progress."""
    current_day: int = 1
    remaining_budget: float = 0.0
    completed_destinations: List[str] = field(default_factory=list)
    current_plan_version: int = 1


class TravelSessionMemory(BaseSessionMemory):
    """Holds and serializes working session memory for travel planning and reflection."""

    def __init__(
        self,
        session_id: str,
        version: int = 1,
        preferences: Optional[UserPreferences] = None,
        constraints: Optional[TripConstraints] = None,
        state: Optional[CurrentTripState] = None,
    ):
        """Initializes the TravelSessionMemory.

        Args:
            session_id: A unique string identifier for the planning session.
            version: Schema/memory state version.
            preferences: Optional initial UserPreferences.
            constraints: Optional initial TripConstraints.
            state: Optional initial CurrentTripState.
        """
        self.session_id = session_id
        self.version = version
        self.preferences = preferences or UserPreferences()
        self.constraints = constraints or TripConstraints()
        self.state = state or CurrentTripState()

    def to_yaml(self) -> str:
        """Serializes session state to structured YAML for LLM context injection.

        Excludes empty lists or empty dicts to conserve context tokens.
        """
        data = {
            "session_id": self.session_id,
            "version": self.version,
            "preferences": {k: v for k, v in asdict(self.preferences).items() if v},
            "constraints": {k: v for k, v in asdict(self.constraints).items() if v},
            "state": {k: v for k, v in asdict(self.state).items() if v},
        }
        return yaml.dump(data, sort_keys=False, default_flow_style=False)

    def to_json(self) -> str:
        """Returns JSON representation of memory state."""
        return json.dumps({
            "session_id": self.session_id,
            "version": self.version,
            "preferences": asdict(self.preferences),
            "constraints": asdict(self.constraints),
            "state": asdict(self.state),
        }, indent=2)
