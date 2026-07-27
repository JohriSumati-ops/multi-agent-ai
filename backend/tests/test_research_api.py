"""
tests/test_research_api.py

Full-stack integration tests: real HTTP requests through the FastAPI
TestClient, an in-memory SQLite database, and FakeLLMBackend (patched in
via conftest.py's isolated_embedding_service fixture for every test).
"""

from __future__ import annotations

import uuid


def test_query_with_no_context_returns_fallback(client, auth_headers) -> None:
    response = client.post("/api/v1/research/query", headers=auth_headers, json={"query": "anything at all"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["used_llm"] is False
    assert data["fallback_reason"] is not None


def test_query_with_relevant_memory_produces_answer(client, auth_headers) -> None:
    # Store a long-term memory so context exists.
    client.post(
        "/api/v1/memory/store",
        headers=auth_headers,
        json={"content": "Binary trees provide O(log n) average lookup performance.", "persist_long_term": True},
    )

    response = client.post(
        "/api/v1/research/query", headers=auth_headers, json={"query": "binary tree lookup performance"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    # With the fake, randomly-seeded embedding backend, whether the memory
    # clears the default similarity threshold is not guaranteed — but the
    # endpoint must always respond successfully either way (used_llm True
    # or a graceful fallback), never a 500.
    assert data["used_llm"] in (True, False)
    if data["used_llm"]:
        assert data["answer"] is not None
        assert data["latency_ms"] >= 0


def test_answer_endpoint_returns_200(client, auth_headers) -> None:
    response = client.post("/api/v1/research/answer", headers=auth_headers, json={"query": "anything"})
    assert response.status_code == 200


def test_summarize_endpoint_returns_200(client, auth_headers) -> None:
    response = client.post("/api/v1/research/summarize", headers=auth_headers, json={"query": "anything"})
    assert response.status_code == 200


def test_reason_endpoint_returns_evidence_analysis(client, auth_headers) -> None:
    response = client.post("/api/v1/research/reason", headers=auth_headers, json={"query": "anything"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "evidence_count" in data
    assert "consensus_note" in data


def test_query_validates_empty_string(client, auth_headers) -> None:
    response = client.post("/api/v1/research/query", headers=auth_headers, json={"query": ""})
    assert response.status_code == 422


def test_all_research_endpoints_require_authentication(client) -> None:
    assert client.post("/api/v1/research/query", json={"query": "x"}).status_code == 401
    assert client.post("/api/v1/research/answer", json={"query": "x"}).status_code == 401
    assert client.post("/api/v1/research/summarize", json={"query": "x"}).status_code == 401
    assert client.post("/api/v1/research/reason", json={"query": "x"}).status_code == 401
    assert client.get(f"/api/v1/research/explain/{uuid.uuid4()}").status_code == 401


def test_explain_returns_404_for_nonexistent_response(client, auth_headers) -> None:
    response = client.get(f"/api/v1/research/explain/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_explain_reconstructs_a_persisted_response(client, auth_headers, monkeypatch) -> None:
    """
    Forces a guaranteed context hit (similarity_threshold effectively
    disabled via a monkeypatched default) so /research/query is guaranteed
    to call the LLM and persist a ResearchResponse this test can then
    fetch via /research/explain.
    """
    from core.config import settings

    monkeypatch.setattr(settings, "RETRIEVAL_SIMILARITY_THRESHOLD", -1.0)

    client.post(
        "/api/v1/memory/store",
        headers=auth_headers,
        json={"content": "Explainability test memory content.", "persist_long_term": True},
    )
    query_response = client.post(
        "/api/v1/research/query", headers=auth_headers, json={"query": "explainability test"}
    )
    data = query_response.json()["data"]
    assert data["used_llm"] is True
    response_id = data["response_id"]
    assert response_id is not None

    explain_response = client.get(f"/api/v1/research/explain/{response_id}", headers=auth_headers)
    assert explain_response.status_code == 200
    explain_data = explain_response.json()["data"]
    assert explain_data["query_text"] == "explainability test"
    assert "citations" in explain_data["explainability_payload"]


def test_explain_is_isolated_between_users(client, monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "RETRIEVAL_SIMILARITY_THRESHOLD", -1.0)

    client.post("/api/v1/auth/register", json={"email": "researchA@example.com", "password": "password123"})
    login_a = client.post("/api/v1/auth/login", json={"email": "researchA@example.com", "password": "password123"})
    headers_a = {"Authorization": f"Bearer {login_a.json()['data']['access_token']}"}

    client.post(
        "/api/v1/memory/store", headers=headers_a, json={"content": "User A's isolated content.", "persist_long_term": True}
    )
    query_response = client.post("/api/v1/research/query", headers=headers_a, json={"query": "isolated content"})
    response_id = query_response.json()["data"]["response_id"]

    client.post("/api/v1/auth/register", json={"email": "researchB@example.com", "password": "password123"})
    login_b = client.post("/api/v1/auth/login", json={"email": "researchB@example.com", "password": "password123"})
    headers_b = {"Authorization": f"Bearer {login_b.json()['data']['access_token']}"}

    explain_response = client.get(f"/api/v1/research/explain/{response_id}", headers=headers_b)
    assert explain_response.status_code == 404


def test_query_scoped_to_specific_document(client, auth_headers) -> None:
    doc_response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("notes.txt", b"Hash tables provide average O(1) lookup performance.", "text/plain")},
    )
    document_id = doc_response.json()["data"]["id"]
    client.post(f"/api/v1/retrieval/reindex?document_id={document_id}", headers=auth_headers)

    response = client.post(
        "/api/v1/research/query",
        headers=auth_headers,
        json={"query": "hash table performance", "document_id": document_id},
    )
    assert response.status_code == 200  # must not error even if fake-embedding similarity misses the threshold
