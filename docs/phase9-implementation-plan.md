# Implementation Plan — Phase 9: Guided Local UI (Non-Technical User Path)

Build a local-first, zero-server web interface (`evalrun ui`) for non-technical users to run evaluations, configure local/hosted model endpoints, select scenarios, view pass/fail/block/regression verdicts, and open detailed HTML reports without writing code or typing long CLI commands.

---

## 1. Non-Technical User Workflow

```text
+-----------------------------------------------------------------------+
|  evalrun Local Guided Interface                                      |
+-----------------------------------------------------------------------+
|  1. Configure Agent & Model Endpoint                                  |
|     Target Model: [ qwen2.5-72b-instruct                      ]       |
|     Base URL:     [ http://localhost:8000/v1                  ]       |
|     API Key:      [ ••••••••••••••••••••••••• (In-Memory Only)]       |
|     Agent:        [ agents.travel:TravelPlanningAgent         ]       |
|                                                                       |
|  2. Select Scenario & Baseline                                       |
|     Scenario:     [ evals/scenarios/travel-agent/.../budget.md ]       |
|     Baseline:     [ None / Select Baseline Run Folder         ]       |
|                                                                       |
|  [ 🚀 Run Benchmark Evaluation ]                                      |
|                                                                       |
|  3. Real-Time Results & Verdict                                      |
|     +-------------------------------------------------------------+   |
|     |  RELEASE APPROVED (Exit Code 0)                             |   |
|     |  Overall Score: 92.50 / 100 | Auditor: PASS                 |   |
|     +-------------------------------------------------------------+   |
|                                                                       |
|  [ 📄 Open Interactive HTML Report ]                                  |
+-----------------------------------------------------------------------+
```

---

## 2. Architecture & Components

1. **`cli/main.py`**:
   - Add `evalrun ui` command (`subparsers.add_parser("ui")`).
   - Launches local Python web server (`ui/server.py`).

2. **`ui/server.py`**:
   - Built with standard library `http.server` (or lightweight WSGI/HTTP server) to guarantee zero extra heavy dependencies.
   - Serves static assets (`ui/static/index.html`, `ui/static/style.css`, `ui/static/app.js`).
   - Handles REST endpoints:
     - `GET /api/scenarios`: Returns list of available `.md` benchmark scenarios.
     - `GET /api/baselines`: Returns list of previous run folders in `./eval_results` or `./results`.
     - `POST /api/run`: Invokes `framework.sdk.evaluate` & `compare`, returning structured verdict JSON.

3. **`ui/static/` (Modern Dark Glassmorphism Frontend)**:
   - Built with Vanilla HTML/CSS/JS (Google Font Inter, smooth CSS animations, dark mode glassmorphism theme `#0f172a`, responsive flex layout).
   - In-memory API key protection (never stored on disk).

---

## 3. Verification Plan

- Add unit test suite `tests/test_ui.py` testing API endpoints (`/api/scenarios`, `/api/baselines`, `/api/run`).
- Verify `evalrun ui` starts server cleanly.
- Run full workspace unit test suite.
