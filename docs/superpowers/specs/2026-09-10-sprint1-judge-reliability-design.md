# Sprint 1 — Judge reliability design

Date: 2026-09-10
Status: draft for review (prelude approved in chat; calibrate/gate included in this spec but not implemented until labels exist)
Repo: EvalRun (`imshivamb/EvalRun`)

Interview claim this sprint must make true:

> I quantified judge variance and agreement with humans, and redesigned the regression gate so it cannot fire on noise.

---

## 0. Sequence (locked)

This is dataset-first. Speed is not the goal.

1. Freeze this schema.
2. Harvest every distinct retained agent output, then generate remaining Gemini runs until the unlabeled corpus has 40–60 cases covering travel (all five current scenarios) and support-triage.
3. You label the **entire** corpus in one pass, blinded to prior judge scores, using a local helper that does not call any LLM.
4. Only after labels exist: implement `evalrun calibrate`, then the statistical regression gate, then confidence / failure-condition hard-fail, then the write-up.
5. A second human rater is not available now. The schema keeps a `rater_id` field so a second rater can be added later without rewriting cases. Until then, every public number is documented as single-rater.

Do not run the judge for calibration, and do not change the regression gate, until step 3 is complete.

---

## 1. Calibration corpus

### Target

- **40–60 cases.** Fewer than 40 is a failed corpus, not a “v1.” More than 60 is allowed but not required.
- **Domains:** travel-agent (five existing scenarios) and support-triage. Do not add new travel scenario files.
- **Uniqueness:** two cases are duplicates if SHA-256 of normalized agent output text is equal. Near-duplicates that differ only by whitespace or trailing newlines are collapsed. Distinct models or distinct scenarios with different text are kept.
- **Diversity floor:** after harvest+generate, the corpus must include at least one case from each of: Budget, Route Optimization, Remote Worker, Replanning, Information Gathering, Support triage. If Gemini generation fails for a scenario, stop and record that — do not silently fill with extra Budget runs.

### Layout

```text
evals/calibration/
  README.md
  manifest.json
  cases/
    <case_id>/
      scenario.md          # copy or pointer to the scenario used
      output.md            # frozen agent output (the only text the rater sees besides the scenario)
      meta.json            # provenance; must not be shown by the labeling helper
      labels.json          # written by the helper; absent until labeled
```

`case_id` is a stable slug: `{scenario_id}__{source_tag}__{short_hash}`.

### `meta.json` (never shown while labeling)

```json
{
  "case_id": "travel-planning-budget__live-gemini-001__a1b2c3d4",
  "scenario_id": "travel-planning-budget",
  "profile": "travel-agent",
  "source": "harvested",
  "source_path": "results/live-gemini-001/gemini-3_7-flash_travel-planning-budget_itinerary.md",
  "generator_model": "gemini-3.7-flash",
  "harvested_judge_overall": 84.0,
  "content_sha256": "..."
}
```

Harvested judge scores live only here, for later debugging. They are not human labels and must not appear in `labels.json` or in the helper UI.

### `labels.json`

```json
{
  "case_id": "travel-planning-budget__live-gemini-001__a1b2c3d4",
  "rater_id": "shivam",
  "schema_version": 2,
  "scale": "0-100-step-5",
  "labeled_at_utc": "2026-09-10T18:00:00Z",
  "scores": {
    "Constraint Satisfaction": 80,
    "Planning Quality": 75,
    "Information Accuracy": 70,
    "Personalization": 65,
    "Adaptability": 80
  },
  "decisions": {
    "release": "block",
    "hard_failure": "yes",
    "policy_violation": "no",
    "needs_human_review": "no",
    "primary_failure_category": "constraint_violation",
    "rater_confidence": "certain"
  },
  "notes": {
    "Constraint Satisfaction": "optional free text"
  }
}
```

Rules:

- Every dimension required by the case’s profile must be present.
- Travel and support-triage both use the current five dimension **names** (support already maps onto those names).
- Each score is an integer in `{0, 5, 10, …, 100}`. Any other value is invalid.
- `rater_id` is `shivam` for this pass.
- `schema_version` is `2`. Version 2 added `decisions`; no version-1 labels were ever written.
- Every decision is required and must be one of its listed choices:
  - `release`: `approve` | `block`
  - `hard_failure`, `policy_violation`, `needs_human_review`: `yes` | `no`
  - `primary_failure_category`: `none` | `constraint_violation` | `factual_error` | `missing_requirement` | `wrong_action` | `unsafe_or_policy` | `low_quality`
  - `rater_confidence`: `certain` | `unsure`
