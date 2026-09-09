# Scoring Methodology

The evaluation framework measures agent performance across multiple evaluation dimensions. Each dimension is scored independently on a scale of **0–100**, allowing evaluators to assess specific aspects of an agent's behavior while maintaining detailed feedback.

The framework itself does not assign fixed importance to any evaluation dimension. Instead, individual evaluation profiles define the weighting of each dimension based on the type of AI agent being evaluated. This allows the same evaluation framework to be reused across different domains while adapting to their specific priorities.

The travel profiles do not all use equal weights. The default
`travel-agent` profile weights constraint satisfaction, planning quality,
information accuracy, personalization, and adaptability at 25%, 20%, 20%,
20%, and 15% respectively. Specialized profiles intentionally change these
weights; for example, mid-trip replanning gives adaptability 55% and route
optimization gives planning quality 55%. Always treat the profile recorded in
the run manifest as the source of truth.

### Score Interpretation

| Score  | Interpretation    |
| ------ | ----------------- |
| 90–100 | Excellent         |
| 75–89  | Good              |
| 60–74  | Acceptable        |
| 40–59  | Needs Improvement |
| 0–39   | Poor              |

Weighting decisions are intentionally conservative and should evolve only with
documented empirical evidence. The current evaluator score is not, by itself,
a release decision: independent deterministic checks, auditor gates, and
baseline regression checks may block a run.
