# Canonical evidence artifacts

`canonical-results.json` is the public, secret-free evidence artifact for the
currently retained multi-model benchmark data. It preserves missing/failed
runs as explicit status values rather than treating them as successful zero
scores.

The narrative interpretation is in
[`results/multi-model-benchmarks/comparison.md`](../../results/multi-model-benchmarks/comparison.md).
The auditor limitation is documented in
[`results/independent-auditor/auditor-validation-findings.md`](../../results/independent-auditor/auditor-validation-findings.md).

These are historical artifacts, not a claim that current provider responses
are reproducible today. Future runs must record model versions, prompts,
scenario versions, and judge configuration before adding benchmark claims.
