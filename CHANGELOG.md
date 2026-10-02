# Changelog

## Unreleased

- Replaced the old `agent-eval-platform` clone URL and local `file://` links in
  the README with the `EvalRun` repository.
- Added project URLs to the package metadata.
- Added `--trials N` to `evalrun run` and `trials=` to the SDK: each scenario
  reports pass rate with a 95% Wilson interval, mean score with a 95% t
  interval, and latency p50/p95, in the terminal, HTML report and manifest.
- Added `--regression-mode statistical` to `evalrun run` and
  `regression_mode=` to the SDK's `compare()`: a scenario or dimension
  regresses only when the 95% Welch interval of the change against the
  baseline's trials excludes zero and the drop exceeds the allowed drop. It
  refuses runs with fewer than 2 trials per side. Simple mode stays the default.
- Added `evalrun power`: from a baseline's measured score noise, the trials per
  side needed to catch a given drop 80% of the time under the statistical
  gate, and the smallest drop the baseline's trial count can catch.
- Run statistics now keep every trial's overall and per-dimension scores.
- `evalrun demo` now replays a real recorded run (Gemini 3.7 Flash, 3 trials)
  instead of showing a hardcoded score and invented justifications. The
  recording ships with its provenance in `cli/demo_data/recorded_run.json` and
  is rebuilt with `scripts/build_demo_recording.py`.
- Langfuse tracing now stays off unless both Langfuse keys are configured,
  instead of printing authentication errors on every call.
- Planned next: statistics core, judge calibration, trace import, and
  deterministic checks for EvalRun 1.0.

## [0.4.2] - 2026-10-01

- Added Sprint 0 credibility and safety hardening.
- Added GitHub Actions CI, offline-safe diagnostics, and clean wheel checks.
- Reconciled published benchmark narratives with canonical evidence artifacts.
- Secured the local UI with built-in agent allowlisting, session tokens, and
  workspace-scoped paths.
- Added judge score bounds, deterministic sampling defaults, optional Langfuse
  and MCP integrations, and missing package metadata dependencies.
- Corrected the auditor documentation to disclose 0% specificity in the
  synthetic sensitivity suite.
- Published secret-free MCP replanning and v3 auditor scores in
  `docs/evidence/canonical-results.json`, and removed unbacked Llama/GPT
  five-scenario claims.
- Added a clean wheel-install CI job and marked doctor network probes so CI
  skips live endpoint checks.
- Added the missing `markdown-it-py` package dependency required by clean
  wheel installs.
- Corrected the copyright holder name in `LICENSE`.

## [0.4.1] - 2026-08-25

- Published the local-first `evalrun` package to PyPI.
- Added the guided local UI, scenario validation, environment diagnostics,
  custom profiles, evaluator plugins, and SDK workflows.
- Added baseline regression comparison and standalone HTML reports.
