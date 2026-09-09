# EvalRun — Full Project Review and Final Plan

Date: 2026-09-09
Scope: everything in this repository (code, tests, docs, results, packaging, public footprint), read against the goal stated in `docs/12-week-applied-ai-plan.md`: become interview-ready for Applied AI Engineer / AI Evaluation Engineer roles.

Everything below was verified against the working tree unless marked "claimed". Test suite run: 126 passed in 3.8s. `evalrun demo` from an empty directory: exit 0, `report.html` produced. PyPI: `evalrun` 0.4.1 is live; 0.4.2 is the current release candidate.

---

## 1. Verdict in one paragraph

You have built a real, working, published toolkit with a genuinely good central thesis ("quality score is not a release decision") and one strong empirical story (v3 auditor blocking outputs the LLM judge scored 85–99). That is more than most portfolio projects. What it is missing is not features. It is missing three things that an evaluation engineer is specifically hired for: (1) evidence that the evaluator itself was evaluated (calibration, variance, agreement with humans), (2) the ability to evaluate what actually goes wrong in agents (tool calls, trajectories, cost, loops) instead of only the final prose, and (3) a public record whose numbers can be trusted without caveat. The "missing spark" is rigor turned on itself and a demonstration on an agent you did not write. The plan below turns the project from "an eval harness for my travel agent" into "the local-first pytest for AI agents, with a measured judge", and every phase ends with a claim you can defend in an interview.

---

## 2. What exists today (verified inventory)

| Area | State |
| --- | --- |
| CLI `evalrun` | `run`, `demo`, `init`, `validate`, `doctor`, `ui`. Exit codes 0/1/2. Config file (JSON/TOML) with path resolution. |
| Python SDK | `evaluate()` and `compare()` in `framework/sdk.py`. |
| Agent adapters | Python `module:Class`, HTTP endpoint, `cli:` subprocess. Contract is prompt string in, content string out. |
| Model adapter | `OpenAICompatibleLLM` with exponential backoff, token usage capture. Works with hosted and local endpoints. |
| Evaluation | 5 fixed dimensions (Constraint Satisfaction, Planning Quality, Information Accuracy, Personalization, Adaptability), LLM-as-judge per dimension, weighted mean vs threshold. Profiles per scenario. Support-triage swaps in different prompts for the same 5 dimension names. |
| Independent auditor | `IndependentBudgetAuditor`: LLM prompted separately, produces PASS/BLOCK with violation codes. Travel/INR/JPY specific. |
| Regression | Baseline loader + comparator; per-scenario and per-dimension deltas; `regression_report.json`. |
| Reports | Self-contained `report.html` (784-line generator), `manifest.json`, per-scenario JSON and markdown. Credentials redacted. |
| MCP | Real FastMCP stdio server with 3 deterministic tools, wired into the travel agent's replanning loop. Constraints hardcoded for one scenario. |
| Scenarios | 5 travel + 1 support triage. Markdown with fixed headings, YAML frontmatter. |
| Tests | 126 `unittest` tests, all mocked, fast. CI workflow added; coverage still absent. |
| Docs | Architecture, quickstarts (hosted/local), LangSmith comparison, phase design docs, walkthrough. |
| Public footprint | GitHub public repo with description/topics now set, PyPI 0.4.0 and 0.4.1, legacy phase tags alongside `v0.4.x`. |
| Measured results | v1/v2/v2.1/v3 tables in `results/multi-model-benchmarks/comparison.md`; auditor sensitivity suite (20 synthetic cases); MCP before/after on replanning. |

Roughly 12k lines including tests. `cli/main.py` (694) and `cli/html_reporter.py` (784) are the two oversized files.

---

## 3. What is correct and should be kept

1. The thesis. "Quality score is not a release decision" is the right framing for agent evaluation and it is exactly the kind of judgment interviewers probe for. Keep it as the headline.
2. Local-first, bring-your-own-model, no SaaS. This is a real differentiator against LangSmith/Braintrust/Langfuse-hosted, and it is honest about scope in `docs/langsmith-comparison.md`.
3. CI exit-code contract (0/1/2) and portable JSON/HTML artifacts. This is how eval tooling actually gets adopted.
4. Separation of target model, judge model, and auditor model endpoints. Correct design; most hobby eval tools conflate them.
5. Scenario-as-Markdown with required sections and `evalrun validate`. Good UX for non-code authors, good error messages.
6. Offline `evalrun demo` and `evalrun doctor`. Low-friction onboarding, no keys needed.
7. The v3 auditor experiment write-up (`results/independent-auditor/auditor-validation-findings.md`) is a coherent hypothesis → intervention → measured result → limitation story, including the latency finding (230–366s). This is your best interview asset today.
8. MCP integration is real (stdio FastMCP server, real client, tests proving the revision prompt changes). Not a demo stub.
9. Credential redaction in every artifact, and the decision to hold UI keys only in memory.
10. Test suite is fast and hermetic (except `doctor` network probes). 3.8s for 126 tests is the right shape.

