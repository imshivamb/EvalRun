"""Baseline comparator engine for score delta calculation and release gate enforcement."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from framework.models import EvaluationResult


@dataclass
class DimensionDelta:
    """Stores score delta for a single evaluation dimension."""

    dimension: str
    baseline_score: float
    candidate_score: float
    delta: float
    is_regression: bool


@dataclass
class ScenarioComparison:
    """Stores regression comparison metrics for a single scenario."""

    scenario_id: str
    scenario_name: str
    status: str  # PASSED, FAILED, BLOCKED, REGRESSED, MISSING_IN_CANDIDATE, NEW
    baseline_score: Optional[float]
    candidate_score: Optional[float]
    overall_delta: Optional[float]
    evaluator_passed: bool
    auditor_gate: str
    is_regression: bool
    dimension_deltas: List[DimensionDelta] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "status": self.status,
            "baseline_score": round(self.baseline_score, 2) if self.baseline_score is not None else None,
            "candidate_score": round(self.candidate_score, 2) if self.candidate_score is not None else None,
            "overall_delta": round(self.overall_delta, 2) if self.overall_delta is not None else None,
            "evaluator_passed": self.evaluator_passed,
            "auditor_gate": self.auditor_gate,
            "is_regression": self.is_regression,
            "dimension_deltas": [
                {
                    "dimension": d.dimension,
                    "baseline_score": round(d.baseline_score, 2),
                    "candidate_score": round(d.candidate_score, 2),
                    "delta": round(d.delta, 2),
                    "is_regression": d.is_regression,
                }
                for d in self.dimension_deltas
            ],
        }


@dataclass
class RegressionReport:
    """Encapsulates full run baseline comparison report."""

    run_id: str
    baseline_run_id: Optional[str]
    regression_detected: bool
    release_blocked: bool
    max_allowed_overall_regression: float
    max_allowed_dimension_regression: float
    scenario_comparisons: List[ScenarioComparison]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "baseline_run_id": self.baseline_run_id,
            "regression_detected": self.regression_detected,
            "release_blocked": self.release_blocked,
            "max_allowed_overall_regression": self.max_allowed_overall_regression,
            "max_allowed_dimension_regression": self.max_allowed_dimension_regression,
            "summary": self.summary,
            "scenarios": [sc.to_dict() for sc in self.scenario_comparisons],
        }


def compare_runs(
    candidate_results: List[EvaluationResult],
    baseline_data: Dict[str, Any],
    max_overall_drop: float = 5.0,
    max_dim_drop: float = 10.0,
    candidate_run_id: str = "candidate-run",
) -> RegressionReport:
    """Compares candidate evaluation results against baseline data.

    Calculates overall and dimension score deltas (candidate - baseline).
    Enforces non-short-circuiting 3-tier release gates:
    1. Evaluator Threshold Gate
    2. Independent Auditor Gate (not BLOCK)
    3. Regression Delta Gate (overall delta >= -max_overall_drop AND dim deltas >= -max_dim_drop)

    Args:
        candidate_results: List of candidate EvaluationResult objects.
        baseline_data: Dictionary returned by load_baseline_manifest().
        max_overall_drop: Maximum allowed overall score drop before regressed.
        max_dim_drop: Maximum allowed per-dimension score drop before regressed.
        candidate_run_id: Identifier for candidate run.

    Returns:
        A RegressionReport containing comparison details and release block status.
    """
    baseline_manifest = baseline_data.get("manifest", {})
    baseline_scenarios = baseline_data.get("scenarios", {})
    baseline_run_id = baseline_manifest.get("run_id")

    candidate_by_id = {res.benchmark_id: res for res in candidate_results}

    comparisons: List[ScenarioComparison] = []
    regression_detected = False
    release_blocked = False

    # 1. Check for baseline scenarios missing from candidate run
    for b_id, b_info in baseline_scenarios.items():
        if b_id not in candidate_by_id:
            regression_detected = True
            release_blocked = True
            comparisons.append(
                ScenarioComparison(
                    scenario_id=b_id,
                    scenario_name=b_info.get("scenario_name", b_id),
                    status="MISSING_IN_CANDIDATE",
                    baseline_score=b_info.get("overall_score"),
                    candidate_score=None,
                    overall_delta=None,
                    evaluator_passed=False,
                    auditor_gate="UNKNOWN",
                    is_regression=True,
                )
            )

    # 2. Evaluate all candidate scenarios
    for cand_res in candidate_results:
        s_id = cand_res.benchmark_id
        cand_score = cand_res.overall_score
        eval_passed = cand_res.passed

        meta = getattr(cand_res, "agent_metadata", {})
        auditor_gate = meta.get("audit_gate_decision", "PASS")

        if auditor_gate != "PASS":
            release_blocked = True

        if not eval_passed:
            release_blocked = True

        if s_id in baseline_scenarios:
            b_info = baseline_scenarios[s_id]
            base_score = b_info["overall_score"]
            overall_delta = cand_score - base_score

            # Formula: delta < -max_overall_drop
            overall_regressed = overall_delta < (-abs(max_overall_drop))

            # Per-dimension deltas
            base_dims = b_info.get("dimension_scores", {})
            cand_dims = {ds.dimension: ds.score for ds in cand_res.dimension_scores}

            dimension_deltas: List[DimensionDelta] = []
            dim_regressed = False

            for d_name, c_dscore in cand_dims.items():
                if d_name in base_dims:
                    b_dscore = base_dims[d_name]
                    ddelta = c_dscore - b_dscore
                    d_is_regressed = ddelta < (-abs(max_dim_drop))
                    if d_is_regressed:
                        dim_regressed = True
                    dimension_deltas.append(
                        DimensionDelta(
                            dimension=d_name,
                            baseline_score=b_dscore,
                            candidate_score=c_dscore,
                            delta=ddelta,
                            is_regression=d_is_regressed,
                        )
                    )

            is_scenario_regression = overall_regressed or dim_regressed
            if is_scenario_regression:
                regression_detected = True
                release_blocked = True
                status_str = "REGRESSED"
            elif not eval_passed:
                status_str = "FAILED"
            elif auditor_gate != "PASS":
                status_str = "BLOCKED"
            else:
                status_str = "PASSED"

            comparisons.append(
                ScenarioComparison(
                    scenario_id=s_id,
                    scenario_name=cand_res.benchmark_name,
                    status=status_str,
                    baseline_score=base_score,
                    candidate_score=cand_score,
                    overall_delta=overall_delta,
                    evaluator_passed=eval_passed,
                    auditor_gate=auditor_gate,
                    is_regression=is_scenario_regression,
                    dimension_deltas=dimension_deltas,
                )
            )
        else:
            # Candidate scenario is new
            status_str = "PASSED" if (eval_passed and auditor_gate == "PASS") else ("BLOCKED" if auditor_gate != "PASS" else "FAILED")
            comparisons.append(
                ScenarioComparison(
                    scenario_id=s_id,
                    scenario_name=cand_res.benchmark_name,
                    status=f"NEW ({status_str})",
                    baseline_score=None,
                    candidate_score=cand_score,
                    overall_delta=None,
                    evaluator_passed=eval_passed,
                    auditor_gate=auditor_gate,
                    is_regression=False,
                )
            )

    summary = {
        "total_scenarios": len(comparisons),
        "passed": sum(1 for c in comparisons if c.status == "PASSED"),
        "failed": sum(1 for c in comparisons if not c.evaluator_passed),
        "blocked": sum(1 for c in comparisons if c.auditor_gate != "PASS"),
        "regressed": sum(1 for c in comparisons if c.is_regression),
    }

    return RegressionReport(
        run_id=candidate_run_id,
        baseline_run_id=baseline_run_id,
        regression_detected=regression_detected,
        release_blocked=release_blocked,
        max_allowed_overall_regression=max_overall_drop,
        max_allowed_dimension_regression=max_dim_drop,
        scenario_comparisons=comparisons,
        summary=summary,
    )
