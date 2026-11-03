"""In-process sliding-window rate limiter.

Uses a per-key deque of timestamps.  No Redis required for development —
production should use a Redis-backed limiter for multi-worker deployments.

Usage example in an endpoint:
    from app.core.rate_limit import limiter, RateLimitExceeded

    @router.post("/auth/login")
    async def login(request: Request, ...):
        limiter.check(f"login:{request.client.host}", limit=10, window=60)
        ...
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Thread-safe in-process sliding-window rate limiter."""

    def __init__(self) -> None:
        self._windows: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window: int) -> None:
        """Raise HTTP 429 if ``key`` has exceeded ``limit`` calls in ``window`` seconds."""
        now = time.monotonic()
        cutoff = now - window

        with self._lock:
            dq = self._windows[key]
            # Remove expired timestamps
            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please slow down.",
                    headers={"Retry-After": str(window)},
                )
            dq.append(now)


# Singleton limiter — shared across all requests in the same process
limiter = RateLimiter()


def rate_limit_ip(request: Request, limit: int = 60, window: int = 60) -> None:
    """FastAPI dependency — limit by IP address."""
    ip = request.client.host if request.client else "unknown"
    limiter.check(f"ip:{ip}", limit=limit, window=window)


def rate_limit_auth(request: Request) -> None:
    """Tighter rate limit for authentication endpoints (10 req / 60 s per IP)."""
    ip = request.client.host if request.client else "unknown"
    limiter.check(f"auth:{ip}", limit=10, window=60)
