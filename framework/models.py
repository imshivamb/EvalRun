from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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
class TrialStatistics:
    """Summary of repeated trials of one scenario, with 95% intervals.

    Intervals are None when the trial count is too small to estimate them
    (fewer than two trials for score intervals).
    """

    trials: int
    passes: int
    pass_rate: float
    pass_rate_interval: Optional[Tuple[float, float]]
    score_mean: float
    score_std: Optional[float]
    score_interval: Optional[Tuple[float, float]]
    dimension_means: Dict[str, float]
    dimension_intervals: Dict[str, Optional[Tuple[float, float]]]
    latency_p50_seconds: Optional[float]
    latency_p95_seconds: Optional[float]
    trial_scores: List[float] = field(default_factory=list)
    dimension_trial_scores: Dict[str, List[float]] = field(default_factory=dict)
    confidence_level: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trials": self.trials,
            "passes": self.passes,
            "pass_rate": self.pass_rate,
            "pass_rate_interval": list(self.pass_rate_interval) if self.pass_rate_interval else None,
            "score_mean": self.score_mean,
            "score_std": self.score_std,
            "score_interval": list(self.score_interval) if self.score_interval else None,
            "dimension_means": dict(self.dimension_means),
            "dimension_intervals": {
                name: list(interval) if interval else None
                for name, interval in self.dimension_intervals.items()
            },
            "latency_p50_seconds": self.latency_p50_seconds,
            "latency_p95_seconds": self.latency_p95_seconds,
            "trial_scores": list(self.trial_scores),
            "dimension_trial_scores": {
                name: list(values) for name, values in self.dimension_trial_scores.items()
            },
            "confidence_level": self.confidence_level,
        }


@dataclass
class EvaluationResult:
    """Represents the final evaluation outcome for a benchmark scenario."""

    benchmark_id: str
    benchmark_name: str
    overall_score: float
    dimension_scores: List[DimensionScore]
    passed: bool
    agent_metadata: Dict[str, Any] = field(default_factory=dict)
    statistics: Optional[TrialStatistics] = None
    trial_results: List["EvaluationResult"] = field(default_factory=list)


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

