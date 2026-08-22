# Phase 4 — Local CLI (`evalrun`) Design & Experiment Specification

## Executive Summary

Phase 4 introduces the **`evalrun` Command-Line Interface (CLI)**. The CLI provides a provider-agnostic entry point for evaluating tool-using agents against benchmark scenarios and versioned evaluation suites. It supports cloud hosted APIs (OpenAI, NVIDIA NIM, Gemini) and local user-hosted endpoints (vLLM, Ollama, LM Studio for Qwen, Llama, DeepSeek).

---

## 1. First Slice CLI Syntax & Flags

```bash
evalrun run \
  --scenario evals/scenarios/travel-agent/budget-constrained-itinerary.md \
  --agent agents.travel:TravelPlanningAgent \
  --model qwen2.5-72b-instruct \
  --base-url http://localhost:8000/v1 \
  --judge-model gpt-4o \
  --judge-base-url https://api.openai.com/v1 \
  --output results/run-001
```

### Complete Command Line Interface:

| Category | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| **Input Selection** *(Mutually Exclusive)* | `--scenario` | Path to a single `.md` scenario file. | None |
| | `--suite` | Path to a directory containing `.md` scenarios. | None |
| **Agent Configuration** | `--agent` / `-a` | Python import path (`module:Class` or `module:factory`). | Required |
| **Target Model** | `--model` / `-m` | Target agent model identifier. | Required |
| | `--base-url` | OpenAI-compatible endpoint URL for target agent. | `https://api.openai.com/v1` |
| | `--api-key` | Target model API key credential. | `OPENAI_API_KEY` or `"EMPTY"` |
| **Judge Model** | `--judge-model` | Model used for LLM evaluators. | Target `--model` |
| | `--judge-base-url` | Base URL for judge LLM endpoint. | Target `--base-url` |
| | `--judge-api-key` | API key credential for judge LLM. | Target `--api-key` |
| **Verification & Output** | `--ground-truth` | Path to domain knowledge JSON for claim verification. | `ground_truth/japan_demo.json` |
| | `--output` / `-o` | Output directory path for reports and manifest. | `./eval_results` |

---

## 2. Dynamic Agent Resolver (`cli/resolver.py`)

Accepts import specifier format: `package.module:Symbol`.
- If `Symbol` is a class: instantiates `Symbol(llm=target_llm)`.
- If `Symbol` is a factory callable: invokes `Symbol(llm=target_llm)` or `Symbol()`.
- Raises clear error messages if module import fails or constructor signature is invalid.

---

## 3. Explicit CLI Exit Codes

| Exit Code | Condition |
| :---: | :--- |
| **`0`** | **All Passed**: All scenario evaluations completed successfully and passed evaluator & auditor gates. |
| **`1`** | **Evaluation Failed**: Evaluation completed, but one or more scenarios failed evaluator thresholds or were blocked by auditor. |
| **`2`** | **CLI / Runtime Error**: Invalid flags, scenario missing, import error, model connection failure, or unhandled exception. |

---

## 4. Credential Redaction in `manifest.json`

All output manifests redact secret credentials:
```json
{
  "run_id": "evalrun-20260822-104500",
  "target_model": {
    "model_name": "qwen2.5-72b-instruct",
    "base_url": "http://localhost:8000/v1",
    "api_key": "[REDACTED]"
  },
  "judge_model": {
    "model_name": "gpt-4o",
    "base_url": "https://api.openai.com/v1",
    "api_key": "[REDACTED]"
  }
}
```
