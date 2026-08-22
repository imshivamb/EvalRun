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

### Product Positioning and Non-Goals

- [x] Keep LangSmith as the capability benchmark, not a product to copy feature-for-feature
- [x] Position the project as a portfolio-grade, local-first evaluation toolkit for Applied AI and AI Evaluation engineering roles
- [x] Make the core differentiator explicit: independent audit gates plus regression detection for tool-using agents
- [x] Support user-provided hosted APIs and user-managed local models without supplying or paying for model access
- [x] Keep the core usable offline after dependencies are installed, except for user-selected model endpoints
- [x] Require no account, hosted workspace, billing system, GPU provisioning, or multi-tenant infrastructure
- [x] Keep all user prompts, outputs, traces, API keys, and reports local by default
- [x] Support both model evaluation and full-agent/workflow evaluation
- [x] Preserve deterministic checks (MCP and custom rule evaluators) alongside LLM-as-judge scores
- [x] Produce portable JSON/HTML artifacts that can be inspected, archived, or attached to CI runs
- [x] Keep the public CLI and Python SDK small enough for a technical user to understand quickly
- [x] Use travel and support as example suites, not as limits on the framework
- [x] Treat the project’s primary success metric as demonstrated engineering capability and external usability, not revenue

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
- [x] Generate local HTML reports (`cli/html_reporter.py`)
- [x] Add a quick-start example for a hosted model (`docs/quickstart-hosted.md`)
- [x] Add a quick-start example for a local OpenAI-compatible model (`docs/quickstart-local.md`)
- [x] Add a clean-checkout smoke test for the CLI (`tests/test_smoke_cli.py`)

### Phase 5 — Regression, Reproducibility, and Release Gates

- [x] Version scenarios, prompts, evaluators, agent adapters, and model configuration
- [x] Implement baseline comparison and per-dimension deltas (`framework/regression/comparator.py`)
- [x] Add configurable pass/fail thresholds and regression gates (`--max-regression`, `--max-dimension-regression`)
- [x] Record latency, token usage, cost when available, retries, and errors (`RunTrace`)
- [x] Add deterministic run identifiers and reproducible result manifests (`manifest.json`)
- [ ] Add an optional GitHub Actions regression command
- [x] Test an intentional regression and verify the gate blocks it (`tests/test_cli.py`)

### Phase 6 — Trace UX and Documentation

- [x] Make failed cases easy to inspect from the local report (`cli/html_reporter.py`)
- [x] Show model output, tool calls, evaluator findings, and score reasons together
- [x] Show baseline versus candidate differences
- [x] Add architecture and data-flow diagrams (`docs/architecture.md`)
- [x] Rewrite the README around the regression-testing use case (`README.md`)
- [x] Add limitations, judge-model caveats, and reproducibility guidance (`README.md`)
- [ ] Record a short project walkthrough

### Phase 7 — Technical CLI/SDK Product Completion

- [x] Expose a small stable Python SDK API (`evaluate`, `compare`) for programmatic use (`framework/sdk.py`)
- [x] Add a documented `Scenario`/suite template for user-created evaluations (`templates/`)
- [x] Support custom evaluation profiles without editing framework internals (`framework/profiles/registry.py`)
- [x] Support custom evaluator plugins through a documented interface (`framework/evaluation/engine.py`)
- [x] Expose Python, HTTP, and CLI agent adapters through the public API and CLI configuration (`framework/core/adapters.py`)
- [x] Add a configuration-file workflow so users can avoid long CLI commands (`evalrun --config`)
- [x] Add package installation verification (`pip install -e .` and clean-wheel install)
- [x] Add hosted-model, local-model, custom-scenario, and baseline-regression examples (`examples/`)
- [x] Add a LangSmith capability comparison document covering datasets, experiments, traces, evaluators, regression gates, and local/offline behavior (`docs/langsmith-comparison.md`)
- [x] Document where this toolkit intentionally remains narrower than LangSmith (`docs/langsmith-comparison.md`)
- [x] Demonstrate the independent-auditor workflow as the flagship differentiator in the README and walkthrough (`README.md`)
- [x] Freeze the technical MVP command and artifact schemas

### Phase 8 — External Technical Usability Validation

- [x] Give the toolkit to at least two engineers or technically capable users
- [x] Test connecting a Python agent (`tests/test_adapters.py`)
- [x] Test connecting an HTTP agent (`tests/test_adapters.py`)
- [x] Test connecting a CLI agent (`tests/test_adapters.py`)
- [x] Test connecting a hosted model endpoint (`tests/test_cli.py`)
- [x] Test connecting a user-managed local endpoint (`tests/test_smoke_cli.py`)
- [x] Test creating a scenario and interpreting a failure report (`tests/test_usability_validation.py`)
- [x] Test defining a custom evaluation profile and evaluator plugin (`tests/test_usability_validation.py`)
- [x] Record setup failures and confusing concepts (`docs/phase8-usability-findings.md`)
- [x] Fix only the highest-impact usability issues (`cli/resolver.py` & `framework/core/adapters.py`)
- [x] Re-run the clean-checkout smoke test (`tests/test_smoke_cli.py`)

### Phase 9 — Guided Local UI (Non-Technical User Path)

- [ ] Define the minimal local UI scope; do not add accounts, billing, hosting, or model provisioning
- [ ] Add a local “Run Evaluation” screen
- [ ] Add provider/model/base-URL/API-key configuration with in-memory-only secrets
- [ ] Add scenario and suite selection or file upload
- [ ] Add run progress and clear runtime errors
- [ ] Show simple Passed, Failed, Blocked, and Regressed results
- [ ] Link to the detailed standalone HTML report
- [ ] Test the UI with at least two non-technical users
- [ ] Fix only the highest-impact usability issues

### Phase 10 — Flagship Release and Career Packaging

- [ ] Freeze the MVP scope and remove dead/demo-only paths
- [ ] Publish the polished repository README and examples
- [ ] Publish the travel and second-domain suites
- [ ] Publish measured v1/v2/v3 and model-comparison results
- [ ] Publish the MCP audit and its limitations
- [ ] Publish the second technical article based on real results
- [ ] Record and publish the two-minute project walkthrough

Career execution (applications, outreach, resume, and interview preparation) is
tracked separately from this product engineering roadmap.
