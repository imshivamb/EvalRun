# Week 5 Evaluation Findings: MCP-Backed Deterministic Constraint Validation (Updated Flow)

## Executive Summary

Week 5 evaluates **`v2.1` (Planner + Reflection + MCP Validation)** against the **`v2` Baseline (Planner + Reflection)** on mid-trip disruption replanning (`travel-mid-trip-replanning`).

### Architecture Update: Guaranteed MCP Validation
In the updated architecture, **MCP validation executes on EVERY replanning draft**, regardless of whether the Reflection Agent returns `"ITINERARY APPROVED"` or a critique:
1. **Initial MCP Check (`mcp_validation.initial`)**: Evaluates the initial draft's locked booking assertions and itemized savings arithmetic.
2. **Revision Triggering**: Revision is triggered if `reflection_requires_revision OR mcp_requires_revision`.
3. **Final MCP Check (`mcp_validation.final`)**: Verifies the final revised output post-reflection.

---

## Controlled Benchmark Results

| Evaluation Dimension | `v2` Baseline (Planner + Reflection) | `v2.1` MCP Validated (Planner + Reflection + MCP) | Net Improvement ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Overall Score** | **86.40** | **87.30** | **+0.90** |
| **Constraint Satisfaction** | **94.00** | **94.00** | **+0.00** |
| **Adaptability** | **88.00** | **93.00** | **+5.00** |
| **Planning Quality** | **88.00** | **90.00** | **+2.00** |
| **Personalization** | **78.00** | **82.00** | **+4.00** |
| **Information Accuracy** | **42.00** | **45.00** | **+3.00** |
| **Itinerary Completion** | **100% Full Output** (~10,000 chars) | **100% Full Output** (~8,500 chars) | **Both Passed & Verified** |

---

## Verified MCP Execution Trace (`v2.1`)

The execution trace in [`results/week5/mcp-replanning-gpt-5-6-terra.json`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/week5/mcp-replanning-gpt-5-6-terra.json) confirms that MCP tool calls executed on both passes:

```json
"mcp_validation": {
  "initial": {
    "status": "completed",
    "revision_summary": {
      "scenario_id": "travel-mid-trip-replanning",
      "booking_actions": [
        {"booking_id": "kyoto-hostel", "action": "preserve"},
        {"booking_id": "narita-return-flight", "action": "preserve"}
      ],
      "savings_items": [
        {"label": "Cancel Miyajima ferry", "amount_inr": 2000.0},
        {"label": "Supermarket food rule", "amount_inr": 4500.0},
        {"label": "Café drink cap", "amount_inr": 2500.0},
        {"label": "Thrift/shopping freeze", "amount_inr": 7000.0},
        {"label": "Free teamLab replacement days", "amount_inr": 2000.0},
        {"label": "Urban transport walking", "amount_inr": 1000.0},
        {"label": "Kyoto paid add-ons skip", "amount_inr": 1000.0}
      ]
    },
    "revision_check": {"valid": true, "violations": []},
    "savings_check": {"target_savings_inr": 20000.0, "total_savings_inr": 20000.0, "target_met": true}
  },
  "final": {
    "status": "completed",
    "revision_check": {"valid": true, "violations": []},
    "savings_check": {"target_savings_inr": 20000.0, "total_savings_inr": 20000.0, "target_met": true}
  }
}
```

---

## Key Findings

1. **Both Initial and Final MCP Passes Executed**:
   Unlike previous runs where MCP was skipped when reflection approved, `v2.1` now records both `initial` and `final` validation passes.

2. **Adaptability Improvement (+5.0 Points: 88.0 → 93.0)**:
   The evaluator noted that `v2.1`'s post-MCP revision structured its contingency logic exceptionally well:
   > *"The replanning responds directly and coherently to each disruption while keeping changes tightly localized... The budget cut is translated into a clear remaining-trip target and practical, localized reductions that protect sunk costs, essential transport, the flight, and prepaid lodging."*

3. **100% Deterministic Savings Verification (₹20,000)**:
   The MCP tool `calculate_savings` mathematically verified seven itemized cost-saving rules totaling exactly ₹20,000.0, eliminating LLM arithmetic hallucination.

---

## Saved File Locations

- **Raw Benchmark Dataset**: [`results/week5/mcp-replanning-gpt-5-6-terra.json`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/week5/mcp-replanning-gpt-5-6-terra.json)
- **Executive Findings Report**: [`results/week5/mcp-validation-findings.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/week5/mcp-validation-findings.md)
- **`v2` Baseline Raw Output**: [`scratch/mcp/openai/v2_baseline_itinerary.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/scratch/mcp/openai/v2_baseline_itinerary.md)
- **`v2.1` MCP Validated Raw Output**: [`scratch/mcp/openai/v2_1_mcp_itinerary.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/scratch/mcp/openai/v2_1_mcp_itinerary.md)
