import unittest
import yaml
import json
from agents.travel import (
    Booking,
    RemoteWorkSchedule,
    UserPreferences,
    TripConstraints,
    CurrentTripState,
    TravelSessionMemory,
)


class TestSessionMemory(unittest.TestCase):
    """Tests the TravelSessionMemory data models and serialization APIs."""

    def test_default_initialization(self):
        memory = TravelSessionMemory(session_id="test_session")
        self.assertEqual(memory.session_id, "test_session")
        self.assertEqual(memory.version, 1)
        self.assertEqual(memory.preferences.travel_style, "balanced")
        self.assertEqual(memory.constraints.duration_days, 1)
        self.assertEqual(memory.state.current_day, 1)

    def test_custom_initialization(self):
        booking = Booking(
            booking_id="b1",
            booking_type="flight",
            location="Tokyo",
            start_day=1,
            end_day=1,
            refundable=False,
            notes="Locked non-refundable flight"
        )
        work = RemoteWorkSchedule(
            timezone="JST",
            availability_start="10:00",
            availability_end="18:00"
        )
        pref = UserPreferences(interests=["museums"], travel_style="relaxed")
        consts = TripConstraints(
            total_budget=50000.0,
            duration_days=10,
            destinations=["Tokyo", "Kyoto"],
            remote_work_schedule=work,
            locked_bookings=[booking]
        )
        state = CurrentTripState(current_day=2, remaining_budget=48000.0, current_plan_version=2)

        memory = TravelSessionMemory(
            session_id="s1",
            version=2,
            preferences=pref,
            constraints=consts,
            state=state
        )

        self.assertEqual(memory.session_id, "s1")
        self.assertEqual(memory.version, 2)
        self.assertEqual(memory.preferences.interests, ["museums"])
        self.assertEqual(memory.constraints.total_budget, 50000.0)
        self.assertEqual(memory.constraints.locked_bookings[0].booking_id, "b1")
        self.assertEqual(memory.state.current_day, 2)

    def test_to_yaml_serialization(self):
        pref = UserPreferences(interests=["sushi"], travel_style="fast")
        memory = TravelSessionMemory(session_id="s_yaml", preferences=pref)

        yaml_str = memory.to_yaml()
        parsed = yaml.safe_load(yaml_str)

        self.assertEqual(parsed["session_id"], "s_yaml")
        self.assertEqual(parsed["preferences"]["interests"], ["sushi"])
        self.assertEqual(parsed["preferences"]["travel_style"], "fast")

    def test_to_json_serialization(self):
        pref = UserPreferences(interests=["anime"])
        memory = TravelSessionMemory(session_id="s_json", preferences=pref)

        json_str = memory.to_json()
        parsed = json.loads(json_str)

        self.assertEqual(parsed["session_id"], "s_json")
        self.assertEqual(parsed["preferences"]["interests"], ["anime"])


if __name__ == "__main__":
    unittest.main()
