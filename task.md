- [x] Create `evals/scenarios/travel-agent/information-gathering-uncertainty.md`
- [x] Define `TRAVEL_INFORMATION_GATHERING_UNCERTAINTY_PROFILE` in `framework/profiles/travel.py` and register exports
- [x] Update `compare_models.py` to resolve the new profile dynamically
- [x] Execute comparative evaluations and verify output itineraries for Scenario 5
- [x] Implement `BenchmarkRunner` to automate pipeline orchestration and reporting
- [x] Refactor `compare_models.py` to use `BenchmarkRunner`
- [x] Run unit tests and verify runner outputs
- [x] Build `ResearchAgent` under `agents/research/`
- [x] Add unit tests in `tests/test_research_agent.py` and verify implementation
- [x] Integrate the `ResearchAgent` into the `TravelPlanningAgent`
- [x] Create unit tests in `tests/test_agent_collaboration.py` and verify implementation
- [x] Wire Langfuse tracing (`@observe`) into `TravelPlanningAgent`
- [x] Wire Langfuse tracing (`@observe`) into `ResearchAgent`
- [x] Wire Langfuse tracing (`@observe`) into `EvaluationEngine`
- [x] Extract query planning role into separate `ResearchPlanner` component
- [x] Import `observe` directly from `langfuse` root package
- [x] Run end-to-end verification of multi-agent collaboration with Langfuse enabled
- [x] Design the `SessionMemory` data model and API
- [x] Implement `SessionMemory` class and structure sub-dataclasses (`Booking`, `RemoteWorkSchedule`) under `framework/memory/`
- [x] Integrate `SessionMemory` context rendering into `TravelPlanningAgent.run`
- [x] Add unit tests for memory implementation and planner integration
- [x] Clean up dependency construction and add newline to `TravelPlanningAgent`
- [x] Build `ReflectionAgent` under `agents/reflection/`
- [x] Add unit tests in `tests/test_reflection_agent.py` and verify implementation
- [x] Refactor memory architecture: extract travel-specific schemas to `agents/travel/session.py` (`TravelSessionMemory`), exposing generic `BaseSessionMemory` in `framework/memory/`

## Phase 1 — Deterministic Validation and MCP Reliability

- [x] Define the MCP validation hypothesis, scope, tool contracts, metrics, and non-goals in `docs/week5-mcp-validation-design.md`
- [x] Create a Python 3.12 local environment and add reproducible MCP and Langfuse dependencies
- [x] Implement and test the local MCP validation server (`get_locked_constraints`, `validate_revision`, `calculate_savings`)
- [x] Implement and test the stdio MCP client, including real server discovery and tool invocation
- [x] Define the structured revision-summary contract produced from a draft itinerary
- [x] Integrate MCP validation feedback into the `TravelPlanningAgent` reflection/revision loop
- [x] Add controlled mock-LLM tests proving MCP feedback changes the revision prompt correctly
- [x] Add and test the closed-world evaluation prompt contract for the Phase 1 baseline
- [x] Make v2.1 invoke MCP for every replanning draft and record final validation
- [x] Run the real v2 versus v2.1 Mid-Trip Replanning comparison with GPT-5.6 Terra
- [x] Fix the benchmark runner to propagate scenario context for actual MCP activation
- [x] Repeat the controlled replanning comparison with Gemini models
- [x] Analyze results, document latency and failures, and run the five-scenario regression suite
- [x] Close Phase 1 and tag repository release `v2.1-mcp`

## Productization Roadmap — Local-First Evaluation Toolkit

The product goal is a provider-agnostic evaluation and regression-testing
toolkit for tool-using agents and the models that power them. Hosted APIs and
user-managed local models must use the same adapter contract. The toolkit does
not provision GPUs, host models, or become a multi-tenant SaaS product.

### Phase 2 — Independent Auditor and Generalization