- Decisions must be internally consistent: `approve` is invalid with `hard_failure: yes` or `policy_violation: yes`, and `block` requires a category other than `none`.
- Decisions are labeled directly, never derived from a score threshold. They exist so the same blinded pass can later benchmark typed-decision models (approve/block accuracy, calibration, escalation) on identical frozen cases.
- The helper starts every score and decision blank, so no default value anchors the rater.

### Harvest sources (local, no API)

- `results/**/*_itinerary.md` paired with the sibling `*_report.json` when present.
- MCP audit JSON files under `results/mcp-constraint-validation/` (baseline and mcp `output` fields). These are distinct texts even when the scenario is the same.
- Support-triage report/output pairs.

Do not harvest HTML. Do not invent outputs. Deduplicate by content hash.

### Generate remaining slots (API, after harvest count is known)

- Use existing scenario markdown under `evals/scenarios/`.
- Generator: Gemini via the existing `OpenAICompatibleLLM` adapter (same path as `evalrun run`).
- Run the **agent**, not the judge. Freeze `output.md` only. Do not store a new judge score as a label.
- Stop when unique cases reach at least 40 and diversity floor is met, or at 60, whichever comes first after the floor is met.
- You run this with your keys. The generate step is a command, not a hidden live call from the helper.

### `manifest.json`

Lists every `case_id`, scenario, source (`harvested` | `generated`), whether `labels.json` is complete, and the running unique count. This is the gate: labeling helper will not start until unique count ≥ 40 and diversity floor is met, unless you pass an explicit `--allow-incomplete-corpus` escape hatch (for debugging only; not for the published claim).

---

## 2. Labeling helper (no LLM)

Command: `evalrun label-calibration --dir evals/calibration`

Behavior:

- Reads `manifest.json`, skips already-complete `labels.json`.
- For each remaining case, prints or serves **only** `scenario.md` + `output.md` and a form for five scores.
- Implementation: a local stdlib HTTP page on loopback, same family as `evalrun ui` (localhost, session token, no agent execution). Not a new frontend stack.
- Rejects scores not in the step-5 grid. Requires all five dimensions.
- Writes `labels.json` and updates the manifest.
- Never reads `meta.json` into the page. Never calls an LLM.

This is dataset tooling, not judge measurement.

When every case in the manifest is labeled, print a one-line ready signal: unique count, per-scenario counts, rater_id.

---

## 3. Stop line (locked)

**Allowed before labels exist**

- Directory layout, schema, harvest command, generate command, labeling helper, label validator.

**Forbidden until the corpus is fully labeled**

- `evalrun calibrate` (repeats, σ, Spearman, Kendall, bias, MDE).
- Adding `confidence` to live judge scoring.
- `--judges` ensemble.
- `--regression-mode statistical`.
- Hard-fail on failure conditions.
- The Sprint 1 write-up with measured numbers.

The rest of this document specifies those forbidden pieces so the later implementation is already decided. It is not permission to build them early.

---

## 4. `evalrun calibrate` (after labels)

### What it measures

The **judge**, on **frozen outputs**. It does not re-run agents.

```text
evalrun calibrate \
  --dir evals/calibration \
  --repeats 5 \
  --model <judge-model> \
  --base-url ... \
  --output evals/calibration/calibration_report.json
```

Defaults: `--repeats 5`. Judge calls use existing `temperature=0` (and `seed` where already supported). Repeats still vary because providers are not deterministic; that variance **is** the measurement.

### Per dimension, over labeled cases

For each dimension D, using the human score H and the repeat judge scores J₁…J_R on each case:

- **Judge mean** per case: Ĵ = mean(J).
- **σ (repeatability):** stddev of repeats pooled across cases (document the exact pooling: per-case sample std, then RMS across cases). Use sample standard deviation (n−1). Cases with R < 2 are excluded from σ.
- **Bias:** mean(Ĵ − H) over cases. Same 0–100 units.
- **Spearman ρ** and **Kendall τ** of Ĵ vs H across cases. Implemented as small tested functions, not a new scipy dependency.
- **Minimum detectable regression at 95%:** for a paired comparison of two agent versions, each scored once by this judge, on a suite of N cases:

  MDE = 1.96 × σ_paired

  where σ_paired is estimated from repeat noise as σ × √2 / √N, and N is the number of labeled cases used for that dimension.

  Report MDE next to the current `--max-regression 5.0`. If 5.0 < MDE, the write-up must say the old gate can fire on noise.

### Outputs

- `evals/calibration/calibration_report.json` (committed, secret-free).
- A short markdown summary generated from that JSON.
- HTML is not required in this sprint.

### Failures

