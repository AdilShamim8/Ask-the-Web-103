# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for lxml and friends
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a virtual environment (layer-cached: deps
# change far less often than code — pyproject first, source later)
COPY pyproject.toml README.md ./
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install ".[dev]"

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

# Playwright browsers (installed as root, used by appuser)
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