---

## 4. What is wrong

### 4.1 Credibility problems (fix before anyone else looks)

These matter more than any feature because an evaluation engineer's product is trust in numbers.

1. **Published tables previously disagreed with stored data.** The quick-win
   correction now reconciles the tracked comparison markdown to the retained
   Gemini values and explicitly removes unsupported GPT/Llama rows. A
   secret-free copy is now published at `docs/evidence/canonical-results.json`,
   with its provenance and limitations documented beside it. The historical
   dashboard is now labeled as non-canonical.
2. **Auditor specificity is 0% and it is not disclosed.** `synthetic_auditor_results.json`: 20 cases, recall 100%, specificity 0%, false-positive rate 100%. The auditor blocked both clean cases. The design target in `docs/phase2-independent-auditor-design.md` was recall ≥85% and specificity ≥90%. The findings doc leads with recall and the v3 BLOCK story and never states that the auditor, as measured, blocks everything. An auditor that blocks everything trivially "catches" every violation; the v3 result is therefore much weaker than presented until specificity is fixed and re-measured.
3. **The flagship walkthrough table was illustrative but presented as measured.** It has now been replaced with the canonical retained Gemini results and an explicit auditor limitation.
4. **"Tested with at least two non-technical users" is checked off and points at `tests/test_ui.py`.** That test starts a local HTTP server with a mocked run. Similarly, "Record and publish the two-minute project walkthrough" is checked and points at a markdown file. Phase 10 is marked complete while the "Pre-publication validation still required" list is entirely unchecked.
5. **`LICENSE` was a 0-byte file** on a public repository that is also published to PyPI. This quick-win pass replaced it with MIT.
6. **CI was missing.** This quick-win pass added a Python 3.10–3.12 GitHub Actions matrix, tests, wheel build coverage, and offline demo verification.
7. **Version/tag chaos.** `v10.0-flagship-release-complete`, `v4.2-phase4-complete`, `v0.4.1` all coexist. Public tags should be `v0.4.1` style only; internal phase names belong in a CHANGELOG.
8. **Repo description and topics are empty** on GitHub. Zero stars is fine for a portfolio project; an empty description is not.

### 4.2 Core design limitations (the reason it feels like it lacks a spark)

1. **The agent contract is single-turn string → string.** `AgentAdapter.run(prompt) -> AgentOutput(content: str)`. Nothing about tool calls, intermediate steps, messages, cost, or turns is captured for external agents. Agent failures in practice are trajectory failures: wrong tool, wrong arguments, infinite loops, silently skipped steps, runaway cost. EvalRun cannot see any of them for an agent it did not write. This is why "any agent can be evaluated" is not yet demonstrated on any agent other than your own.
2. **Five fixed, travel-named dimensions.** `framework/evaluation/dimensions.py` hardcodes Constraint Satisfaction, Planning Quality, Information Accuracy, Personalization, Adaptability. The support-triage scenario had to map SLA compliance into "Constraint Satisfaction" and tone into "Personalization", and the runner special-cases `if profile.name == "support-triage"` to swap evaluators. Custom domains cannot define their own dimensions without the plugin registry, and even then the names are still shared.
3. **The evaluator has never been evaluated.** No judge calibration against human labels, no variance measurement (run the judge N times on the same output), no confidence, no temperature/seed control in `OpenAICompatibleLLM.generate`, no clamping of scores to [0,100]. The regression gate `--max-regression 5.0` is a fixed number with no evidence it exceeds judge noise. If judge σ on a single output is 4–6 points (typical for 0–100 rubric judges), a 5-point gate will flag noise and miss real regressions. An interviewer for an eval role will ask about this within the first ten minutes.
4. **`pass_criteria` and `failure_conditions` in scenarios are parsed but never used.** `EvaluationEngine.evaluate` computes `passed = weighted_mean >= threshold`. The per-dimension bullets under "Evaluation Criteria" are only partially injected into judge prompts. Authors write failure conditions believing they gate; they do not.
5. **The "independent auditor" is a travel-specific LLM doing arithmetic.** Hardcoded INR/JPY, `itinerary_content` parameter names, violation codes about visas and lockers. It takes 230–366s because it asks an LLM to sum a 29-day itinerary. The correct architecture (which the project already argues for in `evals/evaluation-philosophy.md`) is: LLM extracts structured line items → code does the arithmetic and comparison. That is fast, deterministic, generalizable, and would fix the specificity problem.
6. **Deterministic checks are absent from the generic path.** The roadmap lists "reusable code checks for arithmetic, totals, required fields, JSON/schema validity, format contracts" as unchecked. Today every score comes from an LLM.
7. **Travel defaults leak into the generic core.** `BenchmarkRunner` defaults `local_verifier_path="ground_truth/japan_demo.json"`, writes `*_itinerary.md`, defaults `output_dir="scratch"`; `Scenario.profile_name` defaults to `"travel-agent"`; `Benchmark` and `Scenario` are duplicate models with converters. `agents/` (travel, research, reflection, auditor, support) ships inside the PyPI package.
8. **No multi-turn, no datasets, no golden references, no structured-output schema.** The scenario format cannot express a conversation, a set of 50 examples with expected outputs, or "the output must validate against this JSON schema".

