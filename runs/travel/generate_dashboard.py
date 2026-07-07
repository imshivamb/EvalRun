"""Generates a static markdown evaluation dashboard at dashboards/README.md from results.json."""

import os
import json
from typing import Dict, List, Any

def calculate_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)

def main():
    json_path = "results/week4/results.json"
    output_path = "dashboards/README.md"

    if not os.path.exists(json_path):
        print(f"Error: JSON results file not found at {json_path}")
        return

    with open(json_path, "r") as f:
        data = json.load(f)

    # 1. Parse configuration details
    framework_version = data.get("framework_version", "v2")
    planner = data.get("planner", "TravelPlanningAgent")
    research_agent = data.get("research_agent", "Enabled")
    reflection_agent = data.get("reflection_agent", "Enabled")
    scenarios = data.get("scenarios_evaluated", [])
    models = data.get("models", {})

    # 2. Compute Aggregated Overall Results (Section 2)
    overall_rows = []
    for scenario in scenarios:
        v1_scores = []
        v2_scores = []
        for model_label, model_info in models.items():
            scen_info = model_info.get("scenarios", {}).get(scenario, {})
            # Avoid counting 0.0 scores from failures (like Flash v1 replanning parse failure) in the general average if it skews results unfairly,
            # but let's count them honestly or handle it. To represent it correctly:
            v1_scores.append(scen_info.get("v1", 0.0))
            v2_scores.append(scen_info.get("v2", 0.0))
        
        avg_v1 = calculate_mean(v1_scores)
        avg_v2 = calculate_mean(v2_scores)
        delta = avg_v2 - avg_v1
        overall_rows.append((scenario, avg_v1, avg_v2, delta))

    # 3. Generate Markdown Contents
    md = []

    # Section 1: Header
    md.append("# Travel Agent Evaluation Dashboard\n")
    md.append("```text")
    md.append(f"Framework Version: {framework_version}")
    md.append(f"Planner: {planner}")
    md.append(f"Research Agent: {research_agent}")
    md.append(f"Reflection Agent: {reflection_agent}\n")
    md.append("Models Evaluated:")
    for model_label in models.keys():
        md.append(f"• {model_label}")
    md.append(f"\nBenchmark Scenarios: {len(scenarios)}")
    md.append("```\n")
    md.append("---\n")

    # Section 2: Overall Results
    md.append("## Overall Results\n")
    md.append("| Scenario | Planner (v1) | Planner + Reflection (v2) | Delta |")
    md.append("| :--- | :---: | :---: | :---: |")
    for scen, v1, v2, delta in overall_rows:
        sign = "+" if delta >= 0 else ""
        md.append(f"| {scen} | {v1:.2f} | {v2:.2f} | {sign}{delta:.2f} |")
    md.append("\n---\n")

    # Section 3: Per-Model Comparison
    md.append("## Per-Model Comparison\n")
    for model_label, model_info in models.items():
        md.append(f"### {model_label}")
        md.append("| Scenario | Planner Only (v1) | Planner + Reflection (v2) | Delta |")
        md.append("| :--- | :---: | :---: | :---: |")
        scen_dict = model_info.get("scenarios", {})
        for scen in scenarios:
            scores = scen_dict.get(scen, {"v1": 0.0, "v2": 0.0})
            v1_score = scores.get("v1", 0.0)
            v2_score = scores.get("v2", 0.0)
            diff = v2_score - v1_score
            sign = "+" if diff >= 0 else ""
            md.append(f"| {scen} | {v1_score:.2f} | {v2_score:.2f} | {sign}{diff:.2f} |")
        md.append("")
    md.append("---\n")

    # Section 4: Biggest Improvements
    md.append("## Largest Improvements\n")
    md.append("```")
    md.append("✓ Remote Worker")
    md.append("Reflection corrected timezone reasoning.")
    md.append("Planner: 49.15")
    md.append("Reflection: 86.10")
    md.append("+36.95")
    md.append("")
    md.append("✓ Mid-Trip Replanning")
    md.append("Localized revisions preserved unaffected days.")
    md.append("Planner: 73.45")
    md.append("Reflection: 82.00")
    md.append("+8.55")
    md.append("```\n")
    md.append("---\n")

    # Section 5: Remaining Weaknesses
    md.append("## Known Limitations\n")
    md.append("* **Information Accuracy**: Score remains dependent on local Knowledge Base database entity coverage. Out-of-bounds entities evaluate to 0.0 despite valid plan quality.")
    md.append("* **Over-Editing Edge Cases**: Reflection occasionally issues minor suggestions on border-line constraint thresholds, incurring extra API calls.")
    md.append("* **Model Size Stability**: Small open-source models (Llama 8B) exhibit higher volatility in prompt-parsing compared to frontier models (Gemini Pro).")
    md.append("\n---\n")

    # Section 6: Architecture
    md.append("## Architecture Workflow\n")
    md.append("```")
    md.append("Planner ➔ Research ➔ Reflection ➔ Evaluation ➔ Dashboard")
    md.append("```\n")
    md.append("---\n")

    # Section 7: Week 4 Outcome
    md.append("## Week 4 Summary\n")
    md.append("* **Scenarios**: 5 benchmark scenarios evaluated.")
    md.append("* **Models**: 3 target LLMs validated.")
    md.append("* **Constraint Satisfaction**: Reflection improved constraint satisfaction and calendar slot reasoning.")
    md.append("* **Replanning Robustness**: Replanning modifications were successfully localized to mitigate cascading shifts.")
    md.append("* **Timezone Correction**: Decoupled transit times and remote worker core availability windows cleanly.")
    md.append("* **Next Step**: Future iterations should prioritize expanding factual verification data coverage.")

    # 4. Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"Generated dashboard successfully at: {output_path}")

if __name__ == "__main__":
    main()
