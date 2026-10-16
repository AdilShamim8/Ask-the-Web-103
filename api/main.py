"""
FastAPI application factory.

Lifespan responsibilities (startup → shutdown):
    1. Configure logging (JSON in prod, redaction always)
    2. Build singletons: settings, cache, LLM client, tool registry
    3. Optional MCP server discovery (opt-in via MCP_SERVERS config)
    4. Freeze the tool registry after discovery (ADR-001)
    5. Warm Playwright for scraper fallback (optional, degrades quietly)
    6. Shutdown: close cache, HTTP pool, browser — drain cleanly

Middleware order (outermost → innermost): RequestID → Logging →
SecurityHeaders → RateLimit → ErrorHandler → CORS. Errors thrown
anywhere produce typed JSON with the request ID.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from api.cache import ResponseCache
from api.middleware import (
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from api.routes import router
from configs.logging_config import configure_logging
from configs.settings import get_settings
from core.llm_client import LLMClient
from tools import build_default_registry
from tools.http_client import close_http_client
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown lifecycle."""
    configure_logging()
    settings = get_settings()

    logger.info(
        "app.starting",
        env=settings.app_env,
        model=settings.default_model,
        fast_model=settings.fast_model,
        search=settings.search_provider.value,
        version=settings.api_version,
    )

    # ── Singletons ───────────────────────────────────────────────────
    app.state.settings = settings
    app.state.cache = ResponseCache()
    app.state.llm_client = LLMClient()

    registry: ToolRegistry = build_default_registry()
    app.state.tool_registry = registry
    app.state.tool_executor = ToolExecutor(registry)

    # ── Optional MCP discovery (external tool servers) ───────────────
    # MCP_SERVERS format: "name1=http://host:port,name2=http://host:port"
    mcp_servers = _parse_mcp_servers()
    if mcp_servers:
        from tools.mcp_client import MCPRegistry

        mcp_registry = MCPRegistry()
        for cfg in mcp_servers:
            mcp_registry.add_server(cfg)
        registry = await mcp_registry.build_registry(base_registry=registry)
        app.state.tool_registry = registry
        app.state.tool_executor = ToolExecutor(registry)

    registry.freeze()  # read-only from here on (ADR-001)
    logger.info("app.tools_ready", tools=registry.names())

    # ── Optional Playwright warm-up (scraper fallback) ────────────────
    try:
        from playwright.async_api import async_playwright

        app.state.playwright = await async_playwright().start()
        app.state.browser = await app.state.playwright.chromium.launch(headless=True)
        logger.info("playwright.ready")
    except Exception as exc:
        logger.warning("playwright.unavailable", error=str(exc)[:150])
        app.state.playwright = None
        app.state.browser = None

    yield  # ── application runs here ──────────────────────────────────

    logger.info("app.shutting_down")
    if getattr(app.state, "browser", None):
        with contextlib.suppress(Exception):
            await app.state.browser.close()
    if getattr(app.state, "playwright", None):
        with contextlib.suppress(Exception):
            await app.state.playwright.stop()
    with contextlib.suppress(Exception):
        await app.state.cache.close()
    with contextlib.suppress(Exception):
        await close_http_client()
    logger.info("app.shutdown_complete")


def _parse_mcp_servers():
    """Parse MCP_SERVERS env into server configs. Empty → no discovery."""
    import os

    from tools.mcp_client import MCPServerConfig

    raw = os.getenv("MCP_SERVERS", "").strip()
    if not raw:
        return []
    servers = []
    for part in raw.split(","):
        if "=" not in part:
            continue
        name, url = part.split("=", 1)
        servers.append(MCPServerConfig(name=name.strip(), base_url=url.strip()))
    return servers


# ── App factory ───────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Ask-the-Web Agent",
        description=(
            "A Perplexity-like AI agent that searches the web, "
            "reasons with ReACT/Reflexion/ReWOO, and returns cited answers."
        ),
        version=settings.api_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware (order matters: added last = outermost) ─────────────
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests=settings.rate_limit_requests,
        window=settings.rate_limit_window,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env == "development" else [],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # ── Routes ─────────────────────────────────────────────────────────
    app.include_router(router, prefix="/v1")

    # Protocol surfaces (A2A + MCP) — built at first request when the
    # app state is ready (registry exists after lifespan startup).
    @app.middleware("http")
    async def _mount_protocols_once(request: Request, call_next):
        if not getattr(app.state, "_protocols_mounted", False):
            from api.a2a_routes import build_protocol_routers

            a2a_router, mcp_router = build_protocol_routers(request)
            app.include_router(a2a_router, prefix="/a2a")
            app.include_router(mcp_router, prefix="")
            app.state._protocols_mounted = True
        return await call_next(request)

    # ── Prometheus metrics ─────────────────────────────────────────────
    app.mount("/metrics", make_asgi_app())

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=get_settings().app_env == "development",
        log_config=None,  # structlog handles logging
        workers=1,        # production uses gunicorn (configs/gunicorn_conf.py)
    )
