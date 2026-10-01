"""Optional observability integration for local and offline EvalRun usage."""

import os
from functools import wraps
from typing import Any, Callable, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])

try:
    from langfuse import observe as _langfuse_observe
except ImportError:
    _langfuse_observe = None


def langfuse_enabled() -> bool:
    """Langfuse tracing runs only when the package is installed and both keys are set."""
    return (
        _langfuse_observe is not None
        and bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
        and bool(os.getenv("LANGFUSE_SECRET_KEY"))
    )


def observe(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    """Use Langfuse when installed and configured, otherwise provide a no-op decorator."""
    if langfuse_enabled():
        return cast(Callable[[F], F], _langfuse_observe(*args, **kwargs))

    def decorator(function: F) -> F:
        @wraps(function)
        def wrapped(*function_args: Any, **function_kwargs: Any) -> Any:
            return function(*function_args, **function_kwargs)

        return cast(F, wrapped)

    return decorator
