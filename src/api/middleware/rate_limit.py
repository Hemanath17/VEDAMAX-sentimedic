"""
Rate limiting middleware for the VEDAMAX API.

Uses a sliding-window in-memory counter per IP address.
Applied as FastAPI middleware so it intercepts ALL requests
before they reach any route handler — more reliable than
a per-route function call which depends on FastAPI's
argument injection working correctly.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

MAX_REQUESTS_PER_WINDOW = 10
WINDOW_SECONDS = 60

# Routes that are rate-limited (LLM-backed, cost money per call)
RATE_LIMITED_PATHS = {"/query", "/upload", "/ingest"}

_request_log: Dict[str, List[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter applied at the ASGI middleware layer."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only rate-limit the expensive endpoints
        path = request.url.path.rstrip("/")
        if path not in RATE_LIMITED_PATHS:
            return await call_next(request)

        client_ip = (
            request.client.host if request.client else "unknown"
        )
        now = time.time()
        window_start = now - WINDOW_SECONDS

        # Prune old entries and check limit
        recent = [t for t in _request_log[client_ip] if t > window_start]

        if len(recent) >= MAX_REQUESTS_PER_WINDOW:
            return Response(
                content=(
                    f'{{"detail":"Rate limit exceeded: max {MAX_REQUESTS_PER_WINDOW} '
                    f'requests per {WINDOW_SECONDS} seconds."}}'
                ),
                status_code=429,
                media_type="application/json",
            )

        recent.append(now)
        _request_log[client_ip] = recent
        return await call_next(request)
