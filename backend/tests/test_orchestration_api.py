"""
tests/test_orchestration_api.py

Full-stack integration tests: real HTTP requests through the FastAPI
TestClient, exercising the complete goal -> plan -> execution ->
explainability pipeline against the three real registered agents.
"""

from __future__ import annotations


def test_list_capabilities(client, auth_headers) -> None:
    response = client.get("/api/v1/orchestration/capabilities", headers=auth_headers)
    assert response.status_code == 200
    capabilities = {c["capability"] for c in response.json()["data"]}
    assert capabilities == {"parse_document", "extract_metadata", "generate_embeddings"}


def test_health_check_endpoint(client, auth_headers) -> None:
    response = client.get("/api/v1/orchestration/health", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()["data"]
    assert all(r["healthy"] for r in results)


def test_execute_goal_with_unregistered_capability_returns_404(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/orchestration/execute",
        headers=auth_headers,
        json={"goal": "do the impossible", "capabilities": ["nonexistent_capability"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "capability_not_registered"


def test_execute_goal_requires_authentication(client) -> None:
    response = client.post(
        "/api/v1/orchestration/execute", json={"goal": "x", "capabilities": ["parse_document"]}
    )
    assert response.status_code == 401


def test_execute_goal_validates_empty_capabilities_list(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/orchestration/execute", headers=auth_headers, json={"goal": "x", "capabilities": []}
    )
    assert response.status_code == 422


def test_execute_goal_end_to_end_with_document_pipeline(client, auth_headers, tmp_path) -> None:
    """
    This exercises the orchestration layer against the SAME agents Phase 2
    already tested via document_service.py — but this time driven entirely
    by the Supervisor/registry/plan machinery, not the hand-written
    pipeline. Since the orchestration API doesn't accept a raw file
    upload, we point `payload.file_path` at a file written directly to
    disk (simulating what a future integration would wire from an
    already-uploaded document's stored path).
    """
    file_path = tmp_path / "orchestrated.txt"
    file_path.write_text("Dynamic programming solves problems via subproblem reuse and memoization.")

    response = client.post(
        "/api/v1/orchestration/execute",
        headers=auth_headers,
        json={
            "goal": "process a document",
            "capabilities": ["parse_document", "extract_metadata"],
            "payload": {
                "file_path": str(file_path),
                "file_format": "txt",
                "original_filename": "orchestrated.txt",
            },
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["plan"]["succeeded"] == 2
    assert data["plan"]["failed"] == 0
    assert len(data["trace"]["timeline"]) == 2
    assert "parse_document" in data["trace"]["agent_selection_reasons"]
    assert "generate_embeddings" in data["trace"]["agents_not_selected"]
    assert data["trace"]["overall_reason"]


def test_execute_goal_reports_partial_failure(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/orchestration/execute",
        headers=auth_headers,
        json={
            "goal": "process a broken document",
            "capabilities": ["parse_document"],
            "payload": {
                "file_path": "/nonexistent/file.txt",
                "file_format": "txt",
                "original_filename": "x.txt",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["plan"]["failed"] == 1
    assert data["plan"]["succeeded"] == 0


def test_orchestration_is_isolated_between_users(client) -> None:
    """Capability listing and health are global (not user-scoped data), but auth is still required per-user."""
    client.post("/api/v1/auth/register", json={"email": "orchA@example.com", "password": "password123"})
    login_a = client.post("/api/v1/auth/login", json={"email": "orchA@example.com", "password": "password123"})
    headers_a = {"Authorization": f"Bearer {login_a.json()['data']['access_token']}"}

    response = client.get("/api/v1/orchestration/capabilities", headers=headers_a)
    assert response.status_code == 200
