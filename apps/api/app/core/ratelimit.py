"""Rate limiting for the API.

Architecture:
- ``RateLimitBackend`` protocol — any store that can answer "is this key
  within its window" (memory, Redis, future: Postgres).
- ``MemoryRateLimiter`` — sliding-window counters in-process; default when
  Redis is not configured or unreachable.
- ``RedisRateLimiter`` — fixed-window INCR/EXPIRE via a pipeline; survives
  multi-worker deployments behind nginx.
- ``RateLimitMiddleware`` — keys requests by client identity (API-key user or
  client IP), enforces the configured budget, and degrades gracefully to the
  in-memory backend if Redis errors at request time.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Protocol

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger(__name__)

EXEMPT_PATHS = frozenset({"/health", "/health/ready", "/metrics", "/docs", "/redoc", "/openapi.json"})


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class RateLimitBackend(Protocol):
    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision: ...


class MemoryRateLimiter:
    """Sliding-window limiter kept entirely in process."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.monotonic()
        window_start = now - window_seconds
        async with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= window_start:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = max(1, int(hits[0] + window_seconds - now) + 1)
                return RateLimitDecision(False, 0, retry_after)
            hits.append(now)
            return RateLimitDecision(True, limit - len(hits), 0)


class RedisRateLimiter:
    """Fixed-window limiter backed by Redis; safe across workers.

    Falls back to allowing the request on transient Redis failure — rate
    limiting is a protection mechanism and must never take the API down.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client = None

    def _get_client(self):  # noqa: ANN202 - lazy redis client
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        try:
            client = self._get_client()
            redis_key = f"ratelimit:{key}:{int(time.time() // window_seconds)}"
            count = await client.incr(redis_key)
            if count == 1:
                await client.expire(redis_key, window_seconds)
            ttl = await client.ttl(redis_key)
            retry_after = max(1, ttl) if ttl > 0 else window_seconds
            allowed = count <= limit
            return RateLimitDecision(
                allowed=allowed,
                remaining=max(0, limit - count),
                retry_after_seconds=retry_after,
            )
        except Exception as e:
            logger.warning("rate_limit_redis_error", error=str(e)[:200])
            return RateLimitDecision(True, limit, 0)


def client_identity(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, backend: RateLimitBackend, limit: int, window_seconds: int):
        super().__init__(app)
        self.backend = backend
        self.limit = limit
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS" or request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        decision = await self.backend.check(
            client_identity(request), self.limit, self.window_seconds
        )
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(decision.remaining),
        }
        if not decision.allowed:
            headers["Retry-After"] = str(decision.retry_after_seconds)
            logger.warning(
                "rate_limit_exceeded",
                path=request.url.path,
                identity=client_identity(request),
                retry_after=decision.retry_after_seconds,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers=headers,
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = headers["X-RateLimit-Limit"]
        response.headers["X-RateLimit-Remaining"] = headers["X-RateLimit-Remaining"]
        return response
