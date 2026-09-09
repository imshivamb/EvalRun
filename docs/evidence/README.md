# Canonical evidence artifacts

`canonical-results.json` is the public, secret-free evidence artifact for
retained EvalRun measurements. It includes:

- the five-scenario Gemini regression suite
- focused mid-trip replanning MCP audits (GPT-5.6 Terra and both Gemini models)
- the v3 independent-auditor comparison
- the 20-case auditor sensitivity confusion matrix

Full itinerary text and judge reasons are omitted. Missing or failed
five-scenario runs are marked explicitly rather than treated as successful
zeros. Llama five-scenario rows were not retained and are not published.

Narrative interpretation:

- [`results/multi-model-benchmarks/comparison.md`](../../results/multi-model-benchmarks/comparison.md)
- [`results/mcp-constraint-validation/mcp-validation-findings.md`](../../results/mcp-constraint-validation/mcp-validation-findings.md)
- [`results/independent-auditor/auditor-validation-findings.md`](../../results/independent-auditor/auditor-validation-findings.md)

These are historical artifacts, not a claim that current provider responses
are reproducible today. Future runs must record model versions, prompts,
scenario versions, and judge configuration before adding benchmark claims.
