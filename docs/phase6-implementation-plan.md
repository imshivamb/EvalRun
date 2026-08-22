# Implementation Plan — Phase 6: Trace UX, Documentation & Failure Visibility

Upgrade the interactive HTML report for seamless failure inspection, document platform architecture with Mermaid data-flow diagrams, and rewrite `README.md` around automated regression testing and release gatekeeping.

---

## 1. Unified Failure Inspection in HTML Report (`cli/html_reporter.py`)

- **Top Failure Navigation Jump Bar**:
  - Adds a "Failure & Block Inspection Bar" right beneath the verdict banner listing every failed, blocked, or regressed scenario with quick anchor links (`#scenario-<id>`).
- **Unified Card Layout**:
  - Group evaluator findings, auditor violations, dimension score reasons, baseline deltas, and raw model output/tool traces together in collapsible tabs or structured sections.
  - Automatically auto-expand failed/blocked/regressed scenario cards upon loading so engineers don't need to manually click open failing cases.

---

## 2. Architecture & Data-Flow Documentation (`docs/architecture.md`)

- Create `docs/architecture.md` containing GitHub Flavored Markdown and Mermaid diagrams:
  1. **High-Level System Architecture**: Evaluator vs Independent Auditor separation.
  2. **Evaluation Core & Adapter Pipeline**: `AgentAdapter` $\rightarrow$ `BenchmarkRunner` $\rightarrow$ `Evaluator` & `BudgetAuditor`.
  3. **Baseline Comparison & 3-Tier Release Gate Engine**: Candidate vs Baseline scenario matching, delta calculation ($\Delta \text{score}$), and exit code decision tree.

---

## 3. Production README Rewrite (`README.md`)

- Rewrite `README.md` focusing on:
  - **Core Problem & Paradigm**: Quality score $\neq$ Release decision. Why LLM evaluators miss hard financial/policy violations and why independent auditors + regression gates are essential.
  - **Quick Start**:
    - Hosted models (`evalrun run --scenario ... --model gpt-4o`)
    - Local models (`evalrun run --scenario ... --model qwen2.5 --base-url http://localhost:8000/v1`)
    - Baseline regression testing (`evalrun run ... --baseline baselines/v1`)
  - **3-Tier Release Gates & Exit Codes**: Explanation of `0`, `1`, `2`.
  - **Artifacts**: `manifest.json`, `regression_report.json`, `report.html`.
  - **Limitations & Reproducibility Guidance**: Temperature, seed, judge model selection caveats.

---

## 4. Test & Verification Plan

- Run full unit test suite:
  ```bash
  PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p "test_*.py"
  ```
- Verify HTML report rendering with auto-expanded failed scenario cards and jump links.
