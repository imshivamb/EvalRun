# EvalRun — Final Product and Career Strategy

Date: 2026-09-20  
Status: final strategic direction; implementation remains governed by the sprint specifications  
Primary goal: build a credible, useful agent-evaluation product while becoming interview-ready for AI Evaluation Engineer and Applied AI Engineer roles

## 1. Executive decision

Continue with the existing plan, but narrow the product claim.

EvalRun should not claim to be the best general-purpose AI evaluation platform. That category includes evaluation, observability, tracing, prompt management, datasets, production monitoring, red-teaming, and collaboration products with much broader scope.

EvalRun should aim to become:

> **The best local-first, evidence-grade CI evaluation system for tool-using agents—combining deterministic assertions with a measured LLM judge.**

Its core promise should be:

> Describe acceptable behaviour, run or import an agent execution, and receive a reproducible release verdict with the evidence behind it.

The product's canonical unit is:

> **Case + trajectory + assertions + verdict + evidence bundle**

Every 1.0 feature should strengthen one part of that unit. Features that do not should be deferred.

## 2. Why this direction is strong

EvalRun already has more substance than a typical portfolio agent project:

- A published CLI and Python SDK.
- Local and hosted OpenAI-compatible model support.
- Separate target, judge, and auditor model configuration.
- Scenario validation and portable JSON/HTML artifacts.
- Regression comparison and CI-friendly `0/1/2` exit codes.
- An offline demo.
- Real MCP-backed validation.
- A second domain beyond travel.
- An unusually valuable failure story: the first auditor achieved 100% recall but 0% specificity and therefore blocked everything.

The strongest existing thesis remains:

> **Quality score is not a release decision.**

That thesis becomes substantially more credible when EvalRun can answer:

1. How reliable is the judge?
2. Which failures were determined by code rather than model opinion?
3. What happened inside the agent trajectory?
4. Can another engineer reproduce the verdict?
5. Does the same system work on an agent the author did not build?

The current final plan correctly prioritizes those questions.

## 3. Current state and honesty boundary

As of this document:

- The calibration prelude exists.
- The corpus contains 14 unique cases, below the required 40–60.
- The diversity floor is not met.
- Human labels have not been completed.
- `evalrun calibrate` has not been implemented.
- Statistical regression gating has not been implemented.
- Generic deterministic assertions have not been implemented.
- Trajectory capture and the recording proxy have not been implemented.
- No third-party-agent trajectory demonstration exists.

Therefore, the following claims must not be made yet:

- “The EvalRun judge is reliable.”
- “The five-point regression threshold exceeds judge noise.”
- “EvalRun can evaluate any agent.”
- “The auditor is production-ready.”
- “A local decision model can replace the rubric judge.”

The public story should distinguish clearly among:

- implemented capability;
- measured result;
- planned capability;
- hypothesis awaiting evidence.

## 4. Product positioning

### 4.1 Category

EvalRun is a developer tool for pre-release agent testing and CI gating. It is not primarily:

- a hosted observability service;
- a prompt-management product;
- an agent framework;
- a model gateway;
- a multi-tenant collaboration platform;
- a production analytics dashboard.

### 4.2 Differentiation

No single phrase such as “local-first,” “pytest for AI,” or “works in CI” should be assumed to be unique.

EvalRun's differentiation is the combination of:

1. **Deterministic-first evaluation**  
   Objective requirements are checked with code before an LLM is asked for an opinion.

2. **Measured judge reliability**  
   Judge agreement, bias, repeat variance, and detectable regression are reported against human labels.

3. **Trajectory-level assertions**  
   Tool use, arguments, loops, permissions, cost, latency, and completion behaviour are testable.

4. **Hard release decisions**  
   Evaluation produces an explicit approve/block/error contract suitable for CI.

5. **Portable evidence**  
   Runs are local files that can be reviewed, committed, uploaded as artifacts, and reproduced.

6. **Framework independence**  
   Agent execution can enter through supported trace contracts rather than requiring adoption of a particular agent framework.

### 4.3 Honest “any agent” claim

The current string-in/string-out adapter is not enough to support “any agent.”

The defensible future wording is:

> EvalRun evaluates agents whose executions can be captured through a supported adapter: an OpenAI-compatible recording proxy, OpenTelemetry spans, a Python trajectory API, or portable JSONL.

