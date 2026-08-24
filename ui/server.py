"""Local-first guided web interface server for non-technical users."""

import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List

STATIC_DIR = Path(__file__).parent / "static"


def list_available_scenarios(base_dir: str = "evals/scenarios") -> List[Dict[str, str]]:
    """Scans base_dir for benchmark scenario (.md) files."""
    scenarios = []
    p = Path(base_dir)
    if p.exists() and p.is_dir():
        for file_path in p.glob("**/*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read(500)
                name = file_path.stem.replace("-", " ").title()
                for line in content.splitlines():
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                        break
                    elif line.startswith("# Benchmark Scenario:"):
                        name = line.split(":", 1)[1].strip()
                        break
                scenarios.append({
                    "id": file_path.stem,
                    "name": name,
                    "path": str(file_path),
                })
            except Exception:
                scenarios.append({
                    "id": file_path.stem,
                    "name": file_path.stem,
                    "path": str(file_path),
                })
    return sorted(scenarios, key=lambda x: x["name"])


def list_available_baselines(search_dirs: List[str] = None) -> List[Dict[str, str]]:
    """Scans output directories for valid baseline run folders containing manifest.json."""
    if search_dirs is None:
        search_dirs = ["eval_results", "results"]
    baselines = []
    for d in search_dirs:
        p = Path(d)
        if p.exists() and p.is_dir():
            for manifest_file in p.glob("**/manifest.json"):
                run_dir = manifest_file.parent
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    run_id = data.get("run_id", run_dir.name)
                    timestamp = data.get("timestamp_utc", "")
                    baselines.append({
                        "run_id": run_id,
                        "timestamp": timestamp,
                        "path": str(run_dir),
                    })
                except Exception:
                    pass
    return sorted(baselines, key=lambda x: x.get("timestamp", ""), reverse=True)


class UIRequestHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler serving static frontend files and API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        # The UI is a local development surface; always serve the latest
        # source files after a restart instead of allowing stale browser cache.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json_response(self, code: int, data: Dict[str, Any]):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/scenarios":
            scenarios = list_available_scenarios()
            self.send_json_response(200, {"scenarios": scenarios})
            return
        elif path == "/api/baselines":
            baselines = list_available_baselines()
            self.send_json_response(200, {"baselines": baselines})
            return
        elif path.startswith("/eval_results/") or path.startswith("/results/"):
            # Enforce strict path traversal protection: ensure file remains within workspace root
            try:
                requested_path = (Path.cwd() / path.lstrip("/")).resolve()
                workspace_root = Path.cwd().resolve()
                if not requested_path.is_relative_to(workspace_root):
                    self.send_json_response(403, {"error": "Access denied: Path traversal outside workspace is forbidden."})
                    return

                if requested_path.exists() and requested_path.is_file():
                    content_type = "text/html" if requested_path.suffix == ".html" else "application/json"
                    with open(requested_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                else:
                    self.send_json_response(404, {"error": "File not found."})
                    return
            except Exception as e:
                self.send_json_response(500, {"error": str(e)})
                return

        # Serve static UI files
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/run":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body)
            except Exception as e:
                self.send_json_response(400, {"error": f"Invalid JSON payload: {e}"})
                return

            scenario = payload.get("scenario")
            agent = payload.get("agent", "agents.travel:TravelPlanningAgent")
            model = payload.get("model", "qwen2.5-72b-instruct")
            base_url = payload.get("base_url", "https://api.openai.com/v1")
            api_key = payload.get("api_key")
            judge_model = payload.get("judge_model")
            baseline = payload.get("baseline")
            output_dir = payload.get("output_dir")
            if not output_dir:
                run_stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                output_dir = f"./eval_results/ui-run-{run_stamp}"

            if not scenario:
                self.send_json_response(400, {"error": "Missing required field 'scenario'."})
                return

            # UI users may provide a custom scenario path, but it must remain
            # inside the local workspace. Never allow the UI to read arbitrary
            # files from the host machine.
            try:
                workspace_root = Path.cwd().resolve()
                scenario_path = (workspace_root / str(scenario)).resolve()
                if not scenario_path.is_relative_to(workspace_root):
                    self.send_json_response(
                        403,
                        {"error": "Scenario path must remain inside the EvalRun workspace."},
                    )
                    return
                if not scenario_path.exists():
                    self.send_json_response(400, {"error": f"Scenario path does not exist: {scenario}"})
                    return
            except Exception as e:
                self.send_json_response(400, {"error": f"Invalid scenario path: {e}"})
                return

            try:
                from framework.sdk import evaluate, compare

                # Execute evaluation programmatically via SDK
                results = evaluate(
                    scenario=scenario,
                    agent=agent,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    judge_model=judge_model,
                    output_dir=output_dir,
                )

                regression_report_dict = None
                release_blocked = False
                if baseline:
                    reg_report = compare(
                        candidate_results=results,
                        baseline=baseline,
                    )
                    regression_report_dict = reg_report.to_dict()
                    release_blocked = reg_report.release_blocked

                scenarios_data = []
                for r in results:
                    gate = getattr(r, "agent_metadata", {}).get("audit_gate_decision", "PASS")
                    if gate == "BLOCK":
                        release_blocked = True
                    scenarios_data.append({
                        "benchmark_id": r.benchmark_id,
                        "name": r.benchmark_name,
                        "overall_score": r.overall_score,
                        "passed": r.passed,
                        "auditor_gate": gate,
                        "dimension_scores": [
                            {"dimension": ds.dimension, "score": ds.score, "reason": ds.reason}
                            for ds in r.dimension_scores
                        ],
                    })

                try:
                    html_report_rel = f"/{Path(output_dir).relative_to(Path.cwd())}/report.html"
                except Exception:
                    html_report_rel = f"/{output_dir}/report.html"

                response_payload = {
                    "status": "success",
                    "total_scenarios": len(results),
                    "all_passed": all(r.passed for r in results),
                    "release_blocked": release_blocked,
                    "html_report_path": html_report_rel,
                    "scenarios": scenarios_data,
                    "regression": regression_report_dict,
                }
                self.send_json_response(200, response_payload)
            except Exception as e:
                self.send_json_response(500, {"error": f"Evaluation execution failed: {e}"})
            return

        self.send_json_response(404, {"error": "Endpoint not found."})


def run_ui_server(host: str = "127.0.0.1", port: int = 8501) -> HTTPServer:
    """Starts the local UI web server on the specified host and port."""
    server = HTTPServer((host, port), UIRequestHandler)
    print(f"=====================================================================")
    print(f"   EVALRUN GUIDED LOCAL UI SERVER STARTED")
    print(f"   URL: http://{host}:{port}")
    if host not in ("127.0.0.1", "localhost"):
        print(f"   SECURITY WARNING: Bound to non-localhost address '{host}'.")
        print(f"   Ensure plain HTTP port is protected behind a secure network firewall.")
    print(f"=====================================================================")
    return server
