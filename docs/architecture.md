# Platform Architecture & Data-Flow Documentation

## Executive Overview

The **Agent Evaluation Platform** provides reproducible evaluation, independent release gatekeeping, generic model adaptation, and automated baseline regression testing for LLM agents.

Key Architectural Principle: **Quality score $\neq$ Release decision.**

While LLM evaluators produce qualitative dimension scores (e.g. 85/100), the **Independent Budget Auditor** enforces strict mathematical, financial, and policy conditions (e.g. unbudgeted luggage lockers, transport omissions, or currency hallucinations) that override qualitative scores and block releases.

---

## 1. System Component Overview

```mermaid
graph TD
    CLI["evalrun CLI (cli/main.py)"] --> Resolver["Dynamic Agent Resolver (cli/resolver.py)"]
    CLI --> Runner["BenchmarkRunner (framework/evaluation/runner.py)"]
    
    Resolver --> AgentAdapter["AgentAdapter (framework/core/adapters.py)"]
    AgentAdapter --> ModelAdapter["OpenAICompatibleLLM (framework/llms/openai_compatible.py)"]
    
    Runner --> Evaluator["LLM Evaluator Engine (framework/evaluation/engine.py)"]
    Runner --> Auditor["Independent Budget Auditor (agents/auditor/budget_auditor.py)"]
    
    Runner --> Artifacts["Result Artifacts (*_report.json, itinerary.md)"]
    
    CLI --> BaselineLoader["Baseline Loader (framework/regression/loader.py)"]
    BaselineLoader --> Comparator["Regression Comparator (framework/regression/comparator.py)"]
    
    Comparator --> Reports["manifest.json & regression_report.json"]
    CLI --> HTMLReporter["HTML Report Generator (cli/html_reporter.py)"]
    HTMLReporter --> HTMLReport["report.html (Interactive Review Layer)"]
```

---

## 2. Evaluation Pipeline & Dual-Pass Auditor Flow

```mermaid
sequenceDiagram
    autonumber
    participant CLI as evalrun CLI
    participant Runner as BenchmarkRunner
    participant Agent as Target Agent
    participant LLM as Target LLM
    participant Evaluator as LLM Judge Evaluator
    participant Auditor as Independent Auditor

    CLI->>Runner: run(scenario_path)
    Runner->>Agent: execute(prompt)
    Agent->>LLM: generate(prompt)
    LLM-->>Agent: Raw Itinerary / Plan Output
    Agent-->>Runner: AgentOutput (content + metadata)
    
    par Qualitative Evaluation
        Runner->>Evaluator: evaluate_dimensions(scenario, output)
        Evaluator-->>Runner: DimensionScores (e.g., 90/100)
    and Hard Policy Audit
        Runner->>Auditor: audit(scenario, output)
        Auditor-->>Runner: AuditReport (gate_decision: PASS / BLOCK)
    end

    Runner-->>CLI: EvaluationResult (scores, auditor_gate, trace)
```

---

## 3. Baseline Comparison & 3-Tier Release Gate Engine

```mermaid
flowchart TD
    Candidate[Candidate Run Results] --> RegEngine[compare_runs Engine]
    Baseline[Baseline Manifest / Reports] --> RegEngine

    RegEngine --> Gate1{1. Evaluator Score Gate}
    Gate1 -- "< Pass Threshold" --> Block[RELEASE BLOCKED Exit Code 1]
    Gate1 -- ">= Pass Threshold" --> Gate2{2. Independent Auditor Gate}

    Gate2 -- "Status == BLOCK" --> Block
    Gate2 -- "Status == PASS" --> Gate3{3. Baseline Regression Gate}

    Gate3 -- "Δ overall < -max_regression OR Δ dim < -max_dim_regression" --> Block
    Gate3 -- "No Regressions" --> Approve[RELEASE APPROVED Exit Code 0]
```

---

## 4. Key Subsystem Responsibilities

1. **`cli/`**:
   - `main.py`: Command-line controller handling argument parsing, run execution, baseline regression invocation, exit code determination (`0`, `1`, `2`).
   - `resolver.py`: Dynamic import and instantiation of Python classes (`module:Class`) or factory functions (`module:factory`).
   - `formatter.py`: Plain-text ASCII terminal summary table formatting and secret redaction.
   - `html_reporter.py`: Self-contained interactive HTML evaluation report with jump bar, search/filter, visual score bars, and baseline deltas.

2. **`framework/core/` & `framework/llms/`**:
   - `adapters.py`: Domain-neutral `AgentAdapter` wrappers (`PythonAgentAdapter`, `HttpAgentAdapter`, `CliAgentAdapter`).
   - `openai_compatible.py`: `OpenAICompatibleLLM` adapter supporting hosted endpoints (OpenAI, NVIDIA NIM, Gemini) and local endpoints (vLLM, Ollama, LM Studio) with exponential backoff retries on transient 5xx/429 errors.

3. **`framework/regression/`**:
   - `loader.py`: Baseline manifest and per-scenario report loader supporting directory paths or isolated manifest files.
   - `comparator.py`: Per-scenario and per-dimension score delta ($\Delta \text{score}$) calculation, missing baseline scenario blocking, and 3-tier release gate evaluation.

4. **`agents/auditor/`**:
   - Deterministic claims extraction and MCP constraint verification enforcing hard financial and policy rules.
