# Calibration corpus (Sprint 1 prelude)

Unlabeled frozen agent outputs for a later single-rater pass. Harvest copies `scenario.md` + `output.md` + `meta.json`. Human `labels.json` files are absent until labeling.

Harvested judge scores live only in `meta.json`. The labeling helper never reads them.

Each `labels.json` (schema version 2) holds five 0–100 dimension scores **and** six typed decisions: release approve/block, hard failure, policy violation, needs human review, primary failure category, and rater confidence. Label decisions directly; do not derive them from scores. See the `labels.json` section of `docs/superpowers/specs/2026-09-10-sprint1-judge-reliability-design.md`.

## Harvest snapshot (2026-09-13)

Command:

```text
evalrun harvest-calibration --results results --scenarios evals/scenarios --output evals/calibration
```

| Bucket | Harvested | Generated | Total |
| --- | ---: | ---: | ---: |
| Budget | 6 | 1 | 7 |
| Route Optimization | 0 | 6 | 6 |
| Remote Worker | 0 | 6 | 6 |
| Replanning | 6 | 1 | 7 |
| Information Gathering | 0 | 7 | 7 |
| Support triage | 2 | 5 | 7 |
| **Total unique** | **14** | **26** | **40** |

- **Gate:** unique count ≥ 40 **and** at least one case in every bucket. **Met (2026-09-26).**
- Harvested cases come from retained `*_itinerary.md` outputs and the MCP baseline/mcp audit files, deduped by SHA-256 of whitespace-normalized text.
- Generated cases were produced by the agent (never the judge) with:

```text
evalrun generate-calibration \
  --dir evals/calibration \
  --model gemini-3.7-flash \
  --base-url https://generativelanguage.googleapis.com/v1beta/openai/ \
  --api-key "$GEMINI_API_KEY"
```

- Generator mix: 33 of 40 outputs come from `gemini-3.7-flash`, so the corpus may under-represent weak outputs. Check the spread of your labels before trusting agreement statistics.

## Commands

```text
evalrun harvest-calibration --results results --output evals/calibration
evalrun generate-calibration --dir evals/calibration --model gemini-3.7-flash \
  --base-url https://generativelanguage.googleapis.com/v1beta/openai/
evalrun label-calibration --dir evals/calibration --port 8502
```

`--allow-incomplete-corpus` is a debug hatch only.
