"""Dynamic Python agent resolver for evalrun CLI."""

import importlib
import inspect
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
    if ":" not in agent_spec:
        raise ValueError(
            f"Invalid agent specification '{agent_spec}'. Expected format 'module:Class' or 'module:factory' "
            "(e.g., 'agents.travel:TravelPlanningAgent')."
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
