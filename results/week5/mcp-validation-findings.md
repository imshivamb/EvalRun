# Week 5 Evaluation Findings: MCP-Backed Deterministic Constraint Validation

## Executive Summary

Week 5 evaluates **`v2.1` (Planner + Reflection + MCP Validation)** against the **`v2` Baseline (Planner + Reflection)** on mid-trip disruption replanning (`travel-mid-trip-replanning`).

The Model Context Protocol (MCP) server was integrated to serve as a **deterministic validator** for hard constraints—verifying immutable booking locks, non-shiftable flight dates, and calculating exact itemized savings arithmetic rather than relying on creative LLM estimations.

In a fully controlled head-to-head comparison where both configurations generated complete, evaluated traveler-facing itineraries under identical closed-world system instructions (`planning_mode="closed_world_evaluation"`), **`v2.1` scored 89.80**, outperforming the `v2` baseline (**84.25**) by **+5.55 overall points** and boosting **Constraint Satisfaction by +16.0 points (78.0 → 94.0)**.

---

## Controlled Benchmark Results

| Evaluation Dimension | `v2` Baseline (Planner + Reflection) | `v2.1` MCP Validated (Planner + Reflection + MCP) | Net Improvement ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Overall Score** | **84.25** | **89.80** | **+5.55** |
| **Constraint Satisfaction** | **78.00** | **94.00** | **+16.00** |
| **Personalization** | **72.00** | **82.00** | **+10.00** |
| **Planning Quality** | **86.00** | **90.00** | **+4.00** |
| **Adaptability** | **91.00** | **93.00** | **+2.00** |
| **Information Accuracy** | **42.00** | **45.00** | **+3.00** |
| **Itinerary Completion** | **100% Full Output** (~10,000 chars) | **100% Full Output** (~8,500 chars) | **Both Complete & Passed** |

---

## Detailed Findings & Diagnostic Analysis

### 1. Constraint Satisfaction (+16.0 Points: 78.0 → 94.0)

* **`v2` Baseline Failure Mode**:
  While `v2` proposed sensible general spending advice (eating at convenience stores, limiting café drinks), it failed to quantify itemized monetary savings or produce a concrete mathematical plan. The evaluator penalized `v2` for this omission:
  > *"The response gives sensible cost-control measures, but it does not quantify expected savings for any measure... Thus, the budget constraint is only partially satisfied."*

* **`v2.1` MCP Solution**:
  The MCP `calculate_savings` tool verified the agent's proposed itemized savings during the intermediate revision step. The tool feedback forced the LLM to output a concrete, mathematically verified target of **₹1,333/day across Days 13–27 (totaling ₹20,000)** alongside itemized category cuts. The evaluator noted:
  > *"The budget reduction is addressed through a stated ₹1,333-per-day savings target across Days 13–27, which totals approximately ₹20,000, plus concrete cost-cutting measures for food, cafés, shopping, paid attractions, taxis, nightlife, and transport."*

### 2. Personalization (+10.0 Points: 72.0 → 82.0)

* By converting the abstract budget cut into a structured daily target, `v2.1` avoided blanket cancellations of traveler hobbies. Instead, it created dedicated "browsing-first" days in Shimokitazawa and Koenji with a protected discretionary cash envelope, preserving the traveler's core interests in street photography, cafés, and thrift browsing on a backpacker budget.

### 3. Planning Quality & Structural Clarity (+4.0 Points: 86.0 → 90.0)

* The MCP validation report prompted `v2.1` to structure the itinerary with a clear **"Key changes at a glance"** summary table, an **"Immediate Actions Today"** checklist, and explicit conditional fallback rules for Miyajima and teamLab.

---

## Saved Artifacts & Outputs

All raw execution outputs and benchmark datasets are saved in `results/week5/`:
- **Raw Evaluation Dataset**: [`results/week5/mcp-replanning-gpt-5-6-terra.json`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/week5/mcp-replanning-gpt-5-6-terra.json)
- **`v2` Baseline Raw Output**: [`results/week5/v2_baseline_itinerary.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/week5/v2_baseline_itinerary.md)
- **`v2.1` MCP Validated Raw Output**: [`results/week5/v2_1_mcp_itinerary.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/week5/v2_1_mcp_itinerary.md)
