from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Benchmark:
    """Represents a single evaluation scenario.

    Stores the parsed details of the benchmark scenario (e.g., from markdown).
    """

    benchmark_id: str
    name: str
    description: str
    prompt: str
    constraints: Dict[str, Any]
    expected_behavior: List[str]
    evaluation_criteria: Dict[str, List[str]]
    pass_criteria: List[str]
    failure_conditions: List[str]
    notes: List[str]
    profile: str = "travel-agent"


@dataclass
class AgentOutput:
    """Represents the raw response/output produced by an AI agent."""

    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DimensionScore:
    """Stores the score and justification for a single evaluation dimension."""

    dimension: str
    score: float
    reason: str


@dataclass
class EvaluationResult:
    """Represents the final evaluation outcome for a benchmark scenario."""

    benchmark_id: str
    benchmark_name: str
    overall_score: float
    dimension_scores: List[DimensionScore]
    passed: bool
    agent_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationProfile:
    """Defines the name and dimension weights for a specific evaluation domain."""

    name: str
    weights: Dict[str, float]
    pass_threshold: float = 75.0


@dataclass
class ParsedSections:
    """Represents the raw, un-transformed markdown sections parsed from a file."""

    description: str
    prompt: str
    constraints: str
    expected_behavior: str
    evaluation_criteria: str
    pass_criteria: str
    failure_conditions: str
    notes: Optional[str] = None


@dataclass
class ParsedBenchmark:
    """Combines raw metadata and raw parsed sections before transformation."""

    metadata: Dict[str, Any]
    sections: ParsedSections

