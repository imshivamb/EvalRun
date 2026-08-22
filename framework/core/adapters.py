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
    def run(self, scenario: Scenario, **kwargs) -> AgentOutput:
        """Executes the wrapped agent on a scenario and returns standardized AgentOutput."""
        pass


class PythonAgentAdapter(AgentAdapter):
    """Adapter wrapping any in-process Python agent object (e.g. TravelPlanningAgent)."""

    def __init__(self, agent: Any, agent_id: Optional[str] = None):
        self.agent = agent
        self.agent_id = agent_id or getattr(agent, "agent_name", agent.__class__.__name__)

    def run(self, scenario: Scenario, **kwargs) -> AgentOutput:
        """Invokes the underlying Python agent instance."""
        if hasattr(self.agent, "run"):
            result = self.agent.run(scenario.prompt, **kwargs)
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

    def run(self, scenario: Scenario, **kwargs) -> AgentOutput:
        payload = {
            "scenario_id": scenario.id,
            "prompt": scenario.prompt,
            "constraints": scenario.constraints,
        }
        resp = requests.post(self.endpoint_url, json=payload, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content") or data.get("output") or resp.text
        metadata = data.get("metadata", {})
        metadata["adapter"] = "HttpAgentAdapter"
        return AgentOutput(content=content, metadata=metadata)


class CliAgentAdapter(AgentAdapter):
    """Adapter wrapping a CLI command-line binary agent."""

    def __init__(self, command_args: list, timeout: float = 120.0):
        self.command_args = command_args
        self.timeout = timeout

    def run(self, scenario: Scenario, **kwargs) -> AgentOutput:
        proc = subprocess.run(
            self.command_args,
            input=scenario.prompt,
            text=True,
            capture_output=True,
            timeout=self.timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"CLI Agent command failed (code {proc.returncode}): {proc.stderr}")
        return AgentOutput(content=proc.stdout.strip(), metadata={"adapter": "CliAgentAdapter"})
