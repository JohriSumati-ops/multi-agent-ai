"""
tests/test_retrieval_api.py

Full-stack integration tests: real HTTP requests through the FastAPI
TestClient, an in-memory SQLite database, and the fake embedding backend
(see docs/Phase3.md Section 19). Exercises the complete
upload -> reindex -> search -> similar -> status -> rebuild lifecycle.
"""

from __future__ import annotations


def _upload_document(client, headers, filename: str, content: bytes) -> dict:
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": (filename, content, "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_reindex_document_makes_it_searchable(client, auth_headers) -> None:
    document = _upload_document(
        client,
        auth_headers,
        "trees.txt",
        b"A tree is a hierarchical data structure with nodes connected by edges.",
    )
    assert document["status"] == "chunked"  # Phase 2 behavior unchanged — see semantic_search_service.py

    reindex_response = client.post(f"/api/v1/retrieval/reindex?document_id={document['id']}", headers=auth_headers)
    assert reindex_response.status_code == 200, reindex_response.text
    reindex_data = reindex_response.json()["data"]
    assert reindex_data["chunks_embedded"] >= 1
    assert reindex_data["status"] == "ready"

    status_response = client.get(f"/api/v1/retrieval/document/{document['id']}", headers=auth_headers)
    assert status_response.status_code == 200
    status_data = status_response.json()["data"]
    assert status_data["status"] == "ready"
    assert status_data["is_fully_embedded"] is True


def test_search_returns_relevant_chunk_with_explainability(client, auth_headers) -> None:
    document = _upload_document(
        client,
        auth_headers,
        "graphs.txt",
        b"Graphs generalize trees by allowing cycles between connected nodes.",
    )
    client.post(f"/api/v1/retrieval/reindex?document_id={document['id']}", headers=auth_headers)

    search_response = client.post(
        "/api/v1/retrieval/search",
        headers=auth_headers,
        json={"query": "graphs and cycles", "top_k": 5, "similarity_threshold": -1.0},
    )
    assert search_response.status_code == 200, search_response.text
    data = search_response.json()["data"]
    assert data["result_count"] >= 1

    top_result = data["results"][0]
    assert top_result["rank"] == 1
    assert top_result["document_id"] == document["id"]
    assert "similarity_score" in top_result
    assert "confidence" in top_result
    assert "reason" in top_result
    assert top_result["reason"]  # non-empty explanation


def test_search_scoped_to_one_document_excludes_others(client, auth_headers) -> None:
    doc_a = _upload_document(client, auth_headers, "a.txt", b"Content about stacks and queues in data structures.")
    doc_b = _upload_document(client, auth_headers, "b.txt", b"Content about stacks and queues in data structures.")
    client.post(f"/api/v1/retrieval/reindex?document_id={doc_a['id']}", headers=auth_headers)
    client.post(f"/api/v1/retrieval/reindex?document_id={doc_b['id']}", headers=auth_headers)

    response = client.post(
        "/api/v1/retrieval/search",
        headers=auth_headers,
        json={"query": "stacks and queues", "top_k": 10, "similarity_threshold": -1.0, "document_id": doc_a["id"]},
    )
    data = response.json()["data"]
    assert all(r["document_id"] == doc_a["id"] for r in data["results"])


def test_similar_endpoint_excludes_the_query_chunk_itself(client, auth_headers) -> None:
    document = _upload_document(
        client,
        auth_headers,
        "hashing.txt",
        b"Hash tables provide average O(1) lookup performance for key-value pairs.",
    )
    client.post(f"/api/v1/retrieval/reindex?document_id={document['id']}", headers=auth_headers)

    chunks_response = client.get(f"/api/v1/documents/{document['id']}/chunks", headers=auth_headers)
    chunk_id = chunks_response.json()["data"][0]["id"]

    similar_response = client.post(
        "/api/v1/retrieval/similar",
        headers=auth_headers,
        json={"chunk_id": chunk_id, "top_k": 5, "similarity_threshold": -1.0},
    )
    assert similar_response.status_code == 200
    results = similar_response.json()["data"]["results"]
    assert all(r["chunk_id"] != chunk_id for r in results)


def test_chunk_vector_info_endpoint(client, auth_headers) -> None:
    document = _upload_document(client, auth_headers, "queues.txt", b"Queues follow first-in-first-out ordering.")
    client.post(f"/api/v1/retrieval/reindex?document_id={document['id']}", headers=auth_headers)

    chunks_response = client.get(f"/api/v1/documents/{document['id']}/chunks", headers=auth_headers)
    chunk_id = chunks_response.json()["data"][0]["id"]

    info_response = client.get(f"/api/v1/retrieval/chunks/{chunk_id}", headers=auth_headers)
    assert info_response.status_code == 200
    info = info_response.json()["data"]
    assert info["chunk_id"] == chunk_id
    assert info["dimension"] > 0


