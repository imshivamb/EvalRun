# Implementation Plan — Phase 8: External Technical Usability Validation

Validate the end-to-end usability and robustness of the `evalrun` toolkit across all 3 agent connection adapters (Python, HTTP, CLI), hosted & local model endpoints, custom evaluation profiles/plugins, and failure report workflows.

---

## 1. Usability & Connection Validation Matrix

| Connection Path | Adapter / Specifier | Protocol / Interface | Validation Target |
| :--- | :--- | :--- | :--- |
| **Python Agent** | `PythonAgentAdapter` / `module:Class` | Direct Python instantiation & `run(prompt)` method | `agents.travel:TravelPlanningAgent` & custom classes |
| **HTTP Agent** | `HttpAgentAdapter` / `http://localhost:8080/run` | HTTP POST JSON request (`{"prompt": "..."}`) $\rightarrow$ JSON response | Mock REST agent server endpoint |
| **CLI Agent** | `CliAgentAdapter` / `python my_agent.py --prompt` | Subprocess stdio stdin/stdout stream | Executable command wrapper |
| **Hosted Model** | `OpenAICompatibleLLM` | OpenAI-compatible cloud API (`api.openai.com`) | `gpt-4o` |
| **Local Model** | `OpenAICompatibleLLM` | User-managed local server (`localhost:8000/v1`) | `qwen2.5-72b-instruct` / `qwen2.5-smoke` |
| **Custom Scenario** | Markdown File (.md) | Benchmark parser & evaluator | Custom domain scenario |
| **Custom Profile & Plugin** | `register_profile` & `register_evaluator_plugin` | Profile weights & custom evaluation logic | Dynamic registry resolution |

---

## 2. Validation Test Suite (`tests/test_adapters.py` & `tests/test_usability_validation.py`)

Create comprehensive end-to-end validation tests for:
- Python, HTTP, and CLI agent adapters in `tests/test_adapters.py`.
- Dynamic CLI resolver support for HTTP (`http://...`) and CLI (`cli:...` or command string) agent specifiers.
- Complete execution of custom scenario + custom profile + custom evaluator plugin in a single run.
- Smoke test execution (`test_smoke_cli.py`).

---

## 3. Usability Findings & Remediation Report (`docs/phase8-usability-findings.md`)

Document setup experiences, error messages, and usability refinements:
- Error message clarity for missing ports/adapters.
- Automatic secret redaction verification.
- Report readability and jump-bar usability.

---

## 4. Verification Plan

- Run full workspace test suite:
  ```bash
  PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p "test_*.py"
  ```
- Run clean-checkout smoke test.
