"""Async client for the local travel-validation MCP server."""

import os
import sys
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class TravelValidationMCPClient:
    """Connects to the local travel constraint server over stdio.

    The client creates a short-lived session per request. This is appropriate for
    the current local validation workflow and keeps the agent integration
    explicit; long-lived connection management is unnecessary until deployment.
    """

    def __init__(self, python_executable: Optional[str] = None):
        self.python_executable = python_executable or sys.executable

    def _server_parameters(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=self.python_executable,
            args=["-m", "framework.mcp.server"],
            env=dict(os.environ),
        )

    async def list_tools(self) -> List[str]:
        """Returns the names of tools exposed by the validation server."""
        async with stdio_client(self._server_parameters()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return [tool.name for tool in result.tools]

    async def call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calls a tool and returns its structured JSON response.

        Raises:
            RuntimeError: If the MCP server reports an error or returns an
                unexpected non-dictionary payload.
        """
        async with stdio_client(self._server_parameters()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)

        if result.isError:
            raise RuntimeError(f"MCP tool '{name}' failed: {result.content}")
        if not isinstance(result.structuredContent, dict):
            raise RuntimeError(
                f"MCP tool '{name}' returned an unexpected payload: {result.content}"
            )
        payload = dict(result.structuredContent)
        # FastMCP wraps plain dictionary tool returns under ``result``. Keep the
        # application-facing client independent from that transport detail.
        if set(payload) == {"result"} and isinstance(payload["result"], dict):
            return dict(payload["result"])
        return payload
