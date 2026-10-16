from __future__ import annotations

import contextlib
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from api.cache import ResponseCache
from api.middleware import (
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
)
from api.routes import router
from configs.logging_config import configure_logging
from configs.settings import get_settings

logger = structlog.get_logger(__name__)

# ── Lifespan ──────────────────────────────────────────────────────────────────

_cache: ResponseCache | None = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown lifecycle."""
    global _cache
    configure_logging()
    settings = get_settings()

    logger.info(
        "app.starting",
        env=settings.app_env,
        model=settings.default_model,
        search=settings.search_provider.value,
    )

    # Initialize cache connection
    _cache = ResponseCache()

    # Warm up Playwright browser for scraping
    try:
        from playwright.async_api import async_playwright
        app.state.playwright = await async_playwright().start()
        app.state.browser = await app.state.playwright.chromium.launch(headless=True)
        logger.info("playwright.ready")
    except Exception as exc:
        logger.warning("playwright.unavailable", error=str(exc))
        app.state.playwright = None
        app.state.browser = None

    yield  # ← application runs here

    # Shutdown
    logger.info("app.shutting_down")
    if _cache:
        await _cache.close()
    if getattr(app.state, "browser", None):
        await app.state.browser.close()
    if getattr(app.state, "playwright", None):
        await app.state.playwright.stop()
    logger.info("app.shutdown_complete")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Ask-the-Web Agent",
        description=(
            "A Perplexity-like AI agent that searches the web, "
            "reasons with ReACT/Reflexion, and returns cited answers."
        ),
        version="1.0.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost applied last) ────────────────
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests=settings.rate_limit_requests,
        window=settings.rate_limit_window,
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env == "development" else [],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # ── Routes ─────────────────────────────────────────────────────────────
    app.include_router(router, prefix="/v1")

    # ── Prometheus metrics ─────────────────────────────────────────────────
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

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
        workers=1,        # Use Gunicorn for multi-worker prod
    )