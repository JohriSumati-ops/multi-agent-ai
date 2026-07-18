"""
tests/test_health.py

Smoke tests for Phase 1's only two business endpoints. These exist mainly
to prove the whole wiring (app -> middleware -> router -> response schema)
actually works end to end, since Phase 1 has no real business logic to test
yet.
"""

from __future__ import annotations


def test_root_endpoint(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "message" in body


def test_health_endpoint_reports_database_status(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] in {"healthy", "degraded"}
    assert isinstance(body["data"]["database"], bool)


def test_version_endpoint(client) -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["app_name"] == "Multi-Agent Research Assistant"


def test_unknown_route_returns_consistent_error_shape(client) -> None:
    response = client.get("/api/v1/definitely-not-a-real-route")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "http_error"
