"""Prometheus instrumentation for the API.

Exposes:
- ``http_requests_total{method, route, status}`` — cumulative request count
- ``http_request_duration_seconds`` — latency histogram per route
- ``http_requests_in_progress`` — gauge of concurrent in-flight requests
- Python GC/platform collectors (default prometheus_client registry)

The ``/metrics`` endpoint renders the standard Prometheus text format and is
exempt from rate limiting and auth so scrapers can reach it.
"""

from __future__ import annotations

import time

import structlog
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

logger = structlog.get_logger(__name__)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests processed.",
    labelnames=["method", "route", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    labelnames=["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being served.",
    labelnames=["method"],
)


def route_template(request: Request) -> str:
    """Best-known route pattern; falls back to the raw path when unrouted."""
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return str(route.path)
    for route_obj in request.app.router.routes:
        match, _child_scope = route_obj.matches(request.scope)
        if match == Match.FULL:
            return str(getattr(route_obj, "path", request.url.path))
    return request.url.path


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            HTTP_REQUESTS_TOTAL.labels(
                method=method, route=route_template(request), status="500"
            ).inc()
            HTTP_REQUEST_DURATION.labels(method=method, route=route_template(request)).observe(
                time.perf_counter() - start
            )
            raise
        finally:
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()

        duration = time.perf_counter() - start
        template = route_template(request)
        HTTP_REQUESTS_TOTAL.labels(method=method, route=template, status=response.status_code).inc()
        HTTP_REQUEST_DURATION.labels(method=method, route=template).observe(duration)
        return response


async def metrics_endpoint(request: Request) -> Response:
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