### 4.3 Engineering and security issues

Critical:
- `ui/server.py` `/api/run` accepts an arbitrary `agent` specifier and passes it to `resolve_agent`, which does `importlib.import_module` and, for `cli:` specs, `subprocess.run`. The server is plain `HTTPServer` with no CSRF token or origin check and it parses the body as JSON regardless of `Content-Type`, so a `text/plain` POST from any web page you visit can reach `localhost:8501` without a CORS preflight. That is remote code execution from the browser. Fix: allowlist agents in the UI, add a per-session token, reject non-loopback origins, and never expose `cli:`/import specs from the web surface.
- `/eval_results/...` and `/results/...` file serving checks the prefix before resolving, so `eval_results/../.env` resolves inside the workspace and is served. `output_dir` and `baseline` from the POST body are not path-checked at all.

High:
- Judge scores are not clamped or validated (`base_llm.py:92`); the auditor parser does validate. A judge returning 850 passes.
- No `temperature`/`seed` passed to the model; judge determinism is left to provider defaults.
- `langfuse` and `fastmcp` are mandatory dependencies; `from langfuse import observe` at module top of `engine.py` and every agent. Without keys the CLI only mutes logs.
- Packaging installs top-level packages named `cli`, `agents`, `framework`, `ui` into site-packages. `pip install evalrun` will collide with any other project that has a `cli` or `framework` package. Public SDK import is `from framework import evaluate`.
- `framework.sdk` imports `cli.resolver`, `cli.formatter`, `cli.html_reporter` (some inline). The library depends on the CLI layer.
- `framework/mcp/__init__.py` defines `__all__` twice; the second drops the client exports.
- Global mutable registries (`_DYNAMIC_EVALUATOR_REGISTRY`, custom profiles) with `importlib` string imports from config.

Medium:
- `isinstance(e, (TimeoutError, TimeoutError))` in `runner.py:210`.
- Many silent `except Exception: pass` (registry lookups, UI scanning, MCP failure fallback that hardcodes booking IDs in `agents/travel/agent.py:293`).
- `run_directory` prints and drops failures; the SDK path correctly records them as failed results. Two behaviors for the same operation.
- `tests/test_custom_profiles.py:75` constructs `BenchmarkRunner` without `output_dir`, so error paths write to the repo `scratch/` directory. That is where the `<MagicMock name='mock.llm.model_name.replace().replace()' ...>_itinerary.md` files come from.
- Inline imports throughout (`runner.py`, `sdk.py`, `ui/server.py`, `adapters.py`, `registry.py`), against your own workspace rule.
- `cli/main.py` and `cli/html_reporter.py` need splitting (parser / commands; template / builder).
- `evals/scoring.md` says weights are equal; `framework/profiles/travel.py` uses 55/20/15/5/5 for replanning.
- Test quality: several tautologies (`assertIsNotNone(auditor)`, `assertIn(exit_code, (0, 2))`), and "usability" tests that inject the scores they then assert on.

---

## 5. Why it is missing the spark

Put bluntly: the project evaluates your own travel agent with an LLM you have not measured, and reports numbers that do not fully reconcile. Each of those three clauses is fixable, and fixing them is precisely the work that demonstrates the job you want.