This wording is both broad and technically honest.

## 5. EvalRun 1.0

### 5.1 User workflow

The user-facing mental model should remain simple:

1. Define a case and acceptable behaviour.
2. Run or import the agent execution.
3. Evaluate deterministic assertions.
4. Evaluate qualitative rubrics where judgment is necessary.
5. Apply hard gates.
6. Compare with a baseline.
7. Produce a report and CI verdict.

A future CLI should converge on:

```text
evalrun init
evalrun record
evalrun run
evalrun compare
```

### 5.2 Required pillars

#### Cases and custom assertions

A case may contain a prompt or scripted interaction, expected constraints, and user-defined assertions.

Priority assertions:

- JSON Schema validation
- required fields
- regex and contains checks
- arithmetic totals
- custom Python checks
- `tool_called`
- `tool_not_called`
- `tool_args_match`
- `first_tool_is`
- `max_steps`
- `no_repeated_tool_call`
- `max_cost_usd`
- `max_latency_s`
- `max_tokens`
- `ends_with_final_answer`

#### Trajectory capture

The canonical trajectory should contain:

- messages and roles;
- tool calls and arguments;
- tool results;
- timing;
- token usage;
- estimated cost;
- errors and retries;
- the final answer.

Ingestion paths:

- OpenAI-compatible recording proxy;
- Python `Trajectory` API or decorator;
- OpenTelemetry GenAI span import;
- plain JSONL import.

Replay should allow judge and assertion changes without re-running the target agent.

#### Judge reliability

`evalrun calibrate` should report:

- repeat variance per dimension;
- bias against human labels;
- Spearman and Kendall agreement;
- failed structured responses;
- minimum detectable regression;
- model, endpoint, temperature, and seed metadata;
- single-rater and dataset limitations.

#### Release gates

The evaluation hierarchy is:

> **deterministic assertions → calibrated qualitative judge → hard gates**

Simple regression mode should remain available for compatibility. Statistical mode should refuse to run without enough paired evidence.

#### Reports and CI

The 1.0 report should show:

- deterministic failures separately from judge findings;
- trajectory steps and tool calls;
- baseline deltas;
- judge calibration metadata;
- cost and latency;
- the exact reason for approve, block, or error.

The GitHub Action should run the suite, post a PR summary, upload the evidence bundle, and return the established exit code.

### 5.3 Completion test

EvalRun 1.0 is complete when a new user can:

1. connect a third-party agent;
2. capture or import its trajectory;
3. author domain-specific assertions;
4. run a suite;
5. compare with a baseline;
6. block a real PR;
7. inspect the measured limitations of the judge;
8. reproduce the verdict from committed or uploaded artifacts.

## 6. Execution order

### Step 1 — Complete the calibration dataset

Follow the locked dataset-first sequence:

- reach 40–60 unique outputs;
- satisfy all scenario buckets;
- label the entire corpus while blinded to historical judge results;
- validate labels;
- only then implement judge measurement.

Do not allow Jev, Laya, proxy work, or additional product ideas to interrupt this stop line.

### Step 2 — Measure the incumbent judge

Implement:

- repeated scoring on frozen outputs;
- variance, bias, Spearman, Kendall, and minimum detectable regression;
- a regenerable JSON report;
- an evidence-backed write-up.

This is the highest-value AI Evaluation Engineer work in the roadmap.

### Step 3 — Add deterministic assertions and auditor v2

Replace LLM arithmetic with:

> structured extraction by a model → deterministic calculation and comparison in code

Re-measure recall, specificity, latency, and failure modes. The old auditor remains a useful baseline.

### Step 4 — Add trajectories, proxy capture, and replay

This is the product's main architectural unlock. It moves EvalRun from final-output scoring to agent-behaviour testing.

### Step 5 — Prove external integration

Evaluate a third-party agent and demonstrate a failure where:

- the final answer appears acceptable;
- the output judge passes or misses the problem;
- the trajectory reveals incorrect tool behaviour;
- a deterministic assertion blocks release.

### Step 6 — Ship the CI product and package cleanup

- Provide `action.yml`.
- Post a PR verdict.
- Upload the report.
- Repackage under `evalrun.*`.
- Move travel-specific code into examples.
- Split oversized CLI and report modules.
- Tag 1.0 only after the full completion test passes.

