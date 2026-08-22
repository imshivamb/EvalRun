# evalrun

> **Quality Score $\neq$ Release Decision.** An LLM evaluator can rate an itinerary 95/100 while an independent auditor blocks it for hard financial violations.

`evalrun` is a local-first toolkit for testing AI agents. You bring the agent, model, and API key; `evalrun` runs the checks on your machine, saves the evidence locally, and tells you whether the result should be released.

The toolkit works with hosted APIs and models running on your own computer. It does not host models, provide API credits, provision GPUs, or require a hosted account.

---

## 🌟 Key Capabilities

- **3-Tier Release Gatekeeping**:
  - **Evaluator Thresholds**: Qualitative dimension scoring (0–100) via LLM judges.
  - **Independent Auditor Gate**: Hard financial, policy, and math validation (blocks releases on unbudgeted items or currency hallucinations).
  - **Baseline Regression Gate**: Automatically detects score drops ($\Delta \text{score}$) against stored baselines.
- **Local-First & Multi-Model**: Compatible with hosted APIs (OpenAI GPT-5.6, NVIDIA NIM, Gemini) and local model servers (vLLM, Ollama, LM Studio) on `http://localhost:8000/v1`.
- **Standalone HTML Review Reports**: Interactive local HTML report with failure quick-jump bars, auto-opened failing cards, search/filter controls, visual score progress bars, and raw model output inspection.
- **CI Exit Code Contract**:
  - `0`: All scenarios passed evaluator, auditor gate passed, and no regression detected.
  - `1`: Release blocked due to evaluator threshold failure, auditor violation, or baseline score regression.
  - `2`: Runtime error, missing file, or invalid configuration.

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/imshivamb/agent-eval-platform.git
cd agent-eval-platform
pip install -e .
```

### 2. Single Scenario Run (Hosted Model)

```bash
export OPENAI_API_KEY="sk-proj-..."

evalrun run \
  --scenario evals/scenarios/travel-agent/budget-constrained-itinerary.md \
  --agent agents.travel:TravelPlanningAgent \
  --model gpt-5.6-terra \
  --judge-model gpt-5.6-terra \
  --output results/run-001
```

### 3. Local Model Server Run (vLLM / Ollama)

```bash
# Users host their own local OpenAI-compatible server at http://localhost:8000/v1
evalrun run \
  --scenario evals/scenarios/travel-agent/budget-constrained-itinerary.md \
  --agent agents.travel:TravelPlanningAgent \
  --model qwen2.5-72b-instruct \
  --base-url http://localhost:8000/v1 \
  --api-key EMPTY \
  --judge-model gpt-5.6-terra \
  --output results/local-run
```

### 4. Guided Local Web UI

Launch the zero-dependency local web interface:

```bash
evalrun ui --port 8501
```

Open `http://127.0.0.1:8501` in your browser to configure endpoints, select scenarios, run evaluations, view pass/fail/block verdicts, and launch interactive HTML reports.

---

## 🐍 Python SDK Usage

Integrate `evalrun` programmatically into Python automation pipelines:

```python
from framework.sdk import evaluate, compare

# 1. Execute Benchmark Evaluation
results = evaluate(
    scenario="evals/scenarios/travel-agent/budget-constrained-itinerary.md",
    agent="agents.travel:TravelPlanningAgent",
    model="gpt-5.6-terra",
    judge_model="gpt-5.6-terra",
    base_url="http://localhost:8000/v1",
)

# 2. Compare Candidate Results against Baseline
report = compare(
    candidate_results=results,
    baseline="results/run-001",
    max_overall_drop=5.0,
)

if report.release_blocked:
    print(f"RELEASE BLOCKED: {report.summary['blocked_reason']}")
```

---

## 📊 Baseline Regression Testing

Compare a candidate prompt, model version, or code change against a prior baseline run:

```bash
evalrun run \
  --scenario evals/scenarios/travel-agent/budget-constrained-itinerary.md \
  --agent agents.travel:TravelPlanningAgent \
  --model gpt-5.6-terra \
  --judge-model gpt-5.6-terra \
  --baseline results/run-001 \
  --max-regression 5.0 \
  --max-dimension-regression 10.0 \
  --output results/candidate-run
```

### Generated Artifacts

- `manifest.json`: Execution metadata with redacted API credentials.
- `regression_report.json`: Machine-readable score deltas ($\Delta \text{score}$) and gate decisions.
- `report.html`: Standalone interactive HTML report for human inspection.

---

## Distribution and deployment

There is no central service to deploy for the current product. The recommended path is:

1. Publish the repository on GitHub.
2. Add tagged releases and a clear quick-start guide.
3. Users install it locally with `pip install -e .` from a clone.
4. Later publish the package to PyPI so users can run `pip install evalrun`.
5. Host documentation on GitHub Pages if useful; the evaluation engine itself remains local.
6. Users provide their own hosted-model API keys or run their own local model server.

The local UI is intended for local use, not public internet deployment. A shared hosted deployment would be a separate project requiring authentication, secret management, isolation, and hosted execution.

## How a run works

```text
Choose a scenario
      ↓
Run your agent with your chosen model
      ↓
Score the result against the criteria
      ↓
Run the independent auditor
      ↓
Compare with a previous run, if supplied
      ↓
Write JSON and HTML evidence
      ↓
Return PASS or BLOCK
```

The command line is useful for repeatable runs, the Python SDK is useful inside scripts and pipelines, and the local browser interface is useful when you prefer a form. All three use the same evaluation engine.

## 🏗️ Architecture & Documentation

For detailed system component diagrams, dual-pass auditor sequence flows, and release gate decision trees, see [`docs/architecture.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/docs/architecture.md).

- Hosted Models Guide: [`docs/quickstart-hosted.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/docs/quickstart-hosted.md)
- Local Models Guide: [`docs/quickstart-local.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/docs/quickstart-local.md)
- CLI Specification: [`docs/phase4-local-cli-design.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/docs/phase4-local-cli-design.md)
- Regression Engine Design: [`docs/phase5-regression-gates-design.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/docs/phase5-regression-gates-design.md)

---

## ⚠️ Limitations & Reproducibility Guidelines

- **Judge Variance**: LLM judge evaluations can exhibit non-zero variance. For baseline regression testing, fix model versions and set deterministic sampling parameters where available.
- **Local Model Requirements**: Local evaluation throughput depends on server VRAM and concurrency settings. Ensure your local server handles parallel requests cleanly.
- **Credential Security**: Credentials in `manifest.json` and `regression_report.json` are automatically redacted into `"[REDACTED]"`. Never commit unredacted API keys.
