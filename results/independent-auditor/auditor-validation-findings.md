# Phase 2 — Independent Auditor Evaluation & Architectural Findings

## Executive Summary

Phase 2 evaluated the **Independent Budget Auditor** (`v3`), a decoupled, non-mutating release gate that inspects finalized agent outputs without shared memory of the planner's or reflection agent's internal reasoning.

Our empirical findings demonstrate a critical architectural principle for agent evaluation: **Quality Score ≠ Release Gate Decision**. Standard multi-dimensional LLM judges frequently grant high or perfect scores (e.g. 94.75–100/100) to agent outputs containing severe financial inaccuracies, whereas an independent budget auditor successfully detects hard compliance violations and issues a release **`BLOCK`**.

However, detailed latency tracking revealed an important operational constraint: auditing a complex 29-day itinerary takes **229s–365s**, making the auditor unsuitable for real-time interactive loops but ideal for asynchronous CI/CD release gates.

The synthetic sensitivity suite also exposed a serious limitation: across 20
cases the auditor achieved **100% recall but 0% specificity** (18 true
positives, 2 false positives, 0 true negatives, 0 false negatives). It blocked
both compliant cases. The auditor therefore demonstrates detection of seeded
violations, but it is not yet a trustworthy release gate; specificity must be
fixed and re-measured before this result is presented as production-ready.

---

## 1. Refined Phase 2 Empirical Hypothesis

> **Refined Hypothesis**: An independent, non-mutating budget auditor detects hard financial violations (`MATH_HALLUCINATION`, `HIDDEN_OVERHEAD`) that both self-reflection and multi-dimensional quality evaluators pass—while preserving comparable planning quality scores—but its high latency requires tiering it as an asynchronous release gate rather than an interactive loop component.

---

## 2. Comparative Benchmark Results (`models/gemini-3.1-pro-preview`)

All three arms (`v1` Planner, `v2` Self-Reflection, `v3` Independent Auditor Gate) were evaluated across identical benchmark scenarios using an unchanged 5-dimension judge engine.

| Configuration Arm | Budget Scenario (`travel-planning-budget`) | Replanning Scenario (`mid-trip-replanning`) |
| :--- | :---: | :---: |
| **`v1` — Baseline Planner** | 84.60 | 98.75 |
| **`v2` — Planner + Reflection** | 85.00 | 99.25 |
| **`v3` — Evaluator Quality Score** | **85.00** | **94.75** |
| **`v3` — Independent Auditor Gate** | **`BLOCK`** 🛑 | **`BLOCK`** 🛑 |
| **Auditor Latency** | **229.91 seconds** | **365.67 seconds** |

---

## 3. Deep-Dive Financial Violation Analysis

The independent auditor detected two primary failure classes across high-scoring itineraries:

### A. `MATH_HALLUCINATION`
- **Budget Scenario**: The itinerary claimed taking the Willer Express overnight bus *"saves ₹8,000 on a Shinkansen ticket"*. The auditor caught that ₹8,000 was the total principal price of the train ticket, not the net savings relative to the bus fare (₹3,500–₹5,000), falsely inflating financial savings.
- **Replanning Scenario**: The itinerary claimed ¥2,000 in savings under *"Skip Paid Entries"*, but explicitly itemized only ¥1,000 from skipping Himeji Castle interior. The remaining ¥1,000 was falsely attributed to visiting intrinsically free sites (Fushimi Inari, Arashiyama) already in the baseline plan.

### B. `HIDDEN_OVERHEAD`
- **Budget Scenario**: The itinerary allocated the exact ₹250,000 budget with ₹0 variance, but completely omitted mandatory pre-trip visa fees for South Korea and Japan (~₹7,000), causing an inevitable budget overflow in practice.

---

## 4. Production Architectural Tiering

Because auditing long-horizon travel itineraries requires extensive verification of daily arithmetic and implicit costs, latency ranges between **3 to 6 minutes**. 

We conclude that LLM evaluation systems should adopt a **two-tier architecture**:

```text
                    1. Interactive User Loop (Low Latency)

    [Planner Agent] ➔ [Self-Reflection / MCP Validation] ➔ [User Output]


                    2. Asynchronous Release / CI Gate (High Rigor)

    [Candidate Output]
           ↓
    [Independent Auditor]
           ↓
    Hard Violations Detected?
           ├── YES ➔ BLOCK (Flag for human review or replan)
           └── NO  ➔ RELEASE (Approve for execution)
```

---

## 5. Conclusion & Phase 2 Checklist Status

The core Phase 2 experimental question is answered: **Independent gatekeeping decouples overall narrative quality from hard constraint compliance.** 

Artifact dataset: [`results/multi-model-benchmarks/v3_auditor_comparison.json`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/multi-model-benchmarks/v3_auditor_comparison.json)
