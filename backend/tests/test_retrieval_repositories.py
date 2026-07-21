"""
tests/test_retrieval_repositories.py

Tests EmbeddingRepository (plain CRUD) and RetrievalRepository (FAISS +
DB composition) directly against `db_session`, without going through the
HTTP layer — see docs/Phase1.md's Repository Pattern rationale for why
this layer is worth testing in isolation.
"""

from __future__ import annotations

import uuid

import numpy as np
import pytest

from models.document import Document, DocumentFormat, DocumentStatus, DocumentType
from models.document_chunk import ChunkingStrategy, DocumentChunk
from models.embedding import Embedding
from models.user import User
from repositories.embedding_repository import EmbeddingRepository
from repositories.retrieval_repository import RetrievalRepository
from retrieval.vector_store import FAISSVectorStore, chunk_uuid_to_vector_id


def _make_user_document_chunk(db_session, *, dimension: int = 8):
    user = User(email="repo-test@example.com", hashed_password="hashed", full_name="Repo Test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    document = Document(
        owner_id=user.id,
        title="Trees Notes",
        file_name="trees.txt",
        file_path="/tmp/trees.txt",
        file_format=DocumentFormat.TXT,
        document_type=DocumentType.OTHER,
        status=DocumentStatus.CHUNKED,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        chunk_text="A tree is a hierarchical data structure.",
        start_position=0,
        end_position=41,
        token_count=7,
        char_count=41,
        chunking_strategy=ChunkingStrategy.PARAGRAPH,
    )
    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    return user, document, chunk


def test_embedding_repository_get_by_chunk_id(db_session) -> None:
    user, document, chunk = _make_user_document_chunk(db_session)
    embedding = Embedding(
        chunk_id=chunk.id,
        document_id=document.id,
        vector_id=chunk_uuid_to_vector_id(chunk.id),
        embedding_model="fake-model",
        dimension=8,
    )
    EmbeddingRepository(db_session).create(embedding)

    found = EmbeddingRepository(db_session).get_by_chunk_id(chunk.id)
    assert found is not None
    assert found.embedding_model == "fake-model"


def test_embedding_repository_get_by_vector_ids_bulk_lookup(db_session) -> None:
    user, document, chunk = _make_user_document_chunk(db_session)
    vector_id = chunk_uuid_to_vector_id(chunk.id)
    EmbeddingRepository(db_session).create(
        Embedding(chunk_id=chunk.id, document_id=document.id, vector_id=vector_id, embedding_model="m", dimension=8)
    )

    results = EmbeddingRepository(db_session).get_by_vector_ids([vector_id, 999999])
    assert len(results) == 1
    assert results[0].chunk_id == chunk.id


def test_embedding_repository_delete_for_document_removes_all(db_session) -> None:
    user, document, chunk = _make_user_document_chunk(db_session)
    repo = EmbeddingRepository(db_session)
    repo.create(
        Embedding(
            chunk_id=chunk.id,
            document_id=document.id,
            vector_id=chunk_uuid_to_vector_id(chunk.id),
            embedding_model="m",
            dimension=8,
        )
    )
    assert len(repo.list_for_document(document.id)) == 1

    repo.delete_for_document(document.id)
    assert len(repo.list_for_document(document.id)) == 0


def test_retrieval_repository_vector_search_resolves_full_chain(db_session, tmp_path) -> None:
    user, document, chunk = _make_user_document_chunk(db_session)
    vector_id = chunk_uuid_to_vector_id(chunk.id)

    vector_store = FAISSVectorStore(dimension=8, embedding_model="fake", storage_dir=str(tmp_path))
    rng = np.random.default_rng(1)
    vector = rng.normal(size=8).astype(np.float32)
    vector /= np.linalg.norm(vector)
    vector_store.add_vectors(np.array([vector_id], dtype=np.int64), vector.reshape(1, -1))

    EmbeddingRepository(db_session).create(
        Embedding(chunk_id=chunk.id, document_id=document.id, vector_id=vector_id, embedding_model="fake", dimension=8)
    )

    retrieval_repo = RetrievalRepository(db_session, vector_store)
    results = retrieval_repo.vector_search(vector, top_k=5, owner_id=user.id)

    assert len(results) == 1
    found_chunk, found_document, score = results[0]
    assert found_chunk.id == chunk.id
    assert found_document.id == document.id
    assert score == pytest.approx(1.0, abs=1e-4)


def test_retrieval_repository_filters_out_other_users_documents(db_session, tmp_path) -> None:
    user, document, chunk = _make_user_document_chunk(db_session)
    vector_id = chunk_uuid_to_vector_id(chunk.id)

    vector_store = FAISSVectorStore(dimension=8, embedding_model="fake", storage_dir=str(tmp_path))
    rng = np.random.default_rng(2)
    vector = rng.normal(size=8).astype(np.float32)
    vector /= np.linalg.norm(vector)
    vector_store.add_vectors(np.array([vector_id], dtype=np.int64), vector.reshape(1, -1))
    EmbeddingRepository(db_session).create(
        Embedding(chunk_id=chunk.id, document_id=document.id, vector_id=vector_id, embedding_model="fake", dimension=8)
    )

    retrieval_repo = RetrievalRepository(db_session, vector_store)
    other_user_id = uuid.uuid4()
    results = retrieval_repo.vector_search(vector, top_k=5, owner_id=other_user_id)
    assert results == []


def test_retrieval_repository_get_embedding_stats(db_session, tmp_path) -> None:
    user, document, chunk = _make_user_document_chunk(db_session)
    vector_store = FAISSVectorStore(dimension=8, embedding_model="fake", storage_dir=str(tmp_path))
    retrieval_repo = RetrievalRepository(db_session, vector_store)

    stats_before = retrieval_repo.get_embedding_stats_for_document(document.id)
    assert stats_before["chunk_count"] == 1
    assert stats_before["embedded_chunk_count"] == 0
    assert stats_before["is_fully_embedded"] is False

    EmbeddingRepository(db_session).create(
        Embedding(
            chunk_id=chunk.id,
            document_id=document.id,
            vector_id=chunk_uuid_to_vector_id(chunk.id),
            embedding_model="fake",
            dimension=8,
        )
    )
    stats_after = retrieval_repo.get_embedding_stats_for_document(document.id)
    assert stats_after["is_fully_embedded"] is True
