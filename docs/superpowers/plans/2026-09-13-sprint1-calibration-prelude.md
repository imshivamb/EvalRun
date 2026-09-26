# Sprint 1 Prelude Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the calibration schema, harvest unique retained outputs into `evals/calibration/`, and ship a blinded local labeling helper — no judge measurement yet.

**Architecture:** Pure functions in `framework/calibration/` own hashing, labels, harvest, and manifest I/O. CLI commands in `cli/calibration.py` stay thin. The label helper is a loopback-only stdlib HTTP server that never reads `meta.json`.

**Tech Stack:** Python 3.10+, stdlib `hashlib`/`json`/`http.server`, existing `evalrun` argparse, unittest.

## Global Constraints

- Do not call an LLM from harvest or the label helper.
- Do not implement `evalrun calibrate`, statistical regression, or confidence.
- Human scores must be integers in `{0, 5, ..., 100}`.
- Label helper must not display harvested judge scores.
- Work on branch `sprint1/calibration-prelude`, not `main`.
- Spec: `docs/superpowers/specs/2026-09-10-sprint1-judge-reliability-design.md`

---

### Task 1: Normalize, hash, case ids, label validation

**Files:**
- Create: `framework/calibration/__init__.py`
- Create: `framework/calibration/schema.py`
- Test: `tests/test_calibration_schema.py`

**Interfaces:**
- Produces: `normalize_output_text(text: str) -> str`, `content_sha256(text: str) -> str`, `make_case_id(scenario_id: str, source_tag: str, digest: str) -> str`, `TRAVEL_AND_SUPPORT_DIMENSIONS: tuple[str, ...]`, `validate_labels(payload: dict) -> list[str]`

- [ ] Write failing tests for whitespace collapsing, SHA-256 stability, invalid scores (73, 101, missing dim), valid step-5 scores
- [ ] Implement schema helpers
- [ ] Run `EVALRUN_SKIP_NETWORK_CHECKS=1 .venv/bin/python -m pytest tests/test_calibration_schema.py -q`

---

### Task 2: Harvest unique cases and write corpus

**Files:**
- Create: `framework/calibration/harvest.py`
- Create: `framework/calibration/store.py`
- Test: `tests/test_calibration_harvest.py`

**Interfaces:**
- Consumes: schema helpers from Task 1
- Produces: `harvest_records(results_root: Path, scenarios_root: Path) -> list[HarvestedRecord]`, `write_corpus(records, dest: Path) -> dict` (manifest)

- [ ] Write failing tests: two identical itineraries collapse; distinct texts both kept; manifest diversity buckets; `meta.json` includes judge score and `labels.json` is absent
- [ ] Implement harvest of `*_itinerary.md` + sibling `*_report.json`, plus MCP JSON `baseline`/`mcp` outputs
- [ ] Map `benchmark_id` to scenario markdown under `evals/scenarios/`
- [ ] Run harvest tests

---

### Task 3: CLI harvest + blinded label helper

**Files:**
- Create: `cli/calibration.py`
- Modify: `cli/main.py` (add `harvest-calibration` and `label-calibration` subcommands)
- Test: `tests/test_calibration_cli.py`

**Interfaces:**
- Consumes: store.write_corpus, validate_labels
- Produces: `evalrun harvest-calibration --results results --output evals/calibration`, `evalrun label-calibration --dir evals/calibration --port 8502`

- [ ] Failing tests: harvest CLI writes manifest; label HTTP GET for a case body does not contain `harvested_judge_overall` or overall scores from meta; POST rejects score 73; POST writes `labels.json`
- [ ] Implement commands; helper uses session token + localhost like `ui/server.py`
- [ ] Run CLI tests plus full `pytest -m "not network"`

---

### Task 4: Run harvest on this repo and document counts

**Files:**
- Create: `evals/calibration/README.md`
- Modify: harvested `evals/calibration/**` (outputs + meta + manifest; no labels)

- [ ] `evalrun harvest-calibration` against local `results/`
- [ ] Record unique count and per-bucket counts in README
- [ ] If unique < 40 or diversity floor missed, stop and report — do not fake Budget extras

---
