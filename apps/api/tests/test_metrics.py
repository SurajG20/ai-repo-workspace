from __future__ import annotations

import re

import pytest
from app.core.metrics import MetricsMiddleware, metrics_endpoint
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def instrumented_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)
    app.add_route("/metrics", metrics_endpoint, include_in_schema=False)

    @app.get("/repos/{repository_id}")
    async def get_repo(repository_id: str) -> dict[str, str]:
        return {"id": repository_id}

    return app


def test_metrics_endpoint_renders_prometheus_format(instrumented_app: FastAPI):
    client = TestClient(instrumented_app)
    client.get("/repos/abc-123")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert b"http_requests_total" in response.content
    assert b"http_request_duration_seconds" in response.content
    assert b"http_requests_in_progress" in response.content


def test_metrics_labels_use_route_template_not_raw_path(instrumented_app: FastAPI):
    client = TestClient(instrumented_app)
    client.get("/repos/secret-id-should-never-leak")
    body = client.get("/metrics").text

    line = next(l for l in body.splitlines() if l.startswith("http_requests_total{"))  # noqa: E741
    assert 'route="/repos/{repository_id}"' in line
    assert "secret-id-should-never-leak" not in body


def test_metrics_record_status_codes(instrumented_app: FastAPI):
    client = TestClient(instrumented_app)
    client.get("/does-not-exist")
    body = client.get("/metrics").text

    assert re.search(r'http_requests_total\{.*status="404"', body)
