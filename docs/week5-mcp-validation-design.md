# Week 5: MCP-Backed Constraint Validation

## Purpose

This work evaluates whether deterministic MCP tools can improve an agent's
reliability when it revises an itinerary under disruption.

The design does not treat MCP as an additional reasoning agent. The LLM remains
responsible for travel judgment, alternatives, pacing, and personalization. MCP
tools own deterministic validation of hard constraints.

```text
LLM proposes a revision
  → MCP validates hard constraints and arithmetic
  → LLM receives structured validation feedback
  → LLM makes a constrained final revision
  → Evaluation framework measures the outcome
```

## Hypothesis

> Planner + Reflection + MCP validation (v2.1) will improve Constraint
> Satisfaction and Adaptability in disruption replanning without materially
> reducing Planning Quality.

## Evaluation Sequence

### Phase 1: Controlled implementation test

Use `travel-mid-trip-replanning` as the first scenario because it includes:

- Immutable Kyoto accommodation on Days 15–18.
- An immutable Day 28 return flight.
- A canceled ferry requiring a safe replacement.
- A required ₹20,000 cost reduction.
- A requirement to localize changes rather than rewrite unaffected days.

The existing Planner + Reflection configuration is the v2 baseline. The new
configuration is v2.1: Planner + Reflection + MCP validation.

### Phase 2: Regression suite

After the controlled scenario works, evaluate v2.1 across all five travel
scenarios:

1. Budget.
2. Route Optimization.
3. Remote Worker Timezones.
4. Mid-Trip Replanning.
5. Information Gathering Under Uncertainty.

The first scenario establishes the end-to-end contract. The full suite checks
that the added validation context does not create regressions elsewhere.

## MCP Server Responsibilities

The initial server exposes deterministic validation tools only.

### `get_locked_constraints`

Returns booking and schedule constraints that the agent must preserve.

Input:

```json
{"scenario_id": "travel-mid-trip-replanning"}
```

Output includes immutable days, locked booking identifiers, and the locked
departure.

### `validate_revision`

Checks a structured revision summary against locked constraints.

Every replanning proposal must produce this JSON alongside its traveler-facing
itinerary. It is a declaration for deterministic verification, not an
alternative itinerary format:

```json
{
  "scenario_id": "travel-mid-trip-replanning",
  "changed_days": [13, 19, 22],
  "booking_actions": [
    {"booking_id": "kyoto-hostel", "action": "preserve"},
    {"booking_id": "narita-return-flight", "action": "preserve"}
  ],
  "savings_items": [
    {"label": "Kyoto-to-Tokyo night bus instead of Shinkansen", "amount_inr": 12000}
  ]
}
```

`changed_days` lists every day whose plan changes. `booking_actions` must make
an explicit assertion for each locked booking. `savings_items` itemizes each
claimed saving in INR; the MCP server, rather than the model, totals it.
Output returns `valid`, a list of violations, and a human-readable explanation.

### `calculate_savings`

Totals explicit cost-saving substitutions against the required reduction.

Input contains individual changes and savings amounts. Output returns total
savings, the target, the remaining gap, and whether the target is met.

## Division of Responsibility

| Component | Responsibility |
| --- | --- |
| TravelPlanningAgent | Propose itinerary changes and traveler-facing explanation. |
| ReflectionAgent | Identify material itinerary issues; avoid cosmetic changes. |
| MCP validation server | Verify explicit constraints and arithmetic deterministically. |
| Evaluation framework | Measure whether MCP-backed validation improved the result. |

## Metrics

Compare v2 and v2.1 using:

- Overall score.
- Constraint Satisfaction score.
- Adaptability score.
- Planning Quality score.
- Number and type of validation violations caught.
- Claimed savings versus deterministic calculated savings.
- Added tool calls and latency.

## Non-Goals

- MCP does not choose destinations or write traveler-facing recommendations.
- MCP does not replace the reflection agent.
- This week does not build a second server merely to demonstrate multi-server
  discovery.
- This week does not add the independent budget-auditor agent; that is Week 6.

## Definition of Done

1. The local MCP server starts and exposes all three tools.
2. Each tool has deterministic unit tests.
3. A client can discover and call every tool.
4. The replanning workflow uses validation feedback before its final revision.
5. v2 versus v2.1 results are recorded for the controlled scenario.
6. The full five-scenario regression suite is run after the controlled test.
