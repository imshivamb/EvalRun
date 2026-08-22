"""Terminal report formatter and credential redaction utilities for evalrun CLI."""

from typing import Any, Dict, List
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


def format_terminal_summary(results: List[EvaluationResult], manifest: Dict[str, Any]) -> str:
    """Renders a clean ASCII summary table for terminal display."""
    lines = []
    lines.append("=" * 80)
    lines.append("                         EVALRUN BENCHMARK SUMMARY")
    lines.append("=" * 80)
    lines.append(f" Run ID:       {manifest.get('run_id', 'N/A')}")
    lines.append(f" Target Model: {manifest.get('target_model', {}).get('model_name', 'N/A')} ({manifest.get('target_model', {}).get('base_url', 'N/A')})")
    lines.append(f" Judge Model:  {manifest.get('judge_model', {}).get('model_name', 'N/A')}")
    lines.append(f" Total Runs:   {len(results)}")
    lines.append("-" * 80)
    lines.append(f"{'Scenario Name':<32} | {'Score':<8} | {'Evaluator':<10} | {'Auditor Gate':<12}")
    lines.append("-" * 80)

    all_passed = True

    for res in results:
        eval_status = "✅ PASS" if res.passed else "❌ FAIL"
        if not res.passed:
            all_passed = False

        audit_status = "N/A"
        # Check if audit_report was recorded in result dimension or metadata
        if hasattr(res, "agent_metadata") and isinstance(res.agent_metadata, dict):
            gate = res.agent_metadata.get("audit_gate_decision")
            if gate:
                audit_status = "✅ PASS" if gate == "PASS" else "🛑 BLOCK"
                if gate != "PASS":
                    all_passed = False

        lines.append(f"{res.benchmark_name[:32]:<32} | {res.overall_score:6.2f}   | {eval_status:<10} | {audit_status:<12}")

    lines.append("=" * 80)
    final_verdict = "✅ ALL SCENARIOS PASSED (Exit Code: 0)" if all_passed else "🛑 EVALUATION OR GATE FAILURE (Exit Code: 1)"
    lines.append(f" Final Verdict: {final_verdict}")
    lines.append("=" * 80)
    lines.append(f" Artifacts saved to: {manifest.get('output_dir', './eval_results')}")
    lines.append("")

    return "\n".join(lines)
