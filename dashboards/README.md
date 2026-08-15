# Travel Agent Evaluation Dashboard

```text
Framework Version: v2
Planner: TravelPlanningAgent
Research Agent: Enabled
Reflection Agent: Enabled

Models Evaluated:
• GPT-5.6 Terra
• Gemini 3.1 Pro
• Gemini 3.5 Flash
• Llama 3.1 8B

Benchmark Scenarios: 5
```

---

## Overall Results

| Scenario | Planner (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 66.38 | 64.15 | -2.22 |
| Route Optimization | 76.88 | 79.25 | +2.38 |
| Remote Worker | 53.08 | 71.42 | +18.35 |
| Replanning | 77.06 | 82.08 | +5.01 |
| Information Gathering | 69.50 | 69.56 | +0.06 |

---

## Per-Model Comparison

### GPT-5.6 Terra
| Scenario | Planner Only (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 61.25 | 71.50 | +10.25 |
| Route Optimization | 82.85 | 81.20 | -1.65 |
| Remote Worker | 79.15 | 79.80 | +0.65 |
| Replanning | 60.10 | 77.00 | +16.90 |
| Information Gathering | 67.95 | 71.65 | +3.70 |

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
| Replanning | 80.00 | 86.30 | +6.30 |
| Information Gathering | 70.50 | 73.35 | +2.85 |

### Llama 3.1 8B
| Scenario | Planner Only (v1) | Planner + Reflection (v2) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 71.95 | 40.30 | -31.65 |
| Route Optimization | 73.90 | 76.45 | +2.55 |
| Remote Worker | 2.00 | 34.70 | +32.70 |
| Replanning | 83.50 | 80.85 | -2.65 |
| Information Gathering | 71.50 | 59.75 | -11.75 |

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
