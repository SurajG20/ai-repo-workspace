from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.ratelimit import (
    EXEMPT_PATHS,
    MemoryRateLimiter,
    RateLimitDecision,
    RateLimitMiddleware,
    RedisRateLimiter,
)


@pytest.fixture
def limited_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        backend=MemoryRateLimiter(),
        limit=3,
        window_seconds=60,
    )

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "true"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_allows_requests_within_budget(limited_app: FastAPI):
    client = TestClient(limited_app)
    for i in range(3):
        response = client.get("/ping")
        assert response.status_code == 200, f"request {i} should pass"
        assert response.headers["X-RateLimit-Limit"] == "3"
        assert response.headers["X-RateLimit-Remaining"] == str(2 - i)


def test_returns_429_with_retry_after_when_exhausted(limited_app: FastAPI):
    client = TestClient(limited_app)
    for _ in range(3):
        client.get("/ping")
    response = client.get("/ping")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) >= 1
    body = response.json()
    assert "Rate limit" in body["detail"]


def test_exempt_paths_bypass_the_limiter(limited_app: FastAPI):
    client = TestClient(limited_app)
    for i in range(5):
        response = client.get("/health")
        assert response.status_code == 200, f"exempt request {i} must never be limited"


@pytest.mark.asyncio
async def test_memory_limiter_window_slides():
    limiter = MemoryRateLimiter()
    for _ in range(2):
        decision = await limiter.check("ip-1", limit=2, window_seconds=60)
        assert decision.allowed
    blocked = await limiter.check("ip-1", limit=2, window_seconds=60)
    assert not blocked.allowed
    other = await limiter.check("ip-2", limit=2, window_seconds=60)
    assert other.allowed


@pytest.mark.asyncio
async def test_redis_limiter_fails_open_on_connection_error(monkeypatch: pytest.MonkeyPatch):
    limiter = RedisRateLimiter("redis://localhost:9999/0")

    class ExplodingClient:
        def incr(self, key):  # noqa: ANN001
            raise ConnectionError("redis down")

    monkeypatch.setattr(limiter, "_get_client", lambda: ExplodingClient())
    decision = await limiter.check("ip-1", limit=10, window_seconds=60)
    assert isinstance(decision, RateLimitDecision)
    assert decision.allowed is True


def test_exempt_paths_cover_operational_surface():
    assert "/health" in EXEMPT_PATHS
    assert "/metrics" in EXEMPT_PATHS
