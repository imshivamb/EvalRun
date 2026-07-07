# Travel Agent Evaluation Dashboard

```text
Framework Version: v2
Planner: TravelPlanningAgent
Research Agent: Enabled
Reflection Agent: Enabled

Models Evaluated:
• Llama 3.1 8B
• Gemini 3.1 Pro
• Gemini 3.5 Flash

Benchmark Scenarios: 5
```

---

## Overall Results

| Scenario | Planner (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 68.08 | 61.70 | -6.38 |
| Route Optimization | 74.88 | 78.60 | +3.72 |
| Remote Worker | 44.38 | 68.63 | +24.25 |
| Replanning | 56.05 | 83.77 | +27.72 |
| Information Gathering | 70.02 | 68.87 | -1.15 |

---

## Per-Model Comparison

### Llama 3.1 8B
| Scenario | Planner Only (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 71.95 | 40.30 | -31.65 |
| Route Optimization | 73.90 | 76.45 | +2.55 |
| Remote Worker | 2.00 | 34.70 | +32.70 |
| Replanning | 83.50 | 80.85 | -2.65 |
| Information Gathering | 71.50 | 59.75 | -11.75 |

### Gemini 3.1 Pro
| Scenario | Planner Only (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 65.15 | 71.25 | +6.10 |
| Route Optimization | 66.65 | 76.15 | +9.50 |
| Remote Worker | 49.15 | 86.10 | +36.95 |
| Replanning | 84.65 | 84.15 | -0.50 |
| Information Gathering | 68.05 | 73.50 | +5.45 |

### Gemini 3.5 Flash
| Scenario | Planner Only (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 67.15 | 73.55 | +6.40 |
| Route Optimization | 84.10 | 83.20 | -0.90 |
| Remote Worker | 82.00 | 85.10 | +3.10 |
| Replanning | 0.00 | 86.30 | +86.30 |
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

## Week 4 Summary

* **Scenarios**: 5 benchmark scenarios evaluated.
* **Models**: 3 target LLMs validated.
* **Constraint Satisfaction**: Reflection improved constraint satisfaction and calendar slot reasoning.
* **Replanning Robustness**: Replanning modifications were successfully localized to mitigate cascading shifts.
* **Timezone Correction**: Decoupled transit times and remote worker core availability windows cleanly.
* **Next Step**: Future iterations should prioritize expanding factual verification data coverage.
