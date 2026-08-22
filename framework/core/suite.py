"""EvaluationSuite class managing versioned collections of Scenarios and EvaluationProfiles."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from framework.core.contracts import Scenario
from framework.models import EvaluationProfile


@dataclass
class EvaluationSuite:
    """Encapsulates a collection of scenarios and domain evaluation profiles."""

    suite_id: str
    name: str
    domain: str
    version: str
    scenarios: List[Scenario]
    profiles: Dict[str, EvaluationProfile] = field(default_factory=dict)

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """Looks up a scenario by ID."""
        for scenario in self.scenarios:
            if scenario.id == scenario_id:
                return scenario
        return None

    def get_profile(self, profile_name: Optional[str] = None) -> EvaluationProfile:
        """Resolves an evaluation profile by name or default key."""
        if profile_name:
            if profile_name in self.profiles:
                return self.profiles[profile_name]
            available = list(self.profiles.keys())
            raise ValueError(
                f"Profile '{profile_name}' not found in suite '{self.suite_id}'. "
                f"Available profiles: {available}"
            )
        if "default" in self.profiles:
            return self.profiles["default"]
        available = list(self.profiles.keys())
        raise ValueError(
            f"No profile specified and no 'default' profile registered for suite '{self.suite_id}'. "
            f"Available profiles: {available}"
        )
