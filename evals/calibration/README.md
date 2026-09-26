# Calibration corpus (Sprint 1 prelude)

Unlabeled frozen agent outputs for a later single-rater pass. Harvest copies `scenario.md` + `output.md` + `meta.json`. Human `labels.json` files are absent until labeling.

Harvested judge scores live only in `meta.json`. The labeling helper never reads them.

Each `labels.json` (schema version 2) holds five 0–100 dimension scores **and** six typed decisions: release approve/block, hard failure, policy violation, needs human review, primary failure category, and rater confidence. Label decisions directly; do not derive them from scores. See the `labels.json` section of `docs/superpowers/specs/2026-09-10-sprint1-judge-reliability-design.md`.

## Harvest snapshot (2026-09-13)

Command:

```text
evalrun harvest-calibration --results results --scenarios evals/scenarios --output evals/calibration
```

| Bucket | Unique cases |
| --- | ---: |
| Budget | 6 |
| Route Optimization | 0 |
| Remote Worker | 0 |
| Replanning | 6 |
| Information Gathering | 0 |
| Support triage | 2 |
| **Total unique** | **14** |

- **Gate:** unique count ≥ 40 **and** at least one case in every bucket. **Not met.**
- Do not label this set for the published claim yet.
- Do not fill missing buckets with extra Budget runs.

## What was kept

- Distinct `*_itinerary.md` outputs for `travel-planning-budget` and `support-urgent-ticket-escalation`.
- MCP `baseline` / `mcp` outputs from `results/mcp-constraint-validation/` (`travel-mid-trip-replanning`).
- Deduped by SHA-256 of whitespace-normalized output text.

## What is missing

Local `results/` has **no** retained outputs for:

- `travel-route-optimization`
- `travel-remote-worker-timezones`
- `travel-information-gathering-uncertainty`

Need **at least 26 more unique cases**, including those three scenarios, before `evalrun label-calibration` can be used without `--allow-incomplete-corpus`.

Fill remaining slots with the agent (not the judge). If a missing scenario cannot produce a unique output, stop and record that — do not pad with extra Budget runs:

```text
evalrun generate-calibration \
  --dir evals/calibration \
  --model gemini-3.7-flash \
  --base-url https://generativelanguage.googleapis.com/v1beta/openai/ \
  --api-key "$GEMINI_API_KEY"
```

## Commands

```text
evalrun harvest-calibration --results results --output evals/calibration
evalrun generate-calibration --dir evals/calibration --model gemini-3.7-flash \
  --base-url https://generativelanguage.googleapis.com/v1beta/openai/
evalrun label-calibration --dir evals/calibration --port 8502
```

`--allow-incomplete-corpus` is a debug hatch only.