- An evaluation engineer's core skill is knowing how much to trust a metric. Today EvalRun has no answer to "how noisy is your judge?" Having that answer, with a chart, is the single most differentiating thing you can add.
- An Applied AI engineer's core skill is making agents reliable in production. Production agent failures are trajectory failures. EvalRun cannot see trajectories.
- "Any agent can be evaluated" is only believable when shown on an agent you did not write, integrated in under five minutes.

The creative move that unlocks all three at once: **an OpenAI-compatible recording proxy**. Any agent, in any framework, in any language, already accepts `base_url`. Point it at `http://localhost:8787/v1` and EvalRun sees every message, tool call, tool result, token count, and latency with zero code changes. That gives you trajectories, cost, replay/caching (rerun the judge without re-running the agent), and a demo that works on LangGraph, OpenAI Agents SDK, smolagents, CrewAI, or a curl script. It is a few hundred lines with `starlette`/`httpx` and it changes what the product is.

---

## 6. Final shape: EvalRun 1.0

One sentence: **the local-first pytest and CI gate for AI agents, with a judge you can trust because it has been measured.**

### 6.1 Six pillars

1. **Cases and assertions.** A case is an input (single prompt or scripted multi-turn) plus assertions. Assertions are, in order of trust: deterministic checks (schema, regex, contains, arithmetic totals, required fields, `tool_called`, `tool_args_match`, `max_steps`, `no_repeated_tool_call`, `max_cost_usd`, `max_latency_s`, custom `python:` check), then LLM rubric scores (with reason and confidence), then gates (auditor-style hard blocks). Deterministic failures are shown separately from judge findings.
2. **Trajectory capture.** Three ways in: (a) recording proxy (zero-code), (b) `@evalrun.trace` decorator / `Trajectory` object for Python agents, (c) import of OpenTelemetry GenAI-semantic-convention spans or a plain JSONL trace. Every run stores a portable `trajectory.json`.
3. **Judge reliability.** `evalrun calibrate`: given a small human-labeled set, runs the judge N times, reports Spearman/Kendall agreement with humans, per-dimension σ, and the minimum regression threshold that exceeds noise at a chosen confidence. Judge calls pass `temperature=0` and `seed` where supported. Optional multi-judge with disagreement routing to human review. Pairwise mode for cases where absolute scoring is unreliable.
4. **Gates and CI.** Statistical regression gate (paired comparison over N runs with a confidence interval) alongside the simple threshold gate. GitHub Action that runs a suite on PR, uploads `report.html` as an artifact, and posts a summary comment. Baselines stored as artifacts or committed manifests.
5. **Human review.** `evalrun review <run>` records reviewer, decision, reason, timestamp into the manifest; review queue in the HTML report for blocks, regressions, and high-disagreement cases.
6. **Reports.** The existing HTML report plus a trajectory view (step list with tool calls and costs), and a calibration report.

### 6.2 Package layout

```
evalrun/
  __init__.py            # evaluate, compare, calibrate, Trajectory, Case
  core/                  # Case, Assertion, Trajectory, Result, Profile (one model, no Benchmark duplicate)
  adapters/              # python, http, cli, proxy_recorder, otel_import
  checks/                # deterministic assertions
  judges/                # rubric judge, pairwise judge, ensemble, calibration
  gates/                 # threshold, regression (statistical), auditor protocol
  regression/
  report/                # html template + builder (template file, not a Python string)
  cli/                   # parser.py, commands/{run,demo,init,validate,doctor,ui,proxy,calibrate,review}.py
  ui/
examples/
  travel_agent/          # TravelPlanningAgent, research, reflection, session memory, MCP server (moved out of the package)
  support_triage/
  external/langgraph_react/   # third-party agent evaluated via proxy, zero code changes
evals/                   # scenarios, calibration labels
tests/
.github/workflows/ci.yml
```

Optional extras: `evalrun[langfuse]`, `evalrun[mcp]`, `evalrun[proxy]`. Core depends on `openai`, `pydantic`, `PyYAML`, `python-frontmatter`, `markdown-it-py` only.

### 6.3 Scenario format v2 (backward compatible)

Keep Markdown scenarios; add optional structured sections so authors can opt into determinism and trajectories:

