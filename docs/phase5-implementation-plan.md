# Implementation Plan — Phase 5: Baseline Comparison & Regression Release Gates

Implement automated baseline manifest/report loading, stable `scenario_id` matching, per-scenario and per-dimension score deltas ($\Delta \text{score}$), non-short-circuiting 3-tier release gates, machine-readable `regression_report.json` artifacts, and enhanced HTML review reports.

---

## Task 1 (Bounded First Task): Baseline Loader & Comparator (`framework/regression/`)

### 1. `framework/regression/loader.py`
- Implements `load_baseline_manifest(path: str) -> Dict[str, Any]`
  - Supports loading from a directory containing `manifest.json` or a single `manifest.json` path.
  - Parses `manifest.json` and loads referenced per-scenario `*_report.json` files if present.
  - Extracts per-scenario overall scores, dimension scores, and auditor decisions indexed by `scenario_id`.

### 2. `framework/regression/comparator.py`
- Data contracts: `DimensionDelta`, `ScenarioComparison`, `RegressionReport`.
- Implements `compare_runs(candidate_results: List[EvaluationResult], baseline_data: Dict[str, Any], max_overall_drop: float = 5.0, max_dim_drop: float = 10.0) -> RegressionReport`
  - Matches candidate results to baseline entries strictly by `scenario_id`.
  - Calculates $\Delta \text{score} = \text{candidate\_score} - \text{baseline\_score}$.
  - Flags regressions when $\Delta \text{score} < -\text{max\_overall\_drop}$ or $\Delta \text{dimension\_score} < -\text{max\_dim\_drop}$.
  - Handles missing scenarios (`MISSING_IN_CANDIDATE` triggers release `BLOCK`, `NEW` scenarios reported safely).
  - Evaluates ALL 3 GATES (Evaluator, Auditor, Regression) for complete diagnosis.

### 3. Unit Tests (`tests/test_regression.py`)
- Test baseline loading from manifest directory and single file.
- Test score delta calculations and threshold boundary conditions.
- Test per-dimension delta calculations.
- Test missing scenario handling (`MISSING_IN_CANDIDATE` vs `NEW`).
- Test non-short-circuit gate reporting.

---

## Task 2: Raw Output Embedding & Artifact Fingerprints

### 1. `framework/models.py` & `framework/evaluation/runner.py`
- Include `raw_output_content` and `raw_output_path` in `EvaluationResult` / `agent_metadata`.
- Compute content hash (SHA256) for scenarios and record Git commit hash in `manifest.json`.

---

## Task 3: CLI Integration & HTML Report Enhancement

### 1. `cli/main.py` & `cli/formatter.py`
- Add `--baseline`, `--max-regression` (default 5.0), `--max-dimension-regression` (default 10.0).
- Integrate `load_baseline_manifest` and `compare_runs`.
- Write `regression_report.json`.
- Enforce exit code `1` when evaluator fails, auditor blocks, or regression delta exceeds threshold.
- Display deltas in terminal ASCII summary table.

### 2. `cli/html_reporter.py`
- Upgrade `report.html` with:
  - Failures-first top-level verdict banner (`RELEASE BLOCKED`).
  - Search, filter (All / Passed / Failed / Blocked / Regressed), and sort controls.
  - Collapsible scenario cards with embedded raw model output text.
  - Visual score progress bars and highlighted lowest-scoring dimension.
  - Baseline comparison deltas table.
