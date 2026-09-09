# Multi-Model Comparative Benchmark Results

## Overview

This document summarizes retained comparative evaluation results of the
travel-planning agent. Public numbers in this file are copied from
[`docs/evidence/canonical-results.json`](../../docs/evidence/canonical-results.json).

Two retained measurement sets exist:

1. **Five-scenario regression suite** for Gemini 3.1 Pro and Gemini 3.5 Flash
   (`v1` planner-only vs `v2.1` planner + reflection + MCP where activated).
2. **Focused mid-trip replanning MCP audits** for GPT-5.6 Terra, Gemini 3.1 Pro,
   and Gemini 3.5 Flash (`v2` vs `v2.1` on `travel-mid-trip-replanning` only).

Llama 3.1 8B five-scenario rows, and any GPT five-scenario rows, were not
retained with matching artifacts and are not published here.

---

## 1. Five-Scenario Regression Suite Report

The scores below are the comprehensive **Five-Scenario Regression Suite**
values stored in `canonical-results.json`.

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

A dedicated controlled audit was executed for Mid-Trip Replanning
(`travel-mid-trip-replanning`) to isolate the deterministic MCP layer under
Day 12 session conditions. Secret-free scores and dimension breakdowns are in
[`docs/evidence/canonical-results.json`](../../docs/evidence/canonical-results.json).
Qualitative notes are in
[`mcp-validation-findings.md`](../mcp-constraint-validation/mcp-validation-findings.md).

| Model | Baseline (`v2`) | MCP-Validated (`v2.1`) | Net Delta |
| :--- | :---: | :---: | :---: |
| **GPT-5.6 Terra** | 86.40 | **87.30** | **+0.90** |
| **Gemini 3.1 Pro** | 99.25 | **99.00** | **-0.25** |
| **Gemini 3.5 Flash** | 98.50 | **99.25** | **+0.75** |

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
In the focused Mid-Trip Replanning runs, the retained MCP artifacts report:
* Unaffected days of the trip were preserved without cascading alterations.
* Locked non-refundable bookings (Kyoto hostel Days 15–18, Narita return flight Day 28) remained anchored.
* MCP deterministically validated the ₹20,000 cost recovery without relying on generative estimations.

---

## Overall Conclusions

1. **Targeted Validation Works**: FastMCP delivered deterministic constraint enforcement where LLMs struggle most (arithmetic totals and immutable anchor preservation under mid-trip replanning stress).
2. **Surfacing Real Trade-Offs**: The retained regression suite detects mixed
   effects, including a large Information Gathering regression for Gemini 3.1
   Pro and a small Remote Worker improvement for Gemini 3.5 Flash.
3. **Public evidence is the committed JSON**: Published tables in this
   repository must match `docs/evidence/canonical-results.json`. Raw itinerary
   traces remain local and are not required to reproduce the score tables.