```yaml
---
id: refund-policy-check
profile: support        # or inline dimensions below
dimensions:             # domain-native names; no more forcing SLA into "Personalization"
  policy_compliance: 40
  tone: 20
  resolution_quality: 40
pass_threshold: 75
checks:                 # deterministic, evaluated before any LLM call
  - type: json_schema
    schema: schemas/refund_decision.json
  - type: tool_called
    name: lookup_order
  - type: tool_not_called
    name: issue_refund       # must escalate, never refund directly
  - type: max_cost_usd
    value: 0.05
  - type: python
    module: checks.refund:total_within_policy
gates:
  - type: auditor
    module: evalrun.gates.arithmetic:LineItemBudgetAuditor
    budget_field: constraints.Budget
turns:                  # optional multi-turn; omitted = single prompt
  - user: "I want a refund for order 1234"
  - user: "It arrived broken, here's the photo"
---
# Description ... (existing sections still required)
```

Existing scenarios keep working: absent `dimensions` and `checks`, behavior is unchanged.

### 6.4 What to cut or move

- Move `agents/travel`, `agents/research`, `agents/reflection`, `framework/memory`, `framework/mcp/server.py` and `constraints.py` to `examples/travel_agent/`. They are the reference application, not the framework. This alone removes most travel leakage from the core.
- Delete the `Benchmark` ↔ `Scenario` duplication; keep one model.
- Delete `framework/llms/gemini.py` and `framework/llms/openai.py` if `openai_compatible.py` covers them (verify usage first).
- The unsupported flagship table is retired; legacy phase tags remain and should be cleaned up during the next release/tagging operation.
- Drop `results/*.md` narratives that cannot be backed by committed JSON, or commit the JSON.

---

## 7. Roadmap

Each phase ends with a defendable interview claim. Estimates assume focused part-time work; halve them for full-time.

### Sprint 0 — Credibility and safety (2–3 days). Do this first.

- Reconcile `comparison.md` with `results.json`: one canonical table; commit the supporting JSON (they contain no secrets) or delete the unbacked rows. Add the auditor confusion matrix (TP 18, FP 2, TN 0, FN 0; specificity 0%) to the auditor findings, directly under recall.
- The flagship walkthrough table has been replaced with canonical evidence. The
  user-study and walkthrough-video claims are now honestly unchecked in the
  local task checklist.
- A real MIT `LICENSE`, GitHub description/topics, `CHANGELOG`, and CI workflow
  are now present. Legacy phase tags remain for a deliberate cleanup during
  the next tagged release.
- Add `.github/workflows/ci.yml`: Python 3.10–3.12 matrix, `pytest`, `evalrun demo`, `pip install .` from wheel. Add `pytest.ini`/`[tool.pytest.ini_options]`, mark `doctor` network tests and skip them in CI.
- UI lockdown: agent allowlist (built-ins plus explicitly registered), per-process CSRF token in `index.html` checked on POST, reject requests whose `Origin`/`Host` is not loopback, path-check `output_dir` and `baseline`, resolve-then-check file serving.
- Clamp judge scores to [0,100] and reject non-numeric; pass `temperature=0` to judge and auditor calls; fix `(TimeoutError, TimeoutError)`; fix `framework/mcp/__init__.py` `__all__`.
- Make `BenchmarkRunner.output_dir` required; fix `tests/test_custom_profiles.py` to use a temp dir; delete `scratch/` MagicMock files.
- Make `langfuse` optional: a no-op `observe` when the package or keys are absent; move to `[langfuse]` extra.

Claim after Sprint 0: "Every number in the repo is backed by a committed artifact, and I disclosed the auditor's 0% specificity rather than hiding it."

### Sprint 1 — Judge reliability (1.5–2 weeks). Highest career value per hour.

- Build a calibration set: 40–60 saved agent outputs (you already have dozens under `results/`), each with a human score per dimension from you (and ideally one other person). Store under `evals/calibration/`.
- `evalrun calibrate --scenario ... --labels ... --repeats 5`: runs the judge N times per output, reports per-dimension σ, Spearman/Kendall vs human, per-dimension bias, and "minimum detectable regression at 95%".
- Add `confidence` to `DimensionScore`; add optional `--judges` (2–3 models) with median aggregation and disagreement routing.
- Replace the fixed `--max-regression 5.0` default with a statistical gate: `--regression-mode statistical --runs 3` computes a paired mean delta with a CI; block only when the CI excludes zero and the point estimate exceeds the threshold. Keep the simple mode.
- Inject `pass_criteria`/`failure_conditions` and the per-dimension criteria bullets into judge prompts; hard-fail when a failure condition is asserted by the judge with high confidence.
- Write-up: "I measured my LLM judge. σ was X points; my 5-point regression gate was inside the noise. Here is what I changed." This is your second article. It is more compelling than the auditor article because almost nobody does it.

