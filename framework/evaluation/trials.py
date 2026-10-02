"""Aggregation of repeated evaluation trials into one scenario result."""

from typing import Dict, List, Optional

from framework.models import DimensionScore, EvaluationResult, TrialStatistics
from framework.stats import mean, mean_interval, percentile, sample_std, wilson_interval

SCORE_MIN = 0.0
SCORE_MAX = 100.0


def _clip_interval(interval):
    if interval is None:
        return None
    low, high = interval
    return max(SCORE_MIN, low), min(SCORE_MAX, high)


def _trial_latency(result: EvaluationResult) -> Optional[float]:
    trace = result.agent_metadata.get("run_trace") or {}
    latency = trace.get("latency_seconds")
    return float(latency) if isinstance(latency, (int, float)) else None


def summarize_trials(trial_results: List[EvaluationResult]) -> TrialStatistics:
    """Computes pass rate, score and latency statistics over repeated trials.

    Score intervals are Student-t intervals clipped to the 0-100 score scale;
    the pass-rate interval is a Wilson interval.
    """
    if not trial_results:
        raise ValueError("cannot summarize zero trials")

    trials = len(trial_results)
    passes = sum(1 for r in trial_results if r.passed)
    scores = [r.overall_score for r in trial_results]

    dimension_values: Dict[str, List[float]] = {}
    for result in trial_results:
        for ds in result.dimension_scores:
            dimension_values.setdefault(ds.dimension, []).append(ds.score)

    latencies = [lat for lat in (_trial_latency(r) for r in trial_results) if lat is not None]

    return TrialStatistics(
        trials=trials,
        passes=passes,
        pass_rate=passes / trials,
        pass_rate_interval=wilson_interval(passes, trials),
        score_mean=mean(scores),
        score_std=sample_std(scores),
        score_interval=_clip_interval(mean_interval(scores)),
        dimension_means={name: mean(values) for name, values in dimension_values.items()},
        dimension_intervals={
            name: _clip_interval(mean_interval(values)) for name, values in dimension_values.items()
        },
        latency_p50_seconds=percentile(latencies, 50) if latencies else None,
        latency_p95_seconds=percentile(latencies, 95) if latencies else None,
        trial_scores=scores,
        dimension_trial_scores=dimension_values,
    )


def aggregate_trials(trial_results: List[EvaluationResult], pass_threshold: float) -> EvaluationResult:
    """Combines repeated trials of one scenario into a single result.

    The scenario passes when the mean overall score meets ``pass_threshold``,
    the same rule a single trial uses. An auditor BLOCK in any trial blocks
    the aggregated result.
    """
    statistics = summarize_trials(trial_results)
    first = trial_results[0]

    dimension_scores = []
    for name, value in statistics.dimension_means.items():
        interval = statistics.dimension_intervals.get(name)
        interval_text = f" (95% interval {interval[0]:.1f}-{interval[1]:.1f})" if interval else ""
        dimension_scores.append(
            DimensionScore(
                dimension=name,
                score=value,
                reason=(
                    f"Mean of {statistics.trials} trials{interval_text}. "
                    "Per-trial justifications are in the trial reports."
                ),
            )
        )

    metadata = dict(first.agent_metadata)
    metadata["trials"] = statistics.trials
    decisions = [r.agent_metadata.get("audit_gate_decision") for r in trial_results]
    present = [d for d in decisions if d]
    if present:
        metadata["audit_gate_decisions"] = decisions
        metadata["audit_gate_decision"] = "BLOCK" if "BLOCK" in present else present[0]

    return EvaluationResult(
        benchmark_id=first.benchmark_id,
        benchmark_name=first.benchmark_name,
        overall_score=statistics.score_mean,
        dimension_scores=dimension_scores,
        passed=statistics.score_mean >= pass_threshold,
        agent_metadata=metadata,
        statistics=statistics,
        trial_results=list(trial_results),
    )
