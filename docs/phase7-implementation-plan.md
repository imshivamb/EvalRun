# Implementation Plan — Phase 7: Technical CLI/SDK Product Completion

Complete the developer-facing product surface of `evalrun`, providing a stable Python SDK API, custom profile/evaluator plugin loading, YAML/TOML/JSON configuration file support, end-to-end example templates, and a LangSmith capability comparison document.

---

## 1. Public Python SDK API (`framework/sdk.py` & `framework/__init__.py`)

Expose a clean programmatic Python API for developers embedding `evalrun` into custom test pipelines or notebooks:

```python
from framework import evaluate, compare, load_suite

# 1. Evaluate single scenario or suite programmatically
results = evaluate(
    scenario="evals/scenarios/travel-agent/budget-constrained-itinerary.md",
    agent="agents.travel:TravelPlanningAgent",
    model="qwen2.5-72b-instruct",
    base_url="http://localhost:8000/v1",
    judge_model="gpt-4o",
    output_dir="./eval_results",
)

# 2. Compare against baseline programmatically
report = compare(
    candidate_results=results,
    baseline="baselines/travel-v1",
    max_regression=5.0,
)

print(f"Release Blocked: {report.release_blocked}")
```

---

## 2. Configuration File Workflow (`evalrun --config evalrun.json` or `evalrun.toml`)

Allow developers to define evaluation runs in configuration files instead of typing long CLI flags:

```json
{
  "scenario": "evals/scenarios/travel-agent/budget-constrained-itinerary.md",
  "agent": "agents.travel:TravelPlanningAgent",
  "model": "qwen2.5-72b-instruct",
  "base_url": "http://localhost:8000/v1",
  "judge_model": "gpt-4o",
  "baseline": "baselines/travel-v1",
  "max_regression": 5.0,
  "output": "./results/config-run"
}
```

CLI Usage:
```bash
evalrun run --config evalrun.json
```

---

## 3. Dynamic Custom Profiles & Evaluator Plugin Loader (`framework/profiles/registry.py`)

Allow users to define custom evaluation profiles and plugin functions without editing internal framework source code:

- `register_profile(name: str, profile: EvaluationProfile)`
- `load_profile_from_file(filepath: str) -> EvaluationProfile`
- Support `--profile path/to/custom_profile.json` or `--profile custom_profile_name` in CLI.

---

## 4. Templates, Examples & LangSmith Comparison Document

- **Templates**: Create `templates/scenario_template.md` and `templates/suite_template.json`.
- **Examples**: Add working scripts in `examples/` (`examples/sdk_usage.py`, `examples/custom_profile_demo.py`, `examples/config_workflow.json`).
- **LangSmith Comparison Document**: Create `docs/langsmith-comparison.md` evaluating `evalrun` vs LangSmith (local-first, zero server, independent auditor gate, offline privacy vs hosted SaaS platform).

---

## 5. Verification Plan

- Add unit tests in `tests/test_sdk.py`, `tests/test_config_workflow.py`, and `tests/test_custom_profiles.py`.
- Verify full test suite passes.