Claim: "I quantified judge variance and agreement with humans, and redesigned the regression gate so it cannot fire on noise."

### Sprint 2 — Deterministic checks and auditor v2 (2 weeks)

- `evalrun/checks/`: `json_schema`, `regex`, `contains`, `required_fields`, `arithmetic_total`, `python` custom, `max_latency_s`, `max_cost_usd`, `max_tokens`. Run before any LLM call; report separately in HTML and manifest.
- Auditor v2 (`LineItemBudgetAuditor`): LLM extracts line items to a strict JSON schema (structured output), Python sums and compares to the budget parsed from `constraints`. Generic: currency and budget field configurable. Target: under 15s, specificity ≥90% on the 20-case suite. Keep the LLM-only auditor as arm B.
- Re-run the synthetic suite and the v1/v2/v3 comparison with auditor v2. Publish the before/after confusion matrices side by side.
- Domain-native dimensions: profiles define their own dimension names and rubric prompts; remove the `support-triage` special case from the runner; move travel rubrics to the travel profile.

Claim: "I replaced an LLM-arithmetic auditor (0% specificity, 4–6 minutes) with extract-then-compute (≥90% specificity, seconds) and re-measured the v3 result honestly."

### Sprint 3 — Trajectories and the recording proxy (2–3 weeks). This is the spark.

- `Trajectory` model: ordered steps of `{role, content, tool_calls, tool_results, tokens, latency_ms, cost_usd}`. Persist `trajectory.json` per case.
- `evalrun proxy --upstream https://api.openai.com/v1 --port 8787 --record runs/rec-001`: OpenAI-compatible `/v1/chat/completions` (streaming and non-streaming) that forwards, records, and computes cost from a small price table. Same proxy adds `--replay` mode: serve cached responses by request hash so judge-only reruns cost nothing and tests are deterministic.
- Trajectory checks: `tool_called`, `tool_not_called`, `tool_args_match` (JSON path), `max_steps`, `no_repeated_tool_call`, `first_tool_is`, `ends_with_final_answer`.
- Trajectory view in `report.html`.
- `examples/external/`: evaluate one popular open-source agent (a LangGraph ReAct agent or an OpenAI Agents SDK agent) with zero code changes via the proxy, plus a scenario that catches a real tool-misuse failure. Record a 90-second GIF of this.
- Optional: import OTel GenAI spans (JSON) into `Trajectory` so Langfuse/Phoenix users can bring traces.

Claim: "Any agent that speaks the OpenAI API can be evaluated at trajectory level with zero integration; here is a third-party agent's tool-misuse caught by a deterministic check."

### Sprint 4 — CI product and 1.0 packaging (1 week)

- `action.yml` GitHub Action: run suite, upload `report.html`, post PR comment with pass/block table and deltas. Dogfood it on this repo with the offline demo and a replay-mode suite.
- Repackage under `evalrun.*` namespace with extras; `from evalrun import evaluate, compare, calibrate`. Deprecation shim for `framework.*` for one release.
- Split `cli/main.py` and `html_reporter.py`. Remove inline imports. Break the `framework → cli` dependency.
- README rewrite around three demos: zero-code proxy evaluation, judge calibration chart, PR comment screenshot. Tag `v1.0.0`.

Claim: "EvalRun 1.0 gates a real PR in CI with a calibrated judge and deterministic trajectory checks."

### Sprint 5 — Optional depth (pick one)

- `evalrun review` and review queue with persisted decisions.
- Multi-turn scenarios with a scripted or LLM-simulated user.
- Pairwise A/B mode with position-swap debiasing.
- Cost/latency budgets as release gates with trend charts across runs.

### If you only have three weeks

Do Sprint 0, Sprint 1, and the proxy plus one external agent from Sprint 3. Skip the rest. Those three produce the strongest interview material per hour: honest numbers, a measured judge, and a zero-code demo on someone else's agent.

---

## 8. Career mapping

