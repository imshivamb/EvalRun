"""Diagnostic doctor module for evalrun doctor command."""

import importlib
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple


def run_doctor_checks() -> Tuple[bool, List[str]]:
    """Runs system diagnostics for EvalRun environment.

    Returns:
        Tuple of (all_ok: bool, lines: List[str])
    """
    lines: List[str] = []
    all_ok = True

    lines.append("=====================================================================")
    lines.append("                     EVALRUN SYSTEM DOCTOR                           ")
    lines.append("=====================================================================")

    # 1. Python Version Check
    py_ver = sys.version.split()[0]
    py_ok = sys.version_info >= (3, 10)
    if not py_ok:
        all_ok = False
    lines.append(f"[{'PASS' if py_ok else 'FAIL'}] Python Version: {py_ver} (Requirement: >= 3.10)")

    # 2. EvalRun Version & Installation State
    try:
        from importlib.metadata import PackageNotFoundError, version
        pkg_version = version("evalrun")
        install_type = "Installed Package"
    except (PackageNotFoundError, ImportError):
        pkg_version = "unknown"
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        try:
            try:
                import tomllib
                with pyproject.open("rb") as f:
                    metadata = tomllib.load(f)
            except ModuleNotFoundError:
                import re
                metadata = {}
                match = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']', pyproject.read_text(encoding="utf-8"))
                if match:
                    metadata = {"project": {"version": match.group(1)}}
            pkg_version = str(metadata.get("project", {}).get("version", "unknown"))
        except Exception:
            pass
        install_type = "Local Source Checkout"

    lines.append(f"[PASS] EvalRun Version: {pkg_version} ({install_type})")

    # 3. Model API Key Environment Variables
    env_keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
        "NVIDIA_API_KEY": os.getenv("NVIDIA_API_KEY"),
    }
    set_keys = [k for k, v in env_keys.items() if v]
    if set_keys:
        lines.append(f"[PASS] Model API Keys Configured: {', '.join(set_keys)}")
    else:
        lines.append("[INFO] Model API Keys Configured: None (Offline demo works without keys)")

    # 4. Agent Importability
    try:
        mod = importlib.import_module("agents.travel")
        agent_cls = getattr(mod, "TravelPlanningAgent", None)
        agent_ok = agent_cls is not None
    except Exception:
        agent_ok = False

    if agent_ok:
        lines.append("[PASS] Built-in Agent Import: agents.travel:TravelPlanningAgent")
    else:
        lines.append("[WARN] Built-in Agent Import: agents.travel not found in python path")

    # 5. Endpoint Reachability (OpenAI API)
    openai_reach = False
    try:
        req = urllib.request.Request("https://api.openai.com/v1/models", headers={"User-Agent": "evalrun-doctor"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            openai_reach = resp.status in (200, 401)
    except urllib.error.HTTPError as e:
        openai_reach = e.code in (401, 403, 200)
    except Exception:
        openai_reach = False

    if openai_reach:
        lines.append("[PASS] Hosted Endpoint Reachability: https://api.openai.com/v1")
    else:
        lines.append("[INFO] Hosted Endpoint Reachability: https://api.openai.com/v1 (Offline or unreachable)")

    # 6. Local Model Server Availability
    local_reach = False
    for local_url in ["http://localhost:8000/v1/models", "http://localhost:11434/api/tags"]:
        try:
            req = urllib.request.Request(local_url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status in (200, 401, 403):
                    local_reach = True
                    break
        except urllib.error.HTTPError as e:
            if e.code in (200, 401, 403):
                local_reach = True
                break
        except Exception:
            pass

    if local_reach:
        lines.append("[PASS] Local Model Server: Active local LLM server detected")
    else:
        lines.append("[INFO] Local Model Server: No active local LLM server detected on 8000/11434")

    # 7. Write Access to Output Folder
    output_dir = Path("./eval_results")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        test_file = output_dir / ".doctor_temp"
        test_file.write_text("write_test", encoding="utf-8")
        test_file.unlink()
        write_ok = True
    except Exception:
        write_ok = False

    if not write_ok:
        all_ok = False
    lines.append(f"[{'PASS' if write_ok else 'FAIL'}] Output Directory Write Access: {output_dir.resolve()}")

    lines.append("=====================================================================")
    if all_ok:
        lines.append(" Doctor Verdict: SYSTEM READY FOR EVALUATION RUNS")
    else:
        lines.append(" Doctor Verdict: ISSUES DETECTED - PLEASE REVIEW WARNINGS ABOVE")
    lines.append("=====================================================================")

    return all_ok, lines
