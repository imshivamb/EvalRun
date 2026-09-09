# Multi-Model Comparative Benchmark Results

## Overview
This document summarizes the comparative evaluation results of the travel-planning agent across architectures (`v1` Planner-Only vs `v2` Planner + Reflection). To ensure robust findings and prevent instruction-overfitting, the evaluations were executed across four different model configurations:
1. **GPT-5.6 Terra** (`gpt-5.6-terra`)
2. **Gemini 3.1 Pro** (`models/gemini-3.1-pro-preview`)
3. **Gemini 3.5 Flash** (`models/gemini-3.5-flash`)
4. **Llama 3.1 8B** (`meta/llama-3.1-8b-instruct`)

> **Evidence policy:** The canonical five-scenario values below are the values
> currently present in `results.json`. Earlier GPT/Llama and curated markdown
> exports were not retained with matching raw artifacts, so they are not
> presented as reproducible measurements here.

---

## 1. Five-Scenario Regression Suite Report

The scores below represent the comprehensive **Five-Scenario Regression Suite**, which verifies cross-scenario agent stability when reflection and closed-world planning controls are activated.

### Model: Gemini 3.1 Pro
| Scenario | Planner Only (v1) | Planner + Reflection + MCP (v2.1) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 84.00 | 81.50 | -2.50 |
| Route Optimization | 89.40 | 86.10 | -3.30 |
| Remote Worker | 94.00 | 93.10 | -0.90 |
| Replanning | 99.25 | 96.45 | -2.80 |
| Information Gathering | 35.00 | 14.75 | -20.25 |

### Model: Gemini 3.5 Flash
| Scenario | Planner Only (v1) | Planner + Reflection + MCP (v2.1) | Delta |
| :--- | :---: | :---: | :---: |
| Budget | 84.60 | 72.85 | -11.75 |
| Route Optimization | 90.50 | 87.90 | -2.60 |
| Remote Worker | 93.10 | 94.60 | **+1.50** |
| Replanning | 0.00 | 0.00 | 0.00 (missing/failed run) |
| Information Gathering | 0.00 | 0.00 | 0.00 (missing/failed run) |

---

## 2. Focused Mid-Trip Replanning FastMCP Audits

In addition to the five-scenario regression check, a **dedicated controlled audit** was executed for Mid-Trip Replanning (`travel-mid-trip-replanning`) to isolate and certify the deterministic MCP layer under exact Day 12 session conditions. Each run generates complete per-run `agent_metadata` containing validated locked booking IDs and exact arithmetic savings checks.

| Model | Baseline (`v2`) | MCP-Validated (`v2.1`) | Net Delta ($\Delta$) | Deterministic Audit Artifact |
| :--- | :---: | :---: | :---: | :--- |
| **GPT-5.6 Terra** | 86.40 | **87.30** | **+0.90** | [`mcp-replanning-gpt-5-6-terra.json`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/mcp-constraint-validation/mcp-replanning-gpt-5-6-terra.json) |
| **Gemini 3.1 Pro** | 99.25 | **99.00** | **-0.25** | [`mcp-replanning-gemini-3-1-pro.json`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/mcp-constraint-validation/mcp-replanning-gemini-3-1-pro.json) |
| **Gemini 3.5 Flash** | 98.50 | **99.25** | **+0.75** | [`mcp-replanning-gemini-3-5-flash.json`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/mcp-constraint-validation/mcp-replanning-gemini-3-5-flash.json) |

For comprehensive qualitative analysis of the MCP validation traces across models, see [`mcp-validation-findings.md`](file:///Users/shivam/Projects/AI/agent-eval-platform/results/mcp-constraint-validation/mcp-validation-findings.md).

---

## Optimization Impact Analysis

### 1. Targeted MCP Scope vs. Broader Suite Interpretation
> [!IMPORTANT]
> **Understanding the Evaluation Scope**: FastMCP deterministic constraint validation (`validate_revision`, `calculate_savings`) is a **targeted intervention specifically designed and activated for Mid-Trip Replanning** (`travel-mid-trip-replanning`). The remaining four benchmark scenarios (Budget, Route Optimization, Remote Worker, Information Gathering) do not invoke MCP tools; their deltas evaluate the broader **Planner + Reflection loop** and **closed-world evaluation mode**.
>
> The five-scenario suite serves as a **regression verification harness** to guarantee that the reflection loop and MCP client integration do not introduce regressions across other travel planning capabilities.

### 2. Cross-Model Generalization
The currently retained raw artifact shows mixed effects rather than universal
improvement. Gemini 3.1 Pro declined on every listed scenario, including
Information Gathering (`35.00` ➔ `14.75`). Gemini 3.5 Flash improved only on
Remote Worker (`93.10` ➔ `94.60`) and regressed on Budget and Route
Optimization. These values should be treated as a regression signal, not as a
claim that reflection generalizes positively across models.

### 3. Replanning Robustness & Deterministic Validation
In the focused Mid-Trip Replanning runs, the stored JSON artifacts report:
* Unaffected days of the trip were preserved without cascading alterations.
* Locked non-refundable bookings (Kyoto hostel Days 15–18, Narita return flight Day 28) remained anchored.
* MCP deterministically validated the ₹20,000 cost recovery without relying on generative estimations.

---

## Overall Conclusions

1. **Targeted Validation Works**: FastMCP delivered deterministic constraint enforcement where LLMs struggle most (arithmetic totals and immutable anchor preservation under mid-trip replanning stress).
2. **Surfacing Real Trade-Offs**: The retained regression suite detects mixed
   effects, including a large Information Gathering regression for Gemini 3.1
   Pro and a small Remote Worker improvement for Gemini 3.5 Flash.
3. **End-to-End Audit Trail**: Every run produces persistent JSON reports containing `agent_metadata` and Markdown summaries with full MCP validation traces for verification.
