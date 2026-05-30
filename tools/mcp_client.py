from __future__ import annotations

"""
MCP — Model Context Protocol Client

MCP is Anthropic's open standard that lets LLMs connect to external
data sources and tools via a standardized JSON-RPC-like protocol.

Reference: https://modelcontextprotocol.io/

This module implements:
    1. MCPServer  — represents a running MCP server process
    2. MCPClient  — connects to an MCP server and discovers tools
    3. MCPTool    — wraps an MCP-discovered tool as a BaseTool
    4. MCPRegistry— auto-populates ToolRegistry from MCP servers
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from core.exceptions import ToolExecutionError
from tools.base_tool import BaseTool, ToolDefinition

logger = structlog.get_logger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    name: str
    base_url: str                        # HTTP transport URL
    api_key: str = ""
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)


class MCPClient:
    """
    HTTP-based MCP client.

    MCP uses JSON-RPC 2.0 over HTTP (or stdio for local servers).
    This client uses HTTP transport.

    Protocol flow:
        1. initialize        → handshake, get server capabilities
        2. tools/list        → discover available tools
        3. tools/call        → execute a tool
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self._config = config
        self._session_id: str | None = None
        self._tools_cache: list[dict[str, Any]] | None = None

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            **self._config.headers,
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    async def _jsonrpc(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send a JSON-RPC 2.0 request and return the result."""
        payload = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": method,
            "params": params or {},
        }

        async with httpx.AsyncClient(
            timeout=self._config.timeout,
            headers=self._build_headers(),
        ) as client:
            resp = await client.post(
                f"{self._config.base_url}/mcp",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            raise ToolExecutionError(
                f"mcp:{method}",
                f"MCP error {data['error'].get('code')}: "
                f"{data['error'].get('message')}",
            )

        return data.get("result")

    async def initialize(self) -> dict[str, Any]:
        """Handshake with the MCP server."""
        result = await self._jsonrpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {
                "name": "ask-the-web-agent",
                "version": "1.0.0",
            },
        })
        logger.info(
            "mcp.initialized",
            server=self._config.name,
            server_info=result.get("serverInfo", {}),
        )

        # Send initialized notification
        await self._jsonrpc("notifications/initialized")
        return result

    async def list_tools(self) -> list[dict[str, Any]]:
        """Discover all tools offered by this MCP server."""
        if self._tools_cache is not None:
            return self._tools_cache

        result = await self._jsonrpc("tools/list")
        tools = result.get("tools", [])
        self._tools_cache = tools

        logger.info(
            "mcp.tools_discovered",
            server=self._config.name,
            tool_names=[t["name"] for t in tools],
        )
        return tools

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        """Execute a tool on the MCP server."""
        result = await self._jsonrpc("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        content = result.get("content", [])
        if not content:
            return ""

        # MCP content blocks: text, image, resource
        text_parts = [
            block.get("text", "")
            for block in content
            if block.get("type") == "text"
        ]
        return "\n".join(text_parts)


class MCPTool(BaseTool):
    """
    Wraps an MCP-discovered tool as a standard BaseTool.
    Allows seamless integration into the existing ToolRegistry.
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        tool_spec: dict[str, Any],
    ) -> None:
        self._client = mcp_client
        self._spec = tool_spec
        self._definition = ToolDefinition(
            name=tool_spec["name"],
            description=tool_spec.get("description", ""),
            parameters=tool_spec.get("inputSchema", {
                "type": "object",
                "properties": {},
            }),
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, **kwargs: Any) -> str:
        try:
            return await self._client.call_tool(
                self._definition.name, kwargs
            )
        except Exception as exc:
            raise ToolExecutionError(self._definition.name, str(exc)) from exc


class MCPRegistry:
    """
    Auto-populates a ToolRegistry by connecting to one or more MCP servers
    and discovering their tools.

    Usage:
        mcp_registry = MCPRegistry()
        mcp_registry.add_server(MCPServerConfig(
            name="filesystem",
            base_url="http://localhost:3001",
        ))
        tool_registry = await mcp_registry.build_registry(base_registry)
    """

    def __init__(self) -> None:
        self._servers: list[MCPServerConfig] = []

    def add_server(self, config: MCPServerConfig) -> "MCPRegistry":
        self._servers.append(config)
        return self

    async def build_registry(
        self,
        base_registry: "ToolRegistry | None" = None,
    ) -> "ToolRegistry":
        """Connect to all servers, discover tools, return populated registry."""
        from tools.tool_registry import ToolRegistry  # avoid circular

        registry = base_registry or ToolRegistry()

        async def _load_server(config: MCPServerConfig) -> None:
            try:
                client = MCPClient(config)
                await client.initialize()
                tool_specs = await client.list_tools()

                for spec in tool_specs:
                    tool = MCPTool(mcp_client=client, tool_spec=spec)
                    registry.register(tool)
                    logger.info(
                        "mcp.tool_registered",
                        server=config.name,
                        tool=spec["name"],
                    )
            except Exception as exc:
                logger.error(
                    "mcp.server_failed",
                    server=config.name,
                    error=str(exc),
                )

        await asyncio.gather(*[_load_server(cfg) for cfg in self._servers])
        return registry