"""Simple in-memory per-IP rate limiting for the query endpoint.

Built directly rather than via slowapi, which is incompatible with current
FastAPI/Starlette versions (the limiter silently no-ops instead of
enforcing limits). For a single endpoint, a small dependency-based limiter
is more reliable than fighting an unmaintained library's version drift.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List

from fastapi import HTTPException, Request

MAX_REQUESTS_PER_WINDOW = 10
WINDOW_SECONDS = 60

# IP -> list of request timestamps within the current window.
_request_log: Dict[str, List[float]] = defaultdict(list)


def enforce_rate_limit(request: Request) -> None:
    """Raise 429 if the caller's IP has exceeded the request limit."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    window_start = now - WINDOW_SECONDS
    recent = [t for t in _request_log[client_ip] if t > window_start]

    if len(recent) >= MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {MAX_REQUESTS_PER_WINDOW} "
            f"requests per {WINDOW_SECONDS} seconds.",
        )

    recent.append(now)
    _request_log[client_ip] = recent
