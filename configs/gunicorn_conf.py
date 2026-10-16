"""
Gunicorn configuration for multi-worker production serving.

Why Gunicorn + uvicorn workers instead of bare uvicorn:
* Master process supervises workers — a wedged worker is replaced, not
  load-bearing (FMEA FM-11/FM-17).
* Zero-downtime reloads and SIGTERM-drain semantics match the K8s
  termination budget (45s grace, see deploy/k8s/deployment.yaml).
"""

import multiprocessing
import os

bind = os.getenv("APP_BIND", "0.0.0.0:8000")
workers = int(os.getenv("APP_WORKERS", max(2, multiprocessing.cpu_count() * 2 + 1)))
worker_class = "uvicorn.workers.UvicornWorker"

# ── Timeout / lifecycle ───────────────────────────────────────────────────
# Must stay BELOW the K8s terminationGracePeriodSeconds (45s) so in-flight
# SSE streams drain before the pod is killed.
timeout = 40
graceful_timeout = 35
keepalive = 5

# ── Performance ───────────────────────────────────────────────────────────
max_requests = 10_000            # recycle workers to bound any slow leak
max_requests_jitter = 1_000      # desynchronize recycles across workers
preload_app = True               # fork after import: faster boots, shared imports

# ── Logging ───────────────────────────────────────────────────────────────
# structlog owns log formatting; gunicorn only logs lifecycle events.
accesslog = "-"                  # stdout
errorlog = "-"                   # stderr
loglevel = os.getenv("LOG_LEVEL", "INFO").lower()


def on_starting(server) -> None:
    server.log.info("gunicorn.starting workers=%d bind=%s", workers, bind)


def worker_int(worker) -> None:
    worker.log.info("gunicorn.worker_interrupt pid=%s", worker.pid)


def on_worker_exit(server, worker) -> None:
    server.log.info("gunicorn.worker_exit pid=%s code=%s", worker.pid, worker.exit_code)
