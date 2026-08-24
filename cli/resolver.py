"""Dynamic Python agent resolver for evalrun CLI."""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Any
from framework.llms.base import BaseLLM


def resolve_agent(agent_spec: str, llm: BaseLLM) -> Any:
    """Dynamically imports and constructs an agent instance from an import specifier.

    Specifier format: 'package.module:ClassName' or 'package.module:factory_function'

    Args:
        agent_spec: Import specifier string (e.g. 'agents.travel:TravelPlanningAgent').
        llm: Target LLM client instance to inject into the agent constructor/factory.

    Returns:
        An instantiated agent object.

    Raises:
        ValueError: If the specifier is malformed, module cannot be imported, or symbol cannot be constructed.
    """
    # Terminals sometimes receive escaped underscores when a command is copied
    # from rendered Markdown (``custom\_agent``).  They are not meaningful in a
    # Python import path, so normalize them at the CLI boundary.
    agent_spec = agent_spec.replace("\\_", "_").strip()

    # A console-script entry point has the virtualenv's ``bin`` directory at
    # sys.path[0], not the user's working directory.  Add the current project
    # directory so ``evalrun --agent my_agent:Agent`` works without requiring
    # users to set PYTHONPATH manually.
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # 1. HTTP Endpoint Agent Resolution
    if agent_spec.startswith("http://") or agent_spec.startswith("https://"):
        from framework.core.adapters import HttpAgentAdapter
        return HttpAgentAdapter(endpoint_url=agent_spec)

    # 2. CLI Subprocess Command Agent Resolution
    if agent_spec.startswith("cli:"):
        from framework.core.adapters import CliAgentAdapter
        command = agent_spec[4:].strip()
        return CliAgentAdapter(command=command)

    if ":" not in agent_spec:
        raise ValueError(
            f"Invalid agent specification '{agent_spec}'. Expected format 'module:Class', 'http://...', or 'cli:command'."
        )

    module_path, symbol_name = agent_spec.split(":", 1)
    module_path = module_path.strip()
    symbol_name = symbol_name.strip()

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ValueError(f"Failed to import agent module '{module_path}': {e}") from e

    if not hasattr(module, symbol_name):
        raise ValueError(f"Module '{module_path}' has no attribute or class '{symbol_name}'.")

    symbol = getattr(module, symbol_name)

    if inspect.isclass(symbol):
        sig = inspect.signature(symbol.__init__)
        params = sig.parameters
        if "llm" in params:
            return symbol(llm=llm)
        elif len(params) <= 1:  # Only self
            return symbol()
        else:
            # Try passing llm as first positional argument
            try:
                return symbol(llm)
            except Exception as e:
                raise ValueError(
                    f"Could not instantiate agent class '{symbol_name}' with LLM parameter: {e}"
                ) from e
    elif callable(symbol):
        sig = inspect.signature(symbol)
        params = sig.parameters
        if "llm" in params:
            return symbol(llm=llm)
        elif len(params) == 0:
            return symbol()
        else:
            try:
                return symbol(llm)
            except Exception as e:
                raise ValueError(
                    f"Could not invoke agent factory '{symbol_name}' with LLM parameter: {e}"
                ) from e
    else:
        raise ValueError(f"Symbol '{symbol_name}' in module '{module_path}' is neither a class nor a callable factory.")
