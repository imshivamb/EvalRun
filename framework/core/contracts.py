"""Domain-neutral core contracts and data models for evaluation."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from framework.models import Benchmark


@dataclass
class Scenario:
    """Domain-neutral evaluation scenario specification."""

    id: str
    name: str
    domain: str  # e.g. "travel", "support_triage", "scheduling"
    description: str
    prompt: str
    constraints: Dict[str, Any]
    expected_behavior: List[str]
    evaluation_criteria: Dict[str, List[str]]
    pass_criteria: List[str]
    failure_conditions: List[str]
    notes: Optional[List[str]] = None
    profile_name: str = "travel-agent"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def benchmark_id(self) -> str:
        """Backward-compatibility property for legacy codebase."""
        return self.id

    @property
    def profile(self) -> str:
        """Backward-compatibility property for legacy profile name."""
        return self.profile_name


def to_scenario(benchmark: Benchmark, domain: str = "travel") -> Scenario:
    """Converts a legacy Benchmark instance into a generic Scenario instance."""
    return Scenario(
        id=benchmark.benchmark_id,
        name=benchmark.name,
        domain=domain,
        description=benchmark.description,
        prompt=benchmark.prompt,
        constraints=benchmark.constraints,
        expected_behavior=benchmark.expected_behavior,
        evaluation_criteria=benchmark.evaluation_criteria,
        pass_criteria=benchmark.pass_criteria,
        failure_conditions=benchmark.failure_conditions,
        notes=benchmark.notes,
        profile_name=getattr(benchmark, "profile", "travel-agent"),
    )


def to_benchmark(scenario: Scenario) -> Benchmark:
    """Converts a generic Scenario instance into a legacy Benchmark instance."""
    return Benchmark(
        benchmark_id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        prompt=scenario.prompt,
        constraints=scenario.constraints,
        expected_behavior=scenario.expected_behavior,
        evaluation_criteria=scenario.evaluation_criteria,
        pass_criteria=scenario.pass_criteria,
        failure_conditions=scenario.failure_conditions,
        notes=scenario.notes or [],
        profile=scenario.profile_name,
    )


@dataclass
class RunTrace:
    """Execution trace tracking metadata, latency, token usage, and status for an evaluation run."""

    trace_id: str
    scenario_id: str
    agent_id: str
    model_name: str
    started_at_utc: str
    finished_at_utc: str
    latency_seconds: float
    status: Literal["success", "error", "timeout"]
    error: Optional[str] = None
    retries_attempted: int = 0
    token_usage: Optional[Dict[str, int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
