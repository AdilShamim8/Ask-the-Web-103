# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for lxml and friends
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a virtual environment (layer-cached: deps
# change far less often than code — pyproject first, source later).
#
# NOTE (fixed 2026-10-16): three bugs fixed in this stage —
#   1. LICENSE must be present: pyproject declares license = {file=...}
#      and hatchling hard-fails ("License file does not exist") when it
#      is missing. It is now un-dockerignored and copied here.
#   2. Hatchling needs the package directories to exist at build time,
#      so stub packages are created before `pip install`. The real code
#      lands in the runtime stage via `COPY . .` and shadows the stubs
#      at import time (gunicorn inserts /app at sys.path[0]).
#   3. Install WITHOUT [dev]: CI runs tests, not the image. Shipping
#      pytest/mypy/ruff to production only adds weight and CVE surface
#      for the trivy gate to trip over.
COPY pyproject.toml README.md LICENSE ./
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN mkdir -p core configs tools agents workflows api evaluation \
    && touch core/__init__.py configs/__init__.py tools/__init__.py \
       agents/__init__.py workflows/__init__.py api/__init__.py \
       evaluation/__init__.py \
    && pip install --upgrade pip && pip install .

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps.
# NOTE (fixed 2026-10-16): curl is now installed in the RUNTIME stage —
# the previous image's HEALTHCHECK invoked curl that only existed in the
# builder stage, so every healthcheck failed while the app was healthy.
# See docs/DEPLOYMENT.md and FMEA FM-17.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libexpat1 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Virtual env from builder (no build toolchain ships to runtime)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Playwright browsers (fixed 2026-10-16):
# browsers are installed to /opt/ms-playwright — a world-readable path.
# The previous build installed them as root into /root/.cache, which
# appuser (uid 1000) cannot traverse, so every scrape blew up at
# browser-launch time in the published image while /healthz stayed
# green — a silent feature loss (FMEA FM-14 class).
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
RUN playwright install chromium

# Application code (dockerignore keeps this layer small)
COPY . .

# Non-root user; own /app for any runtime writes (logs, caches)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness: process-level, CHEAP — matches /healthz contract (no
# provider calls, no Redis). Deep checks are /readyz, used by K8s.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/v1/healthz || exit 1

# Production server: gunicorn supervises uvicorn workers
# (configs/gunicorn_conf.py — worker recycling, graceful drain).
CMD ["gunicorn", "api.main:app", \
     "--config", "configs/gunicorn_conf.py"]
