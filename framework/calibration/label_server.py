"""Loopback labeling helper that never reads meta.json."""

import html
import json
import secrets
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from framework.calibration.schema import (
    ALLOWED_SCALE,
    DECISION_CHOICES,
    LABEL_SCHEMA_VERSION,
    TRAVEL_AND_SUPPORT_DIMENSIONS,
    validate_labels,
)

LABEL_TOKEN_HEADER = "X-EvalRun-UI-Token"
MIN_UNIQUE_CASES = 40


class CorpusIncompleteError(RuntimeError):
    """Raised when the unlabeled corpus does not meet the published gate."""


def run_label_server(
    corpus_dir: Path,
    host: str = "127.0.0.1",
    port: int = 8502,
    allow_incomplete_corpus: bool = False,
) -> HTTPServer:
    """Start a localhost labeling server; caller owns serve_forever()."""
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Label helper must bind to localhost.")
    corpus_dir = Path(corpus_dir).resolve()
    manifest_path = corpus_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json in {corpus_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    unique_count = int(manifest.get("unique_count") or 0)
    diversity_ok = bool(manifest.get("diversity_floor_met"))
    if not allow_incomplete_corpus and (unique_count < MIN_UNIQUE_CASES or not diversity_ok):
        raise CorpusIncompleteError(
            "Calibration corpus is incomplete: need unique_count >= 40 and "
            "all diversity buckets. Pass --allow-incomplete-corpus only for debugging."
        )
    token = secrets.token_urlsafe(32)
    handler = _build_handler(corpus_dir, token)
    server = HTTPServer((host, port), handler)
    bound_host, bound_port = server.server_address
    print("=====================================================================")
    print("   EVALRUN CALIBRATION LABEL HELPER")
    print(f"   URL: http://{bound_host}:{bound_port}")
    print("   This page never shows harvested judge scores and never calls an LLM.")
    print("=====================================================================")
    return server


def _build_handler(corpus_dir: Path, token: str):
    class LabelRequestHandler(BaseHTTPRequestHandler):
        calibration_dir = corpus_dir
        session_token = token

        def log_message(self, format: str, *args: Any) -> None:
            return

        def send_json(self, code: int, data: Dict[str, Any]) -> None:
            body = json.dumps(data).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_html(self, code: int, body: str) -> None:
            payload = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _is_local(self) -> bool:
            host = self.headers.get("Host", "").split(":", 1)[0]
            origin = self.headers.get("Origin")
            origin_host = urllib.parse.urlparse(origin).hostname if origin else None
            return host in {"127.0.0.1", "localhost"} and (
                origin_host is None or origin_host in {"127.0.0.1", "localhost"}
            )

        def do_GET(self) -> None:
            if not self._is_local():
                self.send_json(403, {"error": "Label helper requests must originate from localhost."})
                return
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path == "/api/session":
                self.send_json(200, {"token": self.session_token})
                return
            if path == "/api/status":
                self.send_json(200, _status_payload(self.calibration_dir))
                return
            if path == "/api/next":
                case_id = _next_unlabeled_case_id(self.calibration_dir)
                if case_id is None:
                    self.send_json(200, {"done": True, **_ready_signal(self.calibration_dir)})
                    return
                try:
                    self.send_json(200, _case_payload(self.calibration_dir, case_id))
                except FileNotFoundError:
                    self.send_json(404, {"error": "Case not found."})
                return
            if path.startswith("/api/case/"):
                case_id = urllib.parse.unquote(path[len("/api/case/") :])
                try:
                    self.send_json(200, _case_payload(self.calibration_dir, case_id))
                except ValueError:
                    self.send_json(400, {"error": "Invalid case id."})
                except FileNotFoundError:
                    self.send_json(404, {"error": "Case not found."})
                return
            if path in {"/", "/index.html"}:
                self.send_html(200, _page_html())
                return
            self.send_json(404, {"error": "Endpoint not found."})

        def do_POST(self) -> None:
            if not self._is_local():
                self.send_json(403, {"error": "Label helper requests must originate from localhost."})
                return
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/api/label":
                self.send_json(404, {"error": "Endpoint not found."})
                return
            if self.headers.get(LABEL_TOKEN_HEADER) != self.session_token:
                self.send_json(403, {"error": "Missing or invalid session token."})
                return
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                self.send_json(400, {"error": f"Invalid JSON payload: {exc}"})
                return
            try:
                saved = _save_labels(self.calibration_dir, payload)
            except FileNotFoundError:
                self.send_json(404, {"error": "Case not found."})
                return
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
                return
            self.send_json(200, {"status": "saved", "case_id": saved["case_id"]})

    return LabelRequestHandler


def _case_dir(corpus_dir: Path, case_id: str) -> Path:
    if not case_id or case_id != Path(case_id).name or ".." in case_id:
        raise ValueError("invalid case id")
    resolved_root = corpus_dir.resolve()
    case_dir = (resolved_root / "cases" / case_id).resolve()
    if resolved_root not in case_dir.parents:
        raise ValueError("invalid case id")
    if not case_dir.is_dir():
        raise FileNotFoundError(case_id)
    return case_dir


def _case_payload(corpus_dir: Path, case_id: str) -> Dict[str, Any]:
    case_dir = _case_dir(corpus_dir, case_id)
    scenario = (case_dir / "scenario.md").read_text(encoding="utf-8")
    output = (case_dir / "output.md").read_text(encoding="utf-8")
    return {
        "case_id": case_id,
        "scenario": scenario,
        "output": output,
        "dimensions": list(TRAVEL_AND_SUPPORT_DIMENSIONS),
        "labeled": (case_dir / "labels.json").exists(),
    }


def _next_unlabeled_case_id(corpus_dir: Path) -> Optional[str]:
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    for case in manifest.get("cases") or []:
        case_id = case.get("case_id")
        if not case_id:
            continue
        if not (corpus_dir / "cases" / case_id / "labels.json").exists():
            return case_id
    return None


def _status_payload(corpus_dir: Path) -> Dict[str, Any]:
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    remaining = 0
    for case in manifest.get("cases") or []:
        case_id = case.get("case_id")
        if case_id and not (corpus_dir / "cases" / case_id / "labels.json").exists():
            remaining += 1
    return {
        "unique_count": manifest.get("unique_count"),
        "diversity_counts": manifest.get("diversity_counts"),
        "diversity_floor_met": manifest.get("diversity_floor_met"),
        "remaining": remaining,
    }


def _ready_signal(corpus_dir: Path) -> Dict[str, Any]:
    status = _status_payload(corpus_dir)
    return {
        "unique_count": status["unique_count"],
        "diversity_counts": status["diversity_counts"],
        "rater_id": "shivam",
    }


def _save_labels(corpus_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    case_id = str(payload.get("case_id") or "")
    labels = {
        "case_id": case_id,
        "rater_id": payload.get("rater_id") or "shivam",
        "schema_version": payload.get("schema_version"),
        "scale": payload.get("scale") or ALLOWED_SCALE,
        "labeled_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scores": payload.get("scores") or {},
        "decisions": payload.get("decisions") or {},
        "notes": payload.get("notes") or {},
    }
    errors = validate_labels(labels)
    if errors:
        raise ValueError("; ".join(errors))
    case_dir = _case_dir(corpus_dir, case_id)
    (case_dir / "labels.json").write_text(
        json.dumps(labels, indent=2) + "\n", encoding="utf-8"
    )
    _mark_labels_complete(corpus_dir, case_id)
    return labels


def _mark_labels_complete(corpus_dir: Path, case_id: str) -> None:
    manifest_path = corpus_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for case in manifest.get("cases") or []:
        if case.get("case_id") == case_id:
            case["labels_complete"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _page_html() -> str:
    dimension_fields = "".join(
        f'<label>{html.escape(name)}<select class="score" name="{html.escape(name)}"></select></label>'
        for name in TRAVEL_AND_SUPPORT_DIMENSIONS
    )
    decision_fields = "".join(
        f'<label>{html.escape(name)}<select class="decision" name="{html.escape(name)}">'
        '<option value="">—</option>'
        + "".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in choices)
        + "</select></label>"
        for name, choices in DECISION_CHOICES.items()
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>EvalRun calibration labels</title>
  <style>
    body {{ font-family: sans-serif; max-width: 960px; margin: 1.5rem auto; }}
    pre {{ white-space: pre-wrap; background: #f6f6f6; padding: 1rem; }}
    form {{ display: grid; gap: 0.6rem; margin-top: 1rem; }}
    button {{ width: fit-content; padding: 0.4rem 0.8rem; }}
  </style>
</head>
<body>
  <h1>Calibration labels</h1>
  <p>Score only the scenario and output. Harvested judge scores are not shown.</p>
  <p id="status"></p>
  <section>
    <h2>Scenario</h2>
    <pre id="scenario"></pre>
    <h2>Agent output</h2>
    <pre id="output"></pre>
  </section>
  <form id="label-form">
    <h2>Scores</h2>
    {dimension_fields}
    <h2>Decisions</h2>
    {decision_fields}
    <button type="submit">Save labels</button>
  </form>
  <script>
    const steps = Array.from({{length: 21}}, (_, i) => i * 5);
    let token = "";
    let caseId = "";
    async function boot() {{
      const session = await fetch("/api/session").then(r => r.json());
      token = session.token;
      document.querySelectorAll("select.score").forEach(select => {{
        select.innerHTML = `<option value="">—</option>` +
          steps.map(v => `<option value="${{v}}">${{v}}</option>`).join("");
      }});
      await loadNext();
    }}
    async function loadNext() {{
      const data = await fetch("/api/next").then(r => r.json());
      if (data.done) {{
        document.getElementById("status").textContent =
          `Ready. unique=${{data.unique_count}} rater_id=${{data.rater_id}} buckets=${{JSON.stringify(data.diversity_counts)}}`;
        document.getElementById("scenario").textContent = "";
        document.getElementById("output").textContent = "";
        document.getElementById("label-form").style.display = "none";
        return;
      }}
      caseId = data.case_id;
      document.getElementById("status").textContent = "Case " + caseId;
      document.getElementById("scenario").textContent = data.scenario;
      document.getElementById("output").textContent = data.output;
      document.getElementById("label-form").reset();
    }}
    document.getElementById("label-form").addEventListener("submit", async (event) => {{
      event.preventDefault();
      const scores = {{}};
      document.querySelectorAll("select.score").forEach(select => {{
        scores[select.name] = select.value === "" ? null : Number(select.value);
      }});
      const decisions = {{}};
      document.querySelectorAll("select.decision").forEach(select => {{
        decisions[select.name] = select.value || null;
      }});
      const resp = await fetch("/api/label", {{
        method: "POST",
        headers: {{
          "Content-Type": "application/json",
          "{LABEL_TOKEN_HEADER}": token
        }},
        body: JSON.stringify({{
          case_id: caseId,
          rater_id: "shivam",
          schema_version: {LABEL_SCHEMA_VERSION},
          scale: "0-100-step-5",
          scores,
          decisions
        }})
      }});
      if (!resp.ok) {{
        const err = await resp.json();
        alert(err.error || "Save failed");
        return;
      }}
      await loadNext();
    }});
    boot();
  </script>
</body>
</html>
"""
