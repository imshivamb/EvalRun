"""MCP integrations for deterministic agent validation tools."""

from framework.mcp.constraints import (
    calculate_savings,
    get_locked_constraints,
    validate_revision,
)
from framework.mcp.client import TravelValidationMCPClient

__all__ = [
    "calculate_savings",
    "get_locked_constraints",
    "validate_revision",
    "TravelValidationMCPClient",
]
"""MCP-backed deterministic validation components."""

from .revision_summary import RevisionSummary, parse_revision_summary

__all__ = ["RevisionSummary", "parse_revision_summary"]