- [x] Define the auditor hypothesis and measurable success criteria (in `docs/phase2-independent-auditor-design.md`)
- [x] Define the auditor input/output contract and failure taxonomy (in `docs/phase2-independent-auditor-design.md`)
- [x] Implement an independent budget-auditor agent with no shared reflection state (in `agents/auditor/`)
- [x] Harden structured-output JSON parser with 10 unit tests (in `tests/test_independent_auditor.py`)
- [x] Run 20-case synthetic sensitivity suite and benchmark recall/specificity (in `results/multi-model-benchmarks/synthetic_auditor_results.json`)
- [x] Add non-mutating v3 evaluation gate layer and run v1/v2/v3 on Budget & Replanning scenarios
- [x] Measure planning-quality, constraint, latency, and cost trade-offs
- [x] Write the Phase 2 failure-analysis report
- [x] Add one minimal second-domain suite (support triage)
- [x] Add a minimal second-domain agent adapter and evaluation profile

### Phase 3 — Generic Evaluation Core and Model Adapters

- [x] Define generic `Scenario`, `EvaluationSuite`, `AgentAdapter`, `ModelAdapter`, `RunTrace`, and `Evaluator` contracts
- [x] Extract travel-specific assumptions behind the generic interfaces
- [x] Preserve the travel suite as an example plugin, not the framework core
- [x] Implement an OpenAI-compatible model adapter for hosted and local endpoints
- [x] Support user-provided `base_url`, model name, and environment-based credentials
- [x] Add a Python agent adapter and HTTP agent adapter
- [x] Add tests for hosted-style and local-style model configurations
- [x] Document that users run and secure their own local model servers

### Phase 4 — Local CLI and Evaluation Suites

- [x] Create the `evalrun` command-line entry point (`cli/main.py`)
- [x] Run an agent against a single scenario or versioned suite from one command
- [x] Support model selection without changing agent code (`--model`, `--base-url`, `--api-key`)
- [x] Separate target agent endpoint and judge endpoint configurations (`--judge-model`, `--judge-base-url`, `--judge-api-key`)
- [x] Save raw outputs, traces, scores, failures, and redacted configuration metadata (`manifest.json`)
- [x] Implement explicit CLI exit codes (`0` = all passed, `1` = eval/gate failed, `2` = runtime error)
- [ ] Generate local HTML reports
- [ ] Add a quick-start example for a hosted model
- [ ] Add a quick-start example for a local OpenAI-compatible model
- [ ] Add a clean-checkout smoke test for the CLI

### Phase 5 — Regression, Reproducibility, and Release Gates

- [ ] Version scenarios, prompts, evaluators, agent adapters, and model configuration
- [ ] Implement baseline comparison and per-dimension deltas
- [ ] Add configurable pass/fail thresholds and regression gates
- [ ] Record latency, token usage, cost when available, retries, and errors
- [ ] Add deterministic run identifiers and reproducible result manifests
- [ ] Add an optional GitHub Actions regression command
- [ ] Test an intentional regression and verify the gate blocks it

### Phase 6 — Trace UX and Documentation

- [ ] Make failed cases easy to inspect from the local report
- [ ] Show model output, tool calls, evaluator findings, and score reasons together
- [ ] Show baseline versus candidate differences
- [ ] Add architecture and data-flow diagrams
- [ ] Rewrite the README around the regression-testing use case
- [ ] Add limitations, judge-model caveats, and reproducibility guidance
- [ ] Record a short project walkthrough

### Phase 7 — External Usability Validation

- [ ] Give the toolkit to at least two engineers or technically capable users
- [ ] Test connecting a Python agent
- [ ] Test connecting a hosted model endpoint
- [ ] Test connecting a user-managed local endpoint
- [ ] Test creating a scenario and interpreting a failure report
- [ ] Record setup failures and confusing concepts
- [ ] Fix only the highest-impact usability issues
- [ ] Re-run the clean-checkout smoke test

### Phase 8 — Flagship Release and Career Packaging

- [ ] Freeze the MVP scope and remove dead/demo-only paths
- [ ] Publish the polished repository README and examples
- [ ] Publish the travel and second-domain suites
- [ ] Publish measured v1/v2/v3 and model-comparison results
- [ ] Publish the MCP audit and its limitations
- [ ] Publish the second technical article based on real results
- [ ] Prepare the two-minute project walkthrough
- [ ] Prepare five interview stories from measured failures and fixes
- [ ] Update resume and portfolio positioning around agent reliability/evals
- [ ] Continue targeted applications and outreach