| Interview question | Evidence you will have |
| --- | --- |
| "How do you know your evals are reliable?" | Calibration report: σ per dimension, Spearman vs human labels, statistical regression gate. |
| "Tell me about a failure you found with evals." | Auditor v1 blocked everything (0% specificity); v2 extract-then-compute fixed it; v3 result re-measured. |
| "How would you evaluate an agent built by another team?" | Recording proxy, zero code changes, trajectory checks; demo on LangGraph/Agents SDK. |
| "How does this fit in CI?" | GitHub Action posting PR comments, exit-code contract, replay mode for determinism. |
| "What are the limits of LLM-as-judge?" | Variance numbers, disagreement routing, deterministic-first ordering, the 5-point-gate-inside-noise story. |
| "Design an eval platform for a support agent." | Scenario v2 with domain-native dimensions, tool checks, and the support-triage example. |

Articles, in order: (1) the judge-variance article (Sprint 1), (2) auditor v1 → v2 (Sprint 2), (3) zero-code trajectory evaluation of a third-party agent (Sprint 3). Each has a chart and a committed dataset.

README "results" section should contain only numbers that a reader can regenerate from committed artifacts with a documented command.

---

## 9. Quick wins for this week

1. ~~`LICENSE` file, GitHub description and topics, CHANGELOG, CI workflow with `pytest` and `evalrun demo`.~~ Complete.
2. Reconcile or delete contradictory numbers; add the auditor confusion matrix to the findings doc.
3. UI: agent allowlist, CSRF token, path checks. Or, if you would rather not spend time here, mark the UI experimental in the README and disable `/api/run` for non-built-in agents.
4. Clamp judge scores; `temperature=0` on judge/auditor; fix the `TimeoutError` tuple and the `__all__` overwrite.
5. `BenchmarkRunner.output_dir` required; fix the leaking test; delete `scratch/` MagicMock files.
6. Make `langfuse` optional.
7. Fix `evals/scoring.md` to match the actual weights.

---

## 10. Things not to do

- Do not add more travel scenarios or agent features. The travel agent is an example now.
- Do not build a hosted/multi-tenant version. Your positioning is local-first; keep it.
- Do not add a second UI framework or a heavier frontend. The UI is a convenience layer; security first, polish later.
- Do not benchmark more models. Model comparison is not your thesis; judge reliability and trajectory checks are.
- Do not write another phase document before the numbers in the existing ones are reconciled.

---

## 11. Beyond 1.0: EvalRun 2.0 and 3.0

These are conditional. Start none of them before 1.0 ships and before you have market signal (interviews, users, or issues filed). They are here so the 1.0 architecture leaves room for them, and so you can answer "where does this go?" in an interview with a concrete, staged answer instead of a wish list. Everything below stays local-first; nothing requires a hosted service.

### 11.1 EvalRun 2.0 — from testing outputs to testing behaviour (roughly 3–4 months after 1.0)

1.0 answers "did this agent produce an acceptable result on these cases?" 2.0 answers "how does this agent behave under conditions I did not hand-write, and can I trust the judge enough to run it cheaply and constantly?"

1. **Simulated users and adversarial personas.** Multi-turn scenarios (from 1.0) get an LLM-driven user with a goal, a persona, and a budget of turns: impatient, vague, contradictory, hostile, prompt-injecting. The simulator is itself checked (did it stay in character, did it leak the goal). Deliverable: the support-triage suite run against five personas with a per-persona pass matrix.
2. **Scenario synthesis from traces.** Import production or proxy traces (already captured by the 1.0 proxy or OTel import), cluster failed and low-confidence trajectories, and propose new cases with drafted assertions for a human to accept or edit. Evals stop being hand-written one at a time. Deliverable: `evalrun mine runs/ --propose` producing a reviewed batch of 20 cases from a week of proxy traffic.
3. **Tool sandboxes (stateful mock worlds).** Generalize the MCP work: a scenario can declare a mock tool server with seeded state (orders, calendars, bookings, tickets) that records every call and can inject faults (timeouts, 500s, stale data, partial results). Agents are evaluated end-to-end with no real side effects, and fault injection tests recovery behaviour. Deliverable: `evals/worlds/support_store/` plus a suite where 30% of tool calls fail and the assertion is "the agent never claims success it did not verify".
4. **Judge distillation.** By 2.0 you will have hundreds of human-labelled and multi-judge-labelled outputs from `calibrate`. Fine-tune or few-shot-tune a small local model (7–8B) as a rubric judge, measure it against the frontier judge and the human labels on a holdout, and publish the agreement/cost/latency trade-off. A private, cheap, fast judge is exactly what teams want and almost nobody has measured. Deliverable: a table of frontier judge vs local judge vs humans, per dimension, with cost per 1,000 evaluations.
5. **Policy and permission gates on trajectories.** Deterministic checks that a trajectory never called a tool outside its declared permission set, never sent PII to an external tool, never exceeded a per-run spend cap, and paused for approval on declared high-impact actions. These are the "tool permission boundaries" and "human approval" items from the 12-week plan, done at the evaluation layer where they can be tested.
6. **Run history and trends.** A local SQLite store of every run and a `evalrun history` view: score, cost, latency, pass rate per scenario over time, with the statistical gate's confidence intervals drawn on the chart. This is where the 1.0 HTML report grows into a real trend view without becoming a hosted dashboard.
7. **`pytest-evalrun` plugin.** Cases become parametrized pytest tests so teams that already live in pytest get EvalRun with zero new CLI to learn; the 1.0 GitHub Action becomes one option among several.

