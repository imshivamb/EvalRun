# Agent Evaluation Platform (`evalrun`)

> **Quality Score $\neq$ Release Decision.** An LLM evaluator can rate an itinerary 95/100 while an independent auditor blocks it for hard financial violations.

The **Agent Evaluation Platform** is a local-first, domain-neutral evaluation framework for AI agents. It features deterministic MCP constraint verification, independent budget audit gates, generic model adapters, and automated baseline regression testing.

---

## 🌟 Key Capabilities

- **3-Tier Release Gatekeeping**:
  - **Evaluator Thresholds**: Qualitative dimension scoring (0–100) via LLM judges.
  - **Independent Auditor Gate**: Hard financial, policy, and math validation (blocks releases on unbudgeted items or currency hallucinations).
  - **Baseline Regression Gate**: Automatically detects score drops ($\Delta \text{score}$) against stored baselines.
- **Local-First & Multi-Model**: Compatible with hosted APIs (OpenAI, NVIDIA NIM, Gemini) and local model servers (vLLM, Ollama, LM Studio) on `http://localhost:8000/v1`.
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
  --model gpt-4o \
  --judge-model gpt-4o \
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
  --judge-model gpt-4o \
  --output results/local-run
```

---

## 📊 Baseline Regression Testing

Compare a candidate prompt, model version, or code change against a prior baseline run:

```bash
evalrun run \
  --scenario evals/scenarios/travel-agent/budget-constrained-itinerary.md \
  --agent agents.travel:TravelPlanningAgent \
  --model qwen2.5-72b-instruct \
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