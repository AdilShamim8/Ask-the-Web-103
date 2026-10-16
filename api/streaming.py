"""
SSE streaming — proper Server-Sent Events with heartbeats.

Production failure modes addressed (FM-10):
* Heartbeats every 15s keep intermediaries (LBs, proxies) from closing
  idle connections while the agent is thinking.
* Client disconnect detection: the generator stops work when the client
  is gone — no wasted compute streaming into a dead socket.
* Hard stream deadline: a stream can never outlive the request budget.
* Every event is valid SSE (``event:``/``data:`` framing), so generic
  SSE clients work, not just our own.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import structlog

logger = structlog.get_logger(__name__)

HEARTBEAT_INTERVAL_S = 15.0
STREAM_DEADLINE_S = 90.0


def sse_event(event: str, data: Any) -> str:
    """Format one SSE frame."""
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


async def sse_stream(
    *,
    producer: AsyncIterator[dict[str, Any]],
    is_disconnected=None,
) -> AsyncIterator[str]:
    """
    Wrap a producer of dict events into a resilient SSE byte stream.

    ``producer``: async generator yielding dicts like
        {"event": "token", "data": {...}}
    ``is_disconnected``: optional callable → bool (client gone?).

    The stream emits ``heartbeat`` events during producer silence and
    terminates with ``done`` or ``error``.
    """
    producer_aiter = producer.__aiter__()
    last_activity = asyncio.get_event_loop().time()
    deadline = last_activity + STREAM_DEADLINE_S
    closed = False

    while not closed:
        now = asyncio.get_event_loop().time()
        if now > deadline:
            logger.warning("stream.deadline_exceeded")
            yield sse_event("error", {"error": "stream_deadline", "retryable": True})
            return

        if is_disconnected is not None:
            try:
                if is_disconnected():
                    logger.info("stream.client_disconnected")
                    return
            except Exception:
                pass

        # Give the producer up to HEARTBEAT_INTERVAL_S, then emit a beat.
        try:
            item = await asyncio.wait_for(
                producer_aiter.__anext__(), timeout=HEARTBEAT_INTERVAL_S
            )
            last_activity = now
        except asyncio.TimeoutError:
            yield sse_event("heartbeat", {"t": round(now, 2)})
            continue
        except StopAsyncIteration:
            return
        except Exception as exc:
            logger.error("stream.producer_error", error=str(exc)[:200])
            yield sse_event("error", {"error": str(exc)[:256]})
            return

        event = item.get("event", "message")
        data = item.get("data", {})
        yield sse_event(event, data)

        if event in ("done", "error"):
            return
