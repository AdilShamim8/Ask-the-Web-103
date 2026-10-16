"""
MCP — Model Context Protocol Client (hardened).

Protocol reference: https://modelcontextprotocol.io/

Flow per server:
    1. initialize        → handshake, capabilities (protocol 2024-11-05)
    2. tools/list        → discover tools (cached with TTL)
    3. tools/call        → execute a tool

Production changes vs. the course version:
* Shared pooled HTTP transport (tools/http_client.py) — no per-call client
  construction (FM-18).
* Tool discovery cache has a TTL and force-refresh; a server adding a tool
  is picked up without a pod restart.
* ``call_tool`` failures invalidate the session; the next call re-hands
  shakes automatically (self-healing, FM-12).
* Circuit breaker per MCP server — a dead server fails fast instead of
  adding 30s of timeout to every request that references its tools.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

from core.exceptions import MCPError
from core.resilience import BreakerRegistry, retry_with_jitter
from tools.base_tool import BaseTool, ToolDefinition
from tools.http_client import get_http_client
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)

_breakers = BreakerRegistry()
_TRANSIENT = (TimeoutError, ConnectionError)

_MCP_PROTOCOL_VERSION = "2024-11-05"
_TOOL_CACHE_TTL_S = 300.0  # 5 min


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    base_url: str
    api_key: str = ""
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)
    enabled: bool = True


class MCPClient:
    """HTTP-transport MCP client with session and cache management."""

    def __init__(self, config: MCPServerConfig) -> None:
        self._config = config
        self._session_id: str | None = None
        self._tools_cache: list[dict[str, Any]] | None = None
        self._tools_cached_at: float = 0.0

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self._config.headers}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    async def _jsonrpc(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": method,
            "params": params or {},
        }

        client = get_http_client()
        resp = await client.post(
            f"{self._config.base_url.rstrip('/')}/mcp",
            json=payload,
            headers=self._build_headers(),
            timeout=self._config.timeout,
        )
        resp.raise_for_status()

        # Track session when the server assigns one.
        if session := resp.headers.get("mcp-session-id"):
            self._session_id = session

        data = resp.json()
        if "error" in data:
            raise MCPError(
                f"MCP error {data['error'].get('code')}: "
                f"{data['error'].get('message')}",
                context={"server": self._config.name, "method": method},
            )
        return data.get("result")

    async def initialize(self) -> dict[str, Any]:
        """Handshake with the MCP server."""
        result = await self._jsonrpc("initialize", {
            "protocolVersion": _MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "clientInfo": {
                "name": "ask-the-web-agent",
                "version": "2.0.0",
            },
        })
        logger.info(
            "mcp.initialized",
            server=self._config.name,
            server_info=result.get("serverInfo", {}),
        )
        # Notification (no response expected per spec)
        try:
            await self._jsonrpc("notifications/initialized")
        except Exception:
            pass  # servers may 204/ignore notifications
        return result

    async def list_tools(
        self, *, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Discover tools; cached for ``_TOOL_CACHE_TTL_S``."""
        fresh = self._tools_cache is not None and (
            time.monotonic() - self._tools_cached_at < _TOOL_CACHE_TTL_S
        )
        if fresh and not force_refresh:
            return self._tools_cache  # type: ignore[return-value]

        result = await self._jsonrpc("tools/list")
        tools = result.get("tools", [])
        self._tools_cache = tools
        self._tools_cached_at = time.monotonic()

        logger.info(
            "mcp.tools_discovered",
            server=self._config.name,
            tool_names=[t["name"] for t in tools],
        )
        return tools

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        """Execute a tool on the MCP server; self-heals a stale session."""
        try:
            result = await self._jsonrpc("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })
        except MCPError:
            # Session likely invalidated server-side → re-handshake once.
            self._session_id = None
            await self.initialize()
            result = await self._jsonrpc("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })

        content = result.get("content", [])
        if not content:
            return ""

        text_parts = [
            block.get("text", "")
            for block in content
            if block.get("type") == "text"
        ]
        return "\n".join(text_parts)


class MCPTool(BaseTool):
    """Wraps an MCP-discovered tool as a standard BaseTool."""

    timeout_s = 30.0
    cost_hint = "moderate"

    def __init__(self, mcp_client: MCPClient, tool_spec: dict[str, Any]) -> None:
        self._client = mcp_client
        self._definition = ToolDefinition(
            name=tool_spec["name"],
            description=tool_spec.get("description", ""),
            parameters=tool_spec.get("inputSchema", {
                "type": "object", "properties": {},
            }),
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, **kwargs: Any) -> str:
        breaker = _breakers.get_or_create(
            f"mcp:{self._client._config.name}",
        )
        try:
            return await breaker.call(
                lambda: retry_with_jitter(
                    lambda: self._client.call_tool(
                        self._definition.name, kwargs
                    ),
                    attempts=2,
                    retry_on=_TRANSIENT,
                )
            )
        except Exception as exc:
            raise MCPError(
                f"MCP tool '{self._definition.name}' failed: {exc}",
                context={"server": self._client._config.name},
            ) from exc

    async def health_check(self) -> bool:
        try:
            await self._client.list_tools()
            return True
        except Exception:
            return False


class MCPRegistry:
    """
    Auto-populates a ToolRegistry by connecting to MCP servers.

    Failure isolation: one unreachable server logs an error and is skipped
    — it never blocks the others (FM-12/FM-13). Each server loads under a
    per-server timeout so a hung endpoint can't stall startup.
    """

    def __init__(self) -> None:
        self._servers: list[MCPServerConfig] = []

    def add_server(self, config: MCPServerConfig) -> MCPRegistry:
        self._servers.append(config)
        return self

    async def build_registry(
        self,
        base_registry: ToolRegistry | None = None,
    ) -> ToolRegistry:
        # ToolRegistry is imported at module level (no cycle exists:
        # tool_registry imports only core + base_tool). The old
        # function-local "avoid circular import" import was invisible
        # to static analysis, leaving the annotations above flagged as
        # undefined names (F821). Fixed 2026-10-16.
        registry = base_registry or ToolRegistry()

        async def _load_server(config: MCPServerConfig) -> None:
            if not config.enabled:
                return
            try:
                client = MCPClient(config)
                await asyncio.wait_for(client.initialize(), timeout=config.timeout)
                tool_specs = await asyncio.wait_for(
                    client.list_tools(), timeout=config.timeout
                )
                for spec in tool_specs:
                    # Namespace MCP tools to avoid colliding with built-ins:
                    # 'filesystem_read' stays distinct from a local 'read'.
                    spec_name = spec["name"]
                    if not spec_name.startswith("mcp_"):
                        spec = {**spec, "name": f"mcp_{spec_name}"}
                    registry.register(MCPTool(mcp_client=client, tool_spec=spec))
                logger.info(
                    "mcp.server_loaded",
                    server=config.name, tools=len(tool_specs),
                )
            except Exception as exc:
                logger.error(
                    "mcp.server_failed",
                    server=config.name,
                    error=str(exc)[:200],
                )

        await asyncio.gather(*[_load_server(cfg) for cfg in self._servers])
        return registry
