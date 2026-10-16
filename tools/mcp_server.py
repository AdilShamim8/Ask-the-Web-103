"""
MCP Server — expose Ask-the-Web's internal tools to OTHER MCP clients.

Why: ADR-004 — MCP is the tool boundary in BOTH directions. We consume
external MCP servers (mcp_client.py), and we can BE one: any MCP-capable
assistant (Claude Desktop, other agents) can then use our hardened web
search / scraper / calculator through the same guards (budgets, SSRF,
truncation) that protect our own agent.

Endpoints (JSON-RPC 2.0 over HTTP POST /mcp):
    initialize               → handshake
    notifications/initialized→ no-op ack
    tools/list               → schema of every registry tool
    tools/call               → execute via ToolExecutor (ALL guards apply)
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)

_PROTOCOL_VERSION = "2024-11-05"
_SERVER_INFO = {"name": "ask-the-web-agent", "version": "2.0.0"}

_JSONRPC_ERRORS = {
    -32700: "Parse error",
    -32600: "Invalid request",
    -32601: "Method not found",
    -32602: "Invalid params",
    -32603: "Internal error",
}


def _rpc_response(rpc_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _rpc_error(rpc_id: str, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id,
            "error": {"code": code, "message": message}}


def create_mcp_server(
    registry: ToolRegistry,
    executor: ToolExecutor,
) -> APIRouter:
    """
    Factory: MCP-compliant FastAPI router over an existing tool registry.

    The executor enforces budgets/SSRF/timeouts — external MCP callers get
    the same protection as our own agent. This is the invariant that makes
    being an MCP server safe, not a privilege escalation hole.
    """
    router = APIRouter(prefix="/mcp", tags=["MCP"], include_in_schema=True)

    @router.post("")
    async def handle_rpc(request: Request) -> JSONResponse:
        rpc_id: str = ""
        try:
            body = await request.json()
            rpc_id = body.get("id", "")
            method = body.get("method", "")
            params = body.get("params", {}) or {}

            if method == "initialize":
                result = {
                    "protocolVersion": _PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": _SERVER_INFO,
                }

            elif method == "notifications/initialized":
                # Notifications carry no id per spec — ack with 204-ish body.
                return JSONResponse({})

            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": d.name,
                            "description": d.description,
                            "inputSchema": d.parameters,
                        }
                        for d in registry.get_definitions()
                    ]
                }

            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {}) or {}

                from core.exceptions import ToolNotFoundError
                from core.message_types import ToolCall

                try:
                    call = ToolCall(
                        id=f"mcp_{uuid.uuid4().hex[:8]}",
                        name=tool_name,
                        arguments=arguments,
                    )
                    tool_result = await executor.execute_one(call)
                    result = {
                        "content": [{
                            "type": "text",
                            "text": tool_result.content,
                        }],
                        "isError": tool_result.is_error,
                    }
                except ToolNotFoundError as exc:
                    return JSONResponse(_rpc_error(rpc_id, -32601, str(exc)))

            else:
                return JSONResponse(
                    _rpc_error(rpc_id, -32601, f"Unknown method: {method}")
                )

            logger.debug("mcp_server.rpc", method=method, ok=True)
            return JSONResponse(_rpc_response(rpc_id, result))

        except Exception as exc:
            logger.warning("mcp_server.rpc_error", error=str(exc)[:200])
            return JSONResponse(
                _rpc_error(rpc_id, -32603, "Internal error")
            )

    return router
