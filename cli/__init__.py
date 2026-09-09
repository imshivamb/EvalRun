"""evalrun CLI package exports."""

from cli.main import create_parser
from cli.resolver import resolve_agent

__all__ = ["create_parser", "resolve_agent"]