Interview claim after 2.0: "My evaluator runs continuously against simulated users and fault-injected tools, proposes new cases from real traces, and I replaced 80% of frontier-judge calls with a local judge I measured against humans."

### 11.2 EvalRun 3.0 — closing the loop (12+ months, only if 2.0 has users)

3.0 is about what happens after a failure is found. Each item is powerful and each has a well-known failure mode; the plan includes the guardrail.

1. **Shadow evaluation of live traffic.** The recording proxy samples a percentage of production requests and evaluates them asynchronously against the calibrated judge and deterministic checks, comparing score distributions to the last baseline release. Alerts on drift (model provider silently changed, prompt regression, new user behaviour). Guardrail: sampling and cost caps are mandatory, and PII redaction runs before any judge call.
2. **Guided repair, not auto-repair.** When a case fails, EvalRun proposes candidate fixes (prompt diff, tool description change, added guard) and re-evaluates each on a holdout set the optimizer never sees. Report the fix as a diff with before/after scores and the holdout result. Guardrail: never optimize against the same judge you report on; keep a frozen holdout and a separate judge, and show both numbers, otherwise you are training to the judge (Goodhart) and the numbers are worthless.
3. **Adversarial search.** An attacker agent mutates scenario inputs (paraphrase, add distractors, change constraints slightly, inject instructions) looking for the smallest change that flips a pass to a fail, and reports minimal-diff failure pairs. This is the agent equivalent of fuzzing, and the minimal-diff report is the deliverable, not a raw list of breaks.
4. **Comparative arenas.** Pairwise, position-debiased judging of two agent versions across a suite, with Bradley–Terry style aggregation into a single preference score and confidence interval. This replaces absolute rubric scores where they are least reliable (open-ended generation) and is a natural extension of 1.0's pairwise mode.
5. **Portable agent report cards.** A standardized, versioned, machine-readable summary of a run set: coverage of scenario categories, deterministic pass rates, judge scores with calibration metadata, cost and latency percentiles, known limitations. Produced locally, committed to git or attached to a release, usable for internal sign-off or external compliance documentation. This is the "eval evidence" artifact procurement and governance teams are starting to ask for, and it fits local-first exactly because it is a file, not a service.
6. **Optional shared server, self-hosted, single binary.** If teams want shared history, ship one process that stores runs and serves the trend view, with auth and no cloud dependency. This is the one place where the "no hosted product" non-goal bends, and only to self-hosted. Decide this from user demand, never from ambition.

Interview claim after 3.0: "EvalRun watches production, proposes repairs it cannot game because it never sees the holdout judge, and ships a report card any reviewer can regenerate."

### 11.3 How the 1.0 design keeps these open

- `Trajectory` as the canonical record (not the final string) is what makes simulation, mining, shadow eval, and permission gates possible. Do not compromise on it in Sprint 3.
- The recording proxy is the ingestion point for 2.0 mining and 3.0 shadow evaluation; design it with sampling and redaction hooks from the start even if they are no-ops in 1.0.
- `calibrate` and the labelled dataset format are the training data for judge distillation; store labels in a stable, versioned schema.
- Deterministic checks and gates as pluggable classes are what permission gates and report cards build on.
- Keep every artifact a file in a directory. That single rule is what lets 3.0 exist without a server.

### 11.4 What would make you skip 2.0/3.0

If by the end of 1.0 you have interviews in motion, stop building and interview. The 12-week plan's Day-90 rule still applies: features are the response to "no screens", not to "screens but no offer". 2.0 is worth doing if it becomes the thing you talk about in a job, or if strangers start filing issues.
