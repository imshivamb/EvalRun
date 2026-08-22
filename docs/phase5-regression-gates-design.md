# Phase 5 — Baseline Comparison, Reproducibility, & Regression Release Gates

## Executive Summary

Phase 5 introduces **Automated Baseline Comparison, Reproducibility Fingerprints, and Regression Release Gates**. The platform compares candidate agent prompts, model versions, or code iterations against a stored baseline run, computing per-scenario and per-dimension score deltas ($\Delta \text{score}$), enforcing strict 3-tier release gates, and outputting machine-readable regression reports and an enhanced interactive HTML review report.

---

## 1. Baseline Manifest Contract & Directory Structure

`--baseline` accepts a directory path or a single `manifest.json` file path:

```text
baseline-run/
├── manifest.json
├── qwen2_5-72b_budget-constrained-itinerary_report.json
├── qwen2_5-72b_budget-constrained-itinerary_itinerary.md
└── qwen2_5-72b_urgent-ticket-escalation_report.json
```

### Enhanced `manifest.json` Schema (with Fingerprints & Scenario References)

```json
{
  "run_id": "evalrun-20260820-100000-orig01",
  "timestamp_utc": "2026-08-20T10:00:00Z",
  "git_commit": "284168a",
  "framework_version": "0.5.0",
  "target_agent_spec": "agents.travel:TravelPlanningAgent",
  "target_model": {
    "model_name": "qwen2.5-72b-instruct",
    "base_url": "http://localhost:8000/v1",
    "api_key": "[REDACTED]"
  },
  "judge_model": {
    "model_name": "gpt-4o",
    "base_url": "https://api.openai.com/v1",
    "api_key": "[REDACTED]"
  },
  "scenarios": [
    {
      "scenario_id": "budget-constrained-itinerary",
      "scenario_name": "Budget Constrained Itinerary",
      "content_hash": "a9f87c...",
      "overall_score": 89.40,
      "passed": true,
      "audit_gate_decision": "PASS",
      "report_path": "qwen2_5-72b_budget-constrained-itinerary_report.json",
      "itinerary_path": "qwen2_5-72b_budget-constrained-itinerary_itinerary.md",
      "dimension_scores": {
        "Constraint Satisfaction": 90.0,
        "Planning Quality": 95.0,
        "Information Accuracy": 85.0
      }
    }
  ]
}
```

---

## 2. Stable Scenario Matching & Missing Scenario Policies

Matching between baseline and candidate runs is strictly performed by `scenario_id`:

- **Scenario Present in Both**: Compute $\Delta \text{overall\_score} = \text{candidate\_score} - \text{baseline\_score}$ and per-dimension deltas.
- **Baseline Scenario Missing from Candidate**: Flagged as `MISSING_IN_CANDIDATE`. Triggers release **`BLOCK`**.
- **New Candidate Scenario Absent from Baseline**: Flagged as `NEW`. Evaluated against standard pass criteria; does not calculate regression delta.
- **Dimension Added or Removed**: Unmatched dimensions are skipped or marked `UNMATCHED_DIMENSION` without throwing errors.

---

## 3. Explicit Regression Delta Formula

$$\Delta \text{score} = \text{Candidate Score} - \text{Baseline Score}$$

A scenario or dimension is flagged as a **Regression** if:

$$\Delta \text{score} < -\text{max\_regression}$$

For example:
- `baseline_score`: 89.40
- `candidate_score`: 82.85
- `delta`: $-6.55$
- With `--max-regression 5.0`: $-6.55 < -5.0 \implies \text{Regression Flagged}$ (`RELEASE BLOCKED`).

---

## 4. Complete Non-Short-Circuit Gate Evaluation Order

All three gates are evaluated for EVERY scenario to provide a complete diagnostic report:

1. **Evaluator Score Gate**: Check if candidate score $\ge$ profile threshold (e.g. 75.0).
2. **Independent Auditor Gate**: Check if auditor gate status is `PASS` (not `BLOCK`).
3. **Baseline Regression Gate**: Check if $\Delta \text{overall\_score} \ge -\text{max\_regression}$ and $\Delta \text{dimension\_score} \ge -\text{max\_dimension\_regression}$.

If ANY gate fails for ANY scenario, the release outcome is **`RELEASE BLOCKED`** (CLI exit code `1`).

---

## 5. Machine-Readable `regression_report.json` Artifact

```json
{
  "run_id": "evalrun-20260822-181500-cand02",
  "baseline_run_id": "evalrun-20260820-100000-orig01",
  "regression_detected": true,
  "max_allowed_overall_regression": 5.0,
  "max_allowed_dimension_regression": 10.0,
  "summary": {
    "total_scenarios": 2,
    "passed_count": 1,
    "failed_count": 0,
    "blocked_count": 1,
    "regressed_count": 1
  },
  "scenarios": [
    {
      "scenario_id": "budget-constrained-itinerary",
      "scenario_name": "Budget Constrained Itinerary",
      "baseline_score": 89.40,
      "candidate_score": 82.85,
      "overall_delta": -6.55,
      "is_regression": true,
      "evaluator_passed": true,
      "auditor_gate": "BLOCK",
      "status": "REGRESSED_AND_BLOCKED",
      "dimension_deltas": [
        {
          "dimension": "Planning Quality",
          "baseline_score": 95.0,
          "candidate_score": 80.0,
          "delta": -15.0,
          "is_regression": true
        }
      ]
    }
  ]
}
```

---

## 6. CLI Exit Codes

| Code | Status | Trigger Condition |
| :---: | :--- | :--- |
| **`0`** | **APPROVED** | Evaluator passed, Auditor gate passed, and no score regression exceeded `--max-regression`. |
| **`1`** | **BLOCKED** | One or more scenarios failed evaluator threshold, auditor returned `BLOCK`, or $\Delta \text{score} < -\text{max-regression}$. |
| **`2`** | **ERROR** | Malformed CLI arguments, missing scenario file, missing baseline manifest, or unhandled exception. |