### Step 7 — Stop and obtain market signal

After 1.0:

- onboard at least three external users or teams;
- measure setup and authoring friction;
- collect failures found and integrations abandoned;
- continue job applications and interviews;
- build 2.0 only in response to evidence.

## 7. Competitive frame

The current comparison set should include, at minimum:

- LangSmith
- Braintrust
- Langfuse
- Arize Phoenix
- DeepEval / Confident AI
- Promptfoo
- Ragas
- Inspect AI

This list is a research frame, not a verified 2026 capability matrix.

The comparison should be refreshed from primary documentation before public claims are made. Compare:

- local/offline operation;
- self-hosting;
- agent trajectory support;
- custom deterministic assertions;
- judge calibration;
- statistical regression;
- replay;
- CI integration;
- human-review workflow;
- OpenTelemetry support;
- supported model protocols;
- data privacy;
- pricing;
- portable artifacts;
- time to first useful evaluation.

The objective is not to claim that competitors lack capabilities. It is to identify a narrow workflow where EvalRun is measurably better.

## 8. Jev and Laya-MLX

### 8.1 Model category

Jev and Laya belong to a different category from a generative rubric judge.

A conventional LLM generates a textual answer token by token. A typed decision model evaluates predefined choices or questions and returns decisions with probabilities, without needing to generate prose.

A useful mental model is:

> **LLMs are workers. Typed decision models are switches.**

Potential decisions include:

- Which agent should handle this request?
- Did the task succeed?
- Was a policy violated?
- Is human review required?
- Which failure category applies?
- Should this run be released?

These models should not automatically replace a generative judge that must interpret an open-ended rubric and explain its reasoning.

### 8.2 Jev

According to the supplied TypeSafe material, Jev is a proprietary hosted typed-decision model intended to return choices, scores, and useful probabilities rather than generated prose.

The supplied sources report:

- hosted API deployment;
- approximately 70–500 ms latency;
- pricing of approximately $0.042 per million input tokens;
- no output-token charge;
- an emphasis on calibrated probabilities.

These are provider- or article-reported figures and must be verified against current TypeSafe documentation before publication.

