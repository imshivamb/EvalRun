"""Optional observability integration for local and offline EvalRun usage."""

from functools import wraps
from typing import Any, Callable, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])

try:
    from langfuse import observe as _langfuse_observe
except ImportError:
    _langfuse_observe = None


def observe(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    """Use Langfuse when installed, otherwise provide a no-op decorator."""
    if _langfuse_observe is not None:
        return cast(Callable[[F], F], _langfuse_observe(*args, **kwargs))

    def decorator(function: F) -> F:
        @wraps(function)
        def wrapped(*function_args: Any, **function_kwargs: Any) -> Any:
            return function(*function_args, **function_kwargs)

        return cast(F, wrapped)

    return decorator
