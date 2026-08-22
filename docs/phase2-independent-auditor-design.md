# Phase 2 — Independent Budget Auditor Design & Experiment Specification

## Executive Summary

Phase 1 established that deterministic tool verification (FastMCP) effectively resolves arithmetic errors and anchor locks on mid-trip replanning scenarios. However, for generalized budget constraints across arbitrary travel scenarios, rigid tool contracts are insufficient on their own. 

In Phase 2, we introduce an **Independent Budget Auditor Agent** (`v3`). Unlike self-reflection (`v2`), which combines critique and content generation into a shared reasoning loop subject to confirmation bias, the Independent Budget Auditor operates as a **decoupled, non-mutating evaluator**. It evaluates finalized plan drafts with zero shared state and returns a structured audit report.

---

## 1. Core Hypothesis

> **Hypothesis**: Decoupling budget auditing into an independent, non-mutating agent—operating with zero shared memory of the reflection agent's internal reasoning—will detect hidden budget violations that self-reflection passes, without degrading overall planning quality or lifestyle personalization.

---

## 2. Architectural Comparison

```text
v1 Arm (Baseline Planner):
  [TravelPlanningAgent] ➔ [Evaluation Engine]

v2 Arm (Planner + Self-Reflection):
  [TravelPlanningAgent] ➔ [ReflectionAgent (Critique & Revision)] ➔ [Evaluation Engine]

v3 Arm (Planner + Self-Reflection + Independent Auditor):
  [TravelPlanningAgent] ➔ [ReflectionAgent] ➔ [IndependentBudgetAuditor] ➔ [Evaluation Engine]
```

### Key Architectural Constraints for v3:
1. **Non-Mutating Execution**: The `IndependentBudgetAuditor` does **NOT** rewrite, edit, or regenerate the itinerary. It performs a read-only audit and outputs a structured diagnostic report.
2. **State Isolation**: The auditor receives only:
   - The original benchmark scenario prompt
   - The finalized itinerary content
   - The target budget parameters
   It has zero access to the `ReflectionAgent`'s internal memory, prompt history, or intermediate critique text.
3. **Decoupled Evaluation**: By separating the auditing role from the rewriting role, we prevent the agent from "negotiating down" budget constraints to justify its own draft choices.

---

## 3. Input/Output Contract

### Input Interface
```python
@dataclass
class AuditRequest:
    scenario_id: str
    scenario_prompt: str
    itinerary_content: str
    total_budget_limit_inr: Optional[float] = None
    daily_budget_limit_jpy: Optional[float] = None
```

### Output Interface (`AuditReport`)
```python
@dataclass
class BudgetViolation:
    violation_type: str  # MATH_HALLUCINATION | DAILY_OVERRUN | HIDDEN_OVERHEAD | ANCHOR_MUTATION
    description: str
    estimated_discrepancy_inr: float
    affected_days: List[int]

@dataclass
class AuditReport:
    status: str  # APPROVED | FLAGGED
    audit_score: float  # 0.0 to 100.0
    violations: List[BudgetViolation]
    total_estimated_spend_inr: float
    budget_limit_inr: float
    variance_inr: float  # Negative indicates overspend
    audit_confidence: float  # 0.0 to 1.0
    reasoning_summary: str
```

---

## 4. Failure Taxonomy

When auditing travel plans, financial errors are categorized under four standardized failure codes:

| Failure Code | Name | Definition & Examples |
| :--- | :--- | :--- |
| `MATH_HALLUCINATION` | Unquantified Savings | Claiming a swap saves money (e.g., "taking local bus saves ₹20,000") without providing verifiable transit/accommodation pricing math. |
| `DAILY_OVERRUN` | Per-Diem Exceeded | Sum of food, entrance fees, and local transit on a specific day exceeds the specified max daily allowance (e.g. spending ¥4,500 on Day 14 when daily limit is ¥2,000). |
| `HIDDEN_OVERHEAD` | Omitted Expenses | Omitting required functional costs (e.g., airport return transfer, luggage lockers, mandatory temple fees) to artificially appear under budget. |
| `ANCHOR_MUTATION` | Non-Refundable Swap | Replacing or canceling a locked, non-refundable accommodation or flight to save money, incurring cancellation penalties ignored by the planner. |

---

## 5. Measurable Success Criteria & Metrics

Because the auditor is non-mutating, it does not directly alter the itinerary's generated text or LLM-judged score; instead, it acts as a release gate blocking non-compliant plans. We evaluate Phase 2 using 8 quantitative metrics:

| Metric | Target / Threshold | Description |
| :--- | :--- | :--- |
| **1. Release Gate Decision Accuracy** | $\ge 90.0\%$ | Percentage of runs where auditor correctly issues `PASS` for compliant plans and `BLOCK` for non-compliant plans. |
| **2. Auditor Sensitivity (Recall)** | $\ge 85.0\%$ | Percentage of actual seeded/real budget violations correctly identified by the auditor (`BLOCK`). |
| **3. Auditor Specificity (1 - FP)** | $\ge 90.0\%$ (False Positives $\le 10\%$) | Percentage of compliant itineraries correctly issued `PASS` without false alarms. |
| **4. Planning Quality Stability** | Within $\pm 2.0$ points of `v2` | Verifies that passing itineraries maintain high route logic, geographic efficiency, and daily pacing. |
| **5. Personalization Stability** | Within $\pm 2.0$ points of `v2` | Verifies that financial auditing does not strip away lifestyle hobbies (thrifting, photography, cafes). |
| **6. Discrepancy Detection Delta** | $> 0$ confirmed instances | Documented cases where `v2` (self-reflection) produced an itinerary passing LLM judgment, but `v3` (auditor) caught a real budget failure. |
| **7. Execution Latency Overhead** | $\le +3.5\text{s}$ per run | Additional wall-clock time added by the audit pass. |
| **8. Token / Cost Overhead** | $\le +20.0\%$ vs `v2` | Additional prompt and completion tokens consumed per evaluation. |

---

## 6. Experimental Protocol

1. **Baseline Benchmarks**:
   - `travel-planning-budget`: Hard strict overall budget and daily allowance constraints.
   - `travel-mid-trip-replanning`: Mid-trip emergency disruption requiring ₹20,000 cost recovery.
2. **Synthetic Sensitivity Suite**:
   - 20 controlled test itineraries with pre-seeded subtle financial errors (5 math hallucinations, 5 daily overruns, 5 hidden overheads, 5 anchor mutations) to benchmark auditor Recall and Precision.
3. **Model Configurations**:
   - GPT-5.6 Terra
   - Gemini 3.1 Pro Preview
   - Gemini 3.5 Flash
4. **Scoring and decision rule**:
   `v3` does not rewrite the itinerary. A case is a successful audit when the
   structured report correctly flags a seeded violation or correctly approves a
   compliant case. The release decision is `BLOCK` when a high-confidence
   violation is found and `PASS` when the audit is approved. A future
   audit-gated revision variant may use these findings to request a new planner
   pass, but that is outside this non-mutating Phase 2 experiment.
5. **Target Outcome Insight**:
   The primary milestone for Phase 2 is demonstrating that `v3` catches subtle
   financial discrepancies that self-reflection (`v2`) misses, with at least 85%
   recall and 90% specificity, while preserving the finalized itinerary and
   producing transparent diagnostic reports.
