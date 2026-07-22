"""
tests/test_memory_api.py

Full-stack integration tests: real HTTP requests through the FastAPI
TestClient, an in-memory SQLite database, and the fake embedding backend
(see docs/Phase3.md Section 19, reused unmodified in Phase 4).
"""

from __future__ import annotations

import uuid


def test_store_memory_short_term(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/memory/store",
        headers=auth_headers,
        json={"content": "Searched for binary search trees", "persist_long_term": False},
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["memory_type"] == "short_term"
    assert data["expires_at"] is not None


def test_store_memory_long_term(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/memory/store",
        headers=auth_headers,
        json={"content": "User struggles with recursion", "persist_long_term": True, "importance_score": 0.9},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["memory_type"] == "long_term"
    assert data["expires_at"] is None


def test_get_history_returns_stored_memories(client, auth_headers) -> None:
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "memory one"})
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "memory two"})

    response = client.get("/api/v1/memory/history", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2


def test_get_history_filters_by_memory_type(client, auth_headers) -> None:
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "short", "persist_long_term": False})
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "long", "persist_long_term": True})

    response = client.get("/api/v1/memory/history?memory_type=long_term", headers=auth_headers)
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["memory_type"] == "long_term"


def test_get_recent(client, auth_headers) -> None:
    for i in range(3):
        client.post("/api/v1/memory/store", headers=auth_headers, json={"content": f"item {i}"})

    response = client.get("/api/v1/memory/recent?limit=2", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2


def test_search_memory_endpoint(client, auth_headers) -> None:
    client.post(
        "/api/v1/memory/store",
        headers=auth_headers,
        json={"content": "User frequently asks about dynamic programming", "persist_long_term": True},
    )

    response = client.get(
        "/api/v1/memory/search",
        headers=auth_headers,
        params={"query": "dynamic programming", "similarity_threshold": -1.0},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["result_count"] == 1
    assert data["results"][0]["reason"]


def test_statistics_endpoint(client, auth_headers) -> None:
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "one"})
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "two", "persist_long_term": True})

    response = client.get("/api/v1/memory/statistics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_memories"] == 2
    assert data["counts_by_type"]["short_term"] == 1
    assert data["counts_by_type"]["long_term"] == 1


def test_session_store_and_retrieve(client, auth_headers) -> None:
    # Session memory has no dedicated write endpoint in the REST surface
    # (it's written internally by other flows) — this test exercises
    # GET/DELETE against a session that was never written to, which should
    # behave gracefully (empty state), and confirms the endpoints work at
    # the HTTP layer.
    session_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/memory/session?session_id={session_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["state"] == {}


def test_delete_session_returns_404_for_nonexistent_session(client, auth_headers) -> None:
    session_id = str(uuid.uuid4())
    response = client.delete(f"/api/v1/memory/session?session_id={session_id}", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "session_not_found"


def test_delete_history_with_type_filter(client, auth_headers) -> None:
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "short", "persist_long_term": False})
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "long", "persist_long_term": True})

    response = client.delete("/api/v1/memory/history?memory_type=short_term", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["deleted_count"] == 1

    remaining = client.get("/api/v1/memory/history", headers=auth_headers).json()["data"]
    assert len(remaining) == 1
    assert remaining[0]["memory_type"] == "long_term"


def test_prune_endpoint(client, auth_headers) -> None:
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "memory"})

    response = client.delete("/api/v1/memory/prune", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert set(data.keys()) == {"expired_deleted", "over_cap_pruned", "archived"}


def test_clear_endpoint_removes_all_memory(client, auth_headers) -> None:
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "short", "persist_long_term": False})
    client.post("/api/v1/memory/store", headers=auth_headers, json={"content": "long", "persist_long_term": True})

    response = client.post("/api/v1/memory/clear", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["cleared_count"] == 2

    remaining = client.get("/api/v1/memory/history", headers=auth_headers).json()["data"]
    assert remaining == []


def test_memory_endpoints_require_authentication(client) -> None:
    assert client.post("/api/v1/memory/store", json={"content": "x"}).status_code == 401
    assert client.get("/api/v1/memory/history").status_code == 401
    assert client.get("/api/v1/memory/search?query=x").status_code == 401
    assert client.get("/api/v1/memory/statistics").status_code == 401


def test_memory_is_isolated_between_users(client) -> None:
    client.post("/api/v1/auth/register", json={"email": "memA@example.com", "password": "password123"})
    login_a = client.post("/api/v1/auth/login", json={"email": "memA@example.com", "password": "password123"})
    headers_a = {"Authorization": f"Bearer {login_a.json()['data']['access_token']}"}
    client.post("/api/v1/memory/store", headers=headers_a, json={"content": "user A's private memory"})

    client.post("/api/v1/auth/register", json={"email": "memB@example.com", "password": "password123"})
    login_b = client.post("/api/v1/auth/login", json={"email": "memB@example.com", "password": "password123"})
    headers_b = {"Authorization": f"Bearer {login_b.json()['data']['access_token']}"}

    response = client.get("/api/v1/memory/history", headers=headers_b)
    assert response.json()["data"] == []


def test_store_memory_validates_content_length(client, auth_headers) -> None:
    response = client.post("/api/v1/memory/store", headers=auth_headers, json={"content": ""})
    assert response.status_code == 422


def test_store_memory_with_conversation_scope(client, auth_headers) -> None:
    conversation_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/memory/store",
        headers=auth_headers,
        json={"content": "conversation turn content", "conversation_id": conversation_id},
    )
    assert response.status_code == 201
    assert response.json()["data"]["conversation_id"] == conversation_id