Source: [UOL overview of Jev](https://www.uol.com.br/tilt/colunas/iagora/2026/09/17/sem-chat-e-quase-sem-custos-como-e-nova-ia-feita-pelo-cocriador-do-chatgpt.ghtm)

### 8.3 Laya-MLX

Laya-MLX is an open-source MLX implementation intended to run small typed-decision models locally on Apple Silicon.

The supplied repository material reports:

- local Apple Silicon execution;
- open checkpoints in roughly the 0.3–0.4B parameter range;
- short-input benchmark medians around 7–13 ms, depending on checkpoint;
- no hosted inference charge when run locally.

These are repository-reported benchmark figures, not independent evidence of decision quality or direct superiority over Jev.

Sources:

- [Laya-MLX repository](https://github.com/mizorewww/laya-mlx)
- [Trendshift repository page](https://trendshift.io/repositories/248935)
- [Zenn discussion of Jev use cases and open implementations](https://zenn.dev/karaage0703/articles/jev-use-cases-open-implementations)

### 8.4 Benchmark warning

“Laya is 50× faster than Jev” is not currently an apples-to-apples conclusion.

The reported Laya latency is local inference on particular Apple hardware and short inputs. The reported Jev latency is end-to-end hosted API latency and therefore includes network and service overhead. Hardware, context length, task difficulty, model quality, and benchmark protocol differ.

The correct statement is:

> Laya-MLX reports materially lower local end-to-end latency on its published short-input benchmark, but no direct quality-controlled Jev comparison has yet established a speed/accuracy frontier.

Source discussing the benchmark limitation: [AI IDE List overview](https://aiidelist.com/blog/what-is-laya-mlx)

## 9. Jev vs Laya-MLX EvalRun experiment

This experiment is worth doing because it connects:

- evaluator reliability;
- calibrated decision-making;
- local inference;
- privacy;
- latency and cost;
- human-review routing.

It should be a bounded research track, not a dependency of EvalRun 1.0.

### 9.1 Research question

> Can a small typed-decision model handle high-volume evaluation triage at materially lower latency and cost while preserving acceptable accuracy and probability calibration?

### 9.2 Do not force typed decisions into the generative judge abstraction

Jev and Laya should initially use an experimental `DecisionModel` interface rather than pretending to be text-generating `OpenAICompatibleLLM` implementations.

Conceptually:

```text
DecisionModel.decide(
    context,
    questions,
    choices
) -> decisions + probabilities + metadata
```

The adapter should preserve:

- raw probabilities;
- model and checkpoint identity;
- local or hosted execution;
- latency;
- cost;
- parse or transport failures.

Integrate this into the stable product only after the benchmark establishes a useful role.

### 9.3 Dataset

Use the same frozen inputs for both models.

The existing five 0–100 rubric scores are not sufficient by themselves. Add blinded human labels for typed decisions such as:

- release: approve/block;
- hard failure present: yes/no;
- human review required: yes/no;
- policy violation present: yes/no;
- primary failure category;
- violated dimensions;
- confidence or ambiguity annotation where the human rater is uncertain.

Do not silently derive every binary label from an arbitrary score threshold. If a threshold-derived label is used, document the transformation and evaluate it separately from directly human-labelled decisions.

Split cases before prompt or policy tuning:

- development set for question wording and adapter debugging;
- frozen holdout for final comparison.

Avoid tuning on the holdout.

### 9.4 Metrics

Decision quality:

- accuracy;
- precision, recall, and F1;
- confusion matrix;
- false-approve rate;
- false-block rate;
- per-category performance;
- performance by domain and input length.

Probability quality:

- Brier score;
- log loss;
- expected calibration error;
- reliability plots;
- selective accuracy at confidence thresholds;
- coverage versus error when uncertain cases are escalated.

Operational quality:

- warm and cold latency;
- p50, p95, and p99 latency;
- throughput;
- input-length sensitivity;
- local memory use;
- energy or power where practical;
- hosted cost per thousand and million decisions;
- transport and structured-response failure rate.

### 9.5 Fair latency protocol

Report two different comparisons:

1. **User-observed end-to-end latency**  
   Local Laya call versus remote Jev API call. This is operationally relevant but includes deployment differences.

2. **Model/service processing latency**  
   Only where each provider exposes trustworthy processing measurements. Do not infer this by subtracting an arbitrary network constant.

Control or record:

- Apple hardware model;
- checkpoint;
- quantization;
- warm-up policy;
- concurrency;
- input length;
- number of decision questions;
- number of choices;
- network location;
- sample count;
- failures and retries.

Never publish a single median as proof of general superiority.

### 9.6 Product roles to test

Test the models in increasing order of risk:

1. **Routing**  
   Choose the evaluator, domain profile, or escalation path.

2. **Review prioritization**  
   Rank cases for human review.

3. **Cheap first-pass evaluation**  
   Evaluate routine binary or categorical requirements.

4. **Judge cascade**  
   Accept high-confidence routine decisions and escalate uncertain or high-impact cases to a stronger judge.

5. **Release gate contribution**  
   Only after false-approve risk and calibration are measured. The typed model should not become the sole hard gate based on latency alone.

### 9.7 Success criteria

Do not select a winner solely by speed.

A typed model earns a product role only if:

- its holdout decision quality meets a declared threshold;
- probability calibration supports the intended automation policy;
- false approvals remain within an explicit risk budget;
- latency and cost improve materially;
- failure behaviour is observable;
- escalation recovers uncertain cases;
- results reproduce across repeated runs.

Possible outcome:

> Laya handles high-confidence local routing and triage; Jev handles cases where its calibration is superior; a generative judge handles open-ended rubric evaluation; humans handle unresolved high-impact disagreement.

That layered architecture is more credible than declaring one universal winner.

## 10. Career positioning

### AI Evaluation Engineer

This is the project's strongest direct fit.

The flagship story should become:

> I measured judge agreement and variance against blinded human labels, discovered whether the existing regression threshold was inside the judge's noise, and redesigned release gating around measured uncertainty.

The Jev/Laya experiment adds:

> I evaluated not only model accuracy but probability calibration and selective automation policies.

### Applied AI Engineer

Strong evidence comes from:

- tool-backed validation;
- structured extraction plus deterministic computation;
- trajectory assertions;
- replay;
- model routing;
- confidence-based escalation;
- external-agent integration;
- cost and latency controls.

### Forward Deployed Engineer

The missing proof is customer integration.

Demonstrate:

- onboarding an agent you did not build;
- translating business policy into assertions;
- adapting to the customer's framework and deployment;
- measuring setup time;
- explaining false positives and model limitations;
- producing a usable release workflow.

One external team using custom evaluations is more valuable than several additional internal features.

### Inference Engineer

EvalRun alone is not sufficient evidence for a dedicated inference-engineering role.

Inference roles typically require deeper work in:

- model serving;
- quantization;
- batching and concurrency;
- KV-cache behaviour;
- GPU or accelerator profiling;
- memory use;
- throughput;
- latency optimization;
- scheduling.

The Laya-MLX benchmark can add credible inference-adjacent evidence if it includes:

- MLX profiling;
- warm/cold behaviour;
- quantization comparisons;
- concurrency and throughput;
- memory measurements;
- input-length scaling.

For inference-heavy applications, pair EvalRun with a separate focused serving or optimization project rather than stretching EvalRun's product scope.

### Additional suitable roles

- Agent Reliability Engineer
- AI Platform Engineer
- AI Engineer — Agents and Evaluation
- Applied ML Engineer working on LLM systems
- Evaluation Infrastructure Engineer

## 11. Portfolio deliverables

The strongest final portfolio package is:

1. A concise README built around the product promise.
2. A calibration report backed by committed labels and JSON.
3. An auditor v1-to-v2 confusion-matrix story.
4. A third-party-agent trajectory failure demo.
5. A real PR blocked by the GitHub Action.
6. A Jev-versus-Laya decision-quality and calibration report.
7. A short walkthrough video.
8. Two or three technical articles, each based only on committed evidence.

Recommended article order:

1. “I measured my LLM judge—and my regression threshold was inside the noise.”
2. “Why an auditor with 100% recall was still useless.”
3. “The final answer passed, but the agent used the wrong tool.”
4. “Jev vs Laya-MLX: accuracy, calibration, latency, and cost on the same evaluation dataset.”

## 12. Product and career stop rules

Do not:

- add more travel scenarios;
- build hosted multi-tenancy before user demand;
- add a heavier frontend;
- publish unsupported benchmark claims;
- call probabilistic model checks deterministic;
- optimize only for judge agreement while ignoring human labels;
- call local latency directly comparable to hosted API latency;
- wait for 2.0 before applying for jobs.

After 1.0:

- If interviews are progressing, prioritize interviewing and storytelling.
- If applications produce no screens, change positioning and targeting.
- If screens do not convert technically, improve the walkthrough and system-design practice.
- Build additional product features only when interviews or users reveal a concrete gap.

## 13. Final recommendation

The current plan is worth following.

The final product should be smaller in scope and stronger in evidence:

> **A local-first agent evaluation and CI system that tests trajectories with deterministic assertions, uses qualitative judges whose reliability has been measured, and produces portable release evidence.**

Jev and Laya-MLX should become a focused evaluation experiment and potentially a typed-decision layer—not a distraction from calibration and not an unmeasured replacement for the rubric judge.

The priority order remains:

1. finish human-labelled calibration data;
2. measure the judge;
3. add deterministic assertions;
4. capture and replay trajectories;
5. prove the system on a third-party agent;
6. gate a real PR;
7. benchmark Jev and Laya on identical frozen cases;
8. stop and obtain market and interview feedback.

If those steps are completed honestly, EvalRun will be a strong portfolio project for AI Evaluation and Applied AI roles and a credible foundation for a useful open-source product.

## 14. Source and verification note

Project claims in this document are grounded in:

- `docs/project-review-and-final-plan.md`
- `docs/12-week-applied-ai-plan.md`
- `docs/superpowers/specs/2026-09-10-sprint1-judge-reliability-design.md`
- the current calibration implementation and manifest

Jev and Laya-MLX facts are attributed to the sources supplied with the request. They were not independently fetched during this update because the configured web-extraction CLI was unavailable. Before publishing model specifications, pricing, or performance numbers, verify them against current primary documentation and record the exact checkpoint, hardware, and benchmark protocol.

