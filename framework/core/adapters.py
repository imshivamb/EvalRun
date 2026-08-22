"""Agent adapters for wrapping internal Python agents, HTTP endpoints, or CLI binaries."""

import json
import subprocess
import requests
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from framework.core.contracts import Scenario
from framework.models import AgentOutput


class AgentAdapter(ABC):
    """Abstract adapter interface decoupling agent evaluation from specific implementations."""

    @abstractmethod
    def run(self, scenario: Any, **kwargs) -> AgentOutput:
        """Executes the wrapped agent on a scenario or prompt string and returns standardized AgentOutput."""
        pass


class PythonAgentAdapter(AgentAdapter):
    """Adapter wrapping any in-process Python agent object (e.g. TravelPlanningAgent)."""

    def __init__(self, agent: Any, agent_id: Optional[str] = None):
        self.agent = agent
        self.agent_id = agent_id or getattr(agent, "agent_name", agent.__class__.__name__)

    def run(self, scenario: Any, **kwargs) -> AgentOutput:
        """Invokes the underlying Python agent instance."""
        prompt_text = scenario if isinstance(scenario, str) else getattr(scenario, "prompt", str(scenario))
        if hasattr(self.agent, "run"):
            result = self.agent.run(prompt_text, **kwargs)
            if isinstance(result, AgentOutput):
                return result
            elif isinstance(result, str):
                return AgentOutput(content=result, metadata={"adapter": "PythonAgentAdapter"})
            else:
                return AgentOutput(content=str(result), metadata={"adapter": "PythonAgentAdapter"})
        else:
            raise AttributeError(f"Wrapped agent object {self.agent} has no 'run' method.")


class HttpAgentAdapter(AgentAdapter):
    """Adapter wrapping an external HTTP/REST API agent endpoint."""

    def __init__(self, endpoint_url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 120.0):
        self.endpoint_url = endpoint_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout

    def run(self, scenario: Any, **kwargs) -> AgentOutput:
        if isinstance(scenario, str):
            prompt_text = scenario
            scenario_id = "scenario-001"
            constraints = {}
        else:
            prompt_text = getattr(scenario, "prompt", str(scenario))
            scenario_id = getattr(scenario, "id", "scenario-001")
            constraints = getattr(scenario, "constraints", {})

        payload = {
            "scenario_id": scenario_id,
            "prompt": prompt_text,
            "constraints": constraints,
        }
        try:
            resp = requests.post(self.endpoint_url, json=payload, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"HTTP Agent endpoint timed out after {self.timeout}s: {e}") from e

        data = resp.json()
        content = data.get("content") or data.get("output") or resp.text
        metadata = data.get("metadata", {})
        metadata["adapter"] = "HttpAgentAdapter"
        return AgentOutput(content=content, metadata=metadata)


class CliAgentAdapter(AgentAdapter):
    """Adapter wrapping a CLI command-line binary agent."""

    def __init__(self, command: Any, timeout: float = 120.0):
        if isinstance(command, str):
            import shlex
            self.command_args = shlex.split(command)
        else:
            self.command_args = command
        self.timeout = timeout

    def run(self, scenario: Any, **kwargs) -> AgentOutput:
        prompt_text = scenario if isinstance(scenario, str) else getattr(scenario, "prompt", str(scenario))
        try:
            proc = subprocess.run(
                self.command_args,
                input=prompt_text,
                text=True,
                capture_output=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"CLI Agent command timed out after {self.timeout}s: {e}") from e

        if proc.returncode != 0:
            raise RuntimeError(f"CLI Agent command failed (code {proc.returncode}): {proc.stderr}")

        stdout_text = proc.stdout.strip()
        try:
            parsed = json.loads(stdout_text)
            if isinstance(parsed, dict) and "content" in parsed:
                content = parsed["content"]
                metadata = parsed.get("metadata", {})
                metadata["adapter"] = "CliAgentAdapter"
                return AgentOutput(content=content, metadata=metadata)
        except Exception:
            pass

        return AgentOutput(content=stdout_text, metadata={"adapter": "CliAgentAdapter"})