- Missing labels → exit 2.
- Judge JSON parse error on a repeat → record that repeat as missing; if a case has fewer than 2 successful repeats, exclude it from σ and count it in a `failed_repeats` tally. Do not impute scores.
- Scores outside 0–100 are already rejected by the judge parser.

---

## 5. Statistical regression gate (after calibrate)

Keep today’s simple gate:

- `--max-regression 5.0` (and per-dimension equivalent) as `--regression-mode simple` (current behavior, renamed default).

Add:

```text
--regression-mode statistical --runs 3
```

`--runs` is how many times **each** of baseline and candidate is evaluated by the judge on the **same frozen agent outputs** (or the same recorded run artifacts). This gate is not “re-run the agent 3 times” unless those artifacts already exist. For this sprint, statistical mode consumes N paired overall scores already produced (repeat judge on frozen outputs). If the user has only one score per side, statistical mode must refuse with exit 2 rather than inventing a CI.

Rule, overall score, paired by scenario:

- Let d_i = candidate_i − baseline_i for each scenario i (or each paired case).
- Mean δ̄, 95% CI using a t interval on the paired differences (N−1 degrees of freedom). N must be ≥ 3.
- **Block only if** (a) the CI does not contain 0 **and** (b) δ̄ < −threshold (threshold still `--max-regression`, default 5.0).

This is stricter than “any 5-point drop.” A noisy −6 with a CI that includes 0 does not block.

Simple mode remains the default so existing CI users do not change behavior until they opt in.

SDK: `compare(..., regression_mode="simple"|"statistical", statistical_runs=3)` with the same refuse-if-insufficient-data rule.

---

## 6. Confidence, criteria injection, multi-judge (after calibrate)

### Confidence

- Extend `DimensionScore` with `confidence: Optional[float] = None` (0.0–1.0).
- Judge JSON schema gains `"confidence": <number 0-1>`.
- Invalid or missing confidence → `None`, not a crash. Do not invent 1.0.

### Failure-condition hard-fail

- `pass_criteria` and `failure_conditions` are already injected into judge prompts (Sprint 0). Keep that.
- Also inject the per-dimension bullets from `benchmark.evaluation_criteria` into that dimension’s rubric (today they are only partially used).
- Additional judge field: `"failure_conditions_triggered": [<string>, ...]`.
- If any listed failure condition is triggered **and** `confidence >= 0.8`, the case `passed` is False regardless of weighted mean. Record the reason in the result. 0.8 is fixed for this sprint (not configurable) so the write-up can cite one number.

### Multi-judge (last, optional if cost is high)

- `--judges model_a,model_b` (2 or 3). Median of Ĵ per dimension. If max−min across judges on a case/dimension is ≥ 15 points, mark `disagreement: true` for routing (report only; no human review queue in this sprint — that is Sprint 5).
- If this ships, it still runs on frozen calibration outputs first, not as a replacement for human labels.

---

## 7. Write-up (last)

A short article/section under `results/` or `docs/` that can only be written from `calibration_report.json`:

- Measured σ per dimension.
- Spearman/Kendall vs the single rater.
- Whether `--max-regression 5.0` is below MDE.
- What changed in the statistical gate.
- Limits: single rater, historical Gemini/travel-heavy harvest, temperature=0 is still noisy.

No number in the write-up that is not in the committed JSON.

---

## 8. Testing

Prelude tests (before labels):

- Dedup by content hash.
- `labels.json` validator rejects 73, 101, missing dimension.
- Helper refuses to expose `harvested_judge_overall`.
- Manifest diversity-floor check.

Calibrate tests (after labels exist, using tiny fixture labels and a MockLLM):

- σ, bias, Spearman, Kendall on a known fixture (hand-computed expected values).
- MDE formula against a fixture σ and N.
- Missing labels → exit 2.
- Failed repeats excluded, not imputed.

Statistical gate tests:

- CI includes 0 → not blocked even if |δ̄| > 5.
- CI excludes 0 and δ̄ < −5 → blocked.
- N < 3 → exit 2.

---

## 9. Non-goals (this sprint)

- Second human rater (schema only).
- Hosted UI, accounts, or a new frontend framework.
- New travel scenarios.
- Measuring the auditor (Sprint 2).
- Trajectory / recording proxy (Sprint 3).
- Changing the five dimension names.

---

## 10. Success criteria

Sprint 1 is done only when all of these are true:

- 40–60 labeled cases in git (outputs + `labels.json`; no secrets).
- `calibration_report.json` committed and regenerable with a documented command.
- Public write-up uses only those numbers.
- Simple regression mode still default; statistical mode implemented and tested.
- Single-rater limitation is stated next to Spearman/Kendall.