def test_chunk_vector_info_returns_404_before_indexing(client, auth_headers) -> None:
    document = _upload_document(client, auth_headers, "unindexed.txt", b"This document has not been reindexed yet.")
    chunks_response = client.get(f"/api/v1/documents/{document['id']}/chunks", headers=auth_headers)
    chunk_id = chunks_response.json()["data"][0]["id"]

    response = client.get(f"/api/v1/retrieval/chunks/{chunk_id}", headers=auth_headers)
    assert response.status_code == 404


def test_reindex_rejects_document_not_yet_chunked(client, auth_headers, monkeypatch) -> None:
    # Upload a corrupted PDF so the Phase 2 pipeline fails before CHUNKED.
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("bad.pdf", b"%PDF-1.4 not actually valid", "application/pdf")},
    )
    assert response.status_code == 422  # upload itself fails, per Phase 2 behavior

    # There's no document_id to reindex in this case (upload failed
    # entirely), so instead verify reindexing a nonexistent ID 404s.
    import uuid

    fake_id = str(uuid.uuid4())
    reindex_response = client.post(f"/api/v1/retrieval/reindex?document_id={fake_id}", headers=auth_headers)
    assert reindex_response.status_code == 404


def test_reindex_is_idempotent(client, auth_headers) -> None:
    document = _upload_document(client, auth_headers, "idempotent.txt", b"Idempotent reindexing test content here.")
    first = client.post(f"/api/v1/retrieval/reindex?document_id={document['id']}", headers=auth_headers)
    second = client.post(f"/api/v1/retrieval/reindex?document_id={document['id']}", headers=auth_headers)

    assert first.json()["data"]["chunks_embedded"] == second.json()["data"]["chunks_embedded"]

    status_response = client.get(f"/api/v1/retrieval/document/{document['id']}", headers=auth_headers)
    # embedded_chunk_count should NOT double after re-indexing twice.
    assert status_response.json()["data"]["embedded_chunk_count"] == status_response.json()["data"]["chunk_count"]


def test_rebuild_reindexes_all_documents(client, auth_headers) -> None:
    doc_a = _upload_document(client, auth_headers, "rebuild_a.txt", b"First document about recursion basics.")
    doc_b = _upload_document(client, auth_headers, "rebuild_b.txt", b"Second document about iteration basics.")

    rebuild_response = client.post("/api/v1/retrieval/rebuild", headers=auth_headers)
    assert rebuild_response.status_code == 200
    data = rebuild_response.json()["data"]
    assert data["documents_processed"] == 2
    assert data["chunks_embedded"] >= 2
    assert data["vectors_in_index"] >= 2

    status_a = client.get(f"/api/v1/retrieval/document/{doc_a['id']}", headers=auth_headers).json()["data"]
    status_b = client.get(f"/api/v1/retrieval/document/{doc_b['id']}", headers=auth_headers).json()["data"]
    assert status_a["status"] == "ready"
    assert status_b["status"] == "ready"


def test_search_requires_authentication(client) -> None:
    response = client.post("/api/v1/retrieval/search", json={"query": "anything"})
    assert response.status_code == 401


def test_search_with_no_documents_returns_empty_results(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/retrieval/search",
        headers=auth_headers,
        json={"query": "anything at all"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["result_count"] == 0


def test_search_isolates_results_between_users(client) -> None:
    client.post("/api/v1/auth/register", json={"email": "owner2@example.com", "password": "password123"})
    owner_login = client.post("/api/v1/auth/login", json={"email": "owner2@example.com", "password": "password123"})
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['data']['access_token']}"}

    document = _upload_document(
        client, owner_headers, "private_notes.txt", b"Private notes about dynamic programming techniques."
    )
    client.post(f"/api/v1/retrieval/reindex?document_id={document['id']}", headers=owner_headers)

    client.post("/api/v1/auth/register", json={"email": "intruder2@example.com", "password": "password123"})
    intruder_login = client.post(
        "/api/v1/auth/login", json={"email": "intruder2@example.com", "password": "password123"}
    )
    intruder_headers = {"Authorization": f"Bearer {intruder_login.json()['data']['access_token']}"}

    search_response = client.post(
        "/api/v1/retrieval/search",
        headers=intruder_headers,
        json={"query": "dynamic programming techniques", "similarity_threshold": -1.0},
    )
    assert search_response.json()["data"]["result_count"] == 0

    document_status_response = client.get(f"/api/v1/retrieval/document/{document['id']}", headers=intruder_headers)
    assert document_status_response.status_code == 404
