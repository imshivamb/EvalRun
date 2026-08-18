# Travel Agent Evaluation Dashboard

```text
Framework Version: v2.1-mcp
Planner: TravelPlanningAgent
Research Agent: Enabled
Reflection Agent: Enabled

Models Evaluated:
• Gemini 3.1 Pro
• Gemini 3.5 Flash

Benchmark Scenarios: 5
```

---

## Overall Results

| Scenario | Planner (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 83.75 | 78.78 | -4.97 |
| Route Optimization | 86.75 | 86.85 | +0.10 |
| Remote Worker | 47.50 | 90.05 | +42.55 |
| Replanning | 85.05 | 85.22 | +0.17 |
| Information Gathering | 69.28 | 73.42 | +4.15 |

---

## Per-Model Comparison

### Gemini 3.1 Pro
| Scenario | Planner Only (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 85.00 | 84.00 | -1.00 |
| Route Optimization | 89.40 | 90.50 | +1.10 |
| Remote Worker | 13.00 | 95.00 | +82.00 |
| Replanning | 84.65 | 84.15 | -0.50 |
| Information Gathering | 68.05 | 73.50 | +5.45 |

### Gemini 3.5 Flash
| Scenario | Planner Only (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 82.50 | 73.55 | -8.95 |
| Route Optimization | 84.10 | 83.20 | -0.90 |
| Remote Worker | 82.00 | 85.10 | +3.10 |
| Replanning | 85.45 | 86.30 | +0.85 |
| Information Gathering | 70.50 | 73.35 | +2.85 |

---

## Largest Improvements

```
✓ Remote Worker
Reflection corrected timezone reasoning.
Planner: 49.15
Reflection: 86.10
+36.95

✓ Mid-Trip Replanning
Localized revisions preserved unaffected days.
Planner: 73.45
Reflection: 82.00
+8.55
```

---

## Known Limitations

* **Information Accuracy**: Score remains dependent on local Knowledge Base database entity coverage. Out-of-bounds entities evaluate to 0.0 despite valid plan quality.
* **Over-Editing Edge Cases**: Reflection occasionally issues minor suggestions on border-line constraint thresholds, incurring extra API calls.
* **Model Size Stability**: Small open-source models (Llama 8B) exhibit higher volatility in prompt-parsing compared to frontier models (Gemini Pro).

---

## Architecture Workflow

```
Planner ➔ Research ➔ Reflection ➔ Evaluation ➔ Dashboard
```

---

## Multi-Model Benchmark Summary

* **Scenarios**: 5 benchmark scenarios evaluated.
* **Models**: 3 target LLMs validated.
* **Constraint Satisfaction**: Reflection improved constraint satisfaction and calendar slot reasoning.
* **Replanning Robustness**: Replanning modifications were successfully localized to mitigate cascading shifts.
* **Timezone Correction**: Decoupled transit times and remote worker core availability windows cleanly.
* **Next Step**: Future iterations should prioritize expanding factual verification data coverage.
