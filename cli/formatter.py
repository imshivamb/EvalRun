"""Terminal report formatter and credential redaction utilities for evalrun CLI."""

from typing import Any, Dict, List, Optional
from framework.models import EvaluationResult

SECRET_KEYS = {"api_key", "apikey", "authorization", "password", "secret", "bearer", "token"}


def redact_credentials(data: Any) -> Any:
    """Recursively redacts sensitive credentials from dictionaries or lists for manifest persistence."""
    if isinstance(data, dict):
        redacted = {}
        for key, val in data.items():
            if key.lower() in SECRET_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_credentials(val)
        return redacted
    elif isinstance(data, list):
        return [redact_credentials(item) for item in data]
    return data


def _interval_text(interval: Optional[Any], scale: float = 1.0, digits: int = 1) -> str:
    if not interval:
        return "[n/a]"
    low, high = interval
    return f"[{low * scale:.{digits}f}-{high * scale:.{digits}f}]"


def _seconds_text(value: Optional[float]) -> str:
    return f"{value:.2f}s" if value is not None else "n/a"


def format_trial_statistics(results: List[EvaluationResult]) -> List[str]:
    """Per-scenario trial statistics lines; empty when every scenario ran once."""
    with_trials = [r for r in results if r.statistics is not None and r.statistics.trials > 1]
    if not with_trials:
        return []
    lines = [" Trial statistics (95% intervals)"]
    for res in with_trials:
        stats = res.statistics
        lines.append(
            f"  {res.benchmark_name[:28]:<28} pass {stats.passes}/{stats.trials} "
            f"{stats.pass_rate * 100:.0f}% {_interval_text(stats.pass_rate_interval, scale=100, digits=0)}"
            f" | score {stats.score_mean:.1f} {_interval_text(stats.score_interval)}"
            f" | latency p50 {_seconds_text(stats.latency_p50_seconds)}"
            f" p95 {_seconds_text(stats.latency_p95_seconds)}"
        )
    return lines


def format_terminal_summary(
    results: List[EvaluationResult],
    manifest: Dict[str, Any],
    regression_report: Optional[Dict[str, Any]] = None,
) -> str:
    """Renders a clean ASCII summary table for terminal display."""
    lines = []
    lines.append("=" * 85)
    lines.append("                         EVALRUN BENCHMARK SUMMARY")
    lines.append("=" * 85)
    lines.append(f" Run ID:       {manifest.get('run_id', 'N/A')}")
    lines.append(f" Target Model: {manifest.get('target_model', {}).get('model_name', 'N/A')} ({manifest.get('target_model', {}).get('base_url', 'N/A')})")
    lines.append(f" Judge Model:  {manifest.get('judge_model', {}).get('model_name', 'N/A')}")
    if manifest.get("baseline_path"):
        lines.append(f" Baseline:     {manifest.get('baseline_path')}")
    lines.append(f" Total Runs:   {len(results)}")
    lines.append("-" * 85)

    if regression_report:
        lines.append(f"{'Scenario Name':<28} | {'Score':<7} | {'Delta':<8} | {'Evaluator':<10} | {'Auditor':<8} | {'Status':<10}")
    else:
        lines.append(f"{'Scenario Name':<32} | {'Score':<8} | {'Evaluator':<10} | {'Auditor Gate':<12}")
    lines.append("-" * 85)

    all_passed = True
    reg_scenarios_by_id = {}
    if regression_report:
        if regression_report.get("release_blocked"):
            all_passed = False
        for s in regression_report.get("scenarios", []):
            reg_scenarios_by_id[s["scenario_id"]] = s

    for res in results:
        eval_status = "PASS" if res.passed else "FAIL"
        if not res.passed:
            all_passed = False

        audit_status = "N/A"
        if hasattr(res, "agent_metadata") and isinstance(res.agent_metadata, dict):
            gate = res.agent_metadata.get("audit_gate_decision")
            if gate:
                audit_status = "PASS" if gate == "PASS" else "BLOCK"
                if gate != "PASS":
                    all_passed = False

        if regression_report:
            reg_info = reg_scenarios_by_id.get(res.benchmark_id, {})
            delta_val = reg_info.get("overall_delta")
            delta_str = f"{delta_val:+.2f}" if delta_val is not None else "N/A"
            status_str = reg_info.get("status", "OK")
            lines.append(
                f"{res.benchmark_name[:28]:<28} | {res.overall_score:6.2f}  | {delta_str:<8} | {eval_status:<10} | {audit_status:<8} | {status_str:<10}"
            )
        else:
            lines.append(f"{res.benchmark_name[:32]:<32} | {res.overall_score:6.2f}   | {eval_status:<10} | {audit_status:<12}")

    trial_lines = format_trial_statistics(results)
    if trial_lines:
        lines.append("-" * 85)
        lines.extend(trial_lines)

    lines.append("=" * 85)
    if regression_report and regression_report.get("regression_detected"):
        final_verdict = "RELEASE BLOCKED: REGRESSION OR GATE FAILURE (Exit Code: 1)"
    elif not all_passed:
        final_verdict = "EVALUATION OR GATE FAILURE (Exit Code: 1)"
    else:
        final_verdict = "ALL SCENARIOS PASSED (Exit Code: 0)"

    lines.append(f" Final Verdict: {final_verdict}")
    lines.append("=" * 85)
    lines.append(f" Artifacts saved to: {manifest.get('output_dir', './eval_results')}")
    lines.append("")

    return "\n".join(lines)
