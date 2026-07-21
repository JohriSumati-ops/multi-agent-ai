"""
tests/test_vector_store.py

Pure NumPy/FAISS tests — no embedding model, no database. Covers index
creation, add/search/remove, persistence round-trips, and the corruption
and dimension-mismatch recovery paths.
"""

from __future__ import annotations

import uuid

import numpy as np
import pytest

from core.exceptions import VectorStoreError
from retrieval.vector_store import FAISSVectorStore, chunk_uuid_to_vector_id


def _random_unit_vectors(n: int, dim: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vectors = rng.normal(size=(n, dim)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors


def test_chunk_uuid_to_vector_id_is_deterministic() -> None:
    cid = uuid.uuid4()
    assert chunk_uuid_to_vector_id(cid) == chunk_uuid_to_vector_id(cid)


def test_chunk_uuid_to_vector_id_fits_int64() -> None:
    for _ in range(20):
        vector_id = chunk_uuid_to_vector_id(uuid.uuid4())
        assert 0 <= vector_id < 2**63


def test_new_store_starts_empty(tmp_path) -> None:
    store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=str(tmp_path))
    assert store.ntotal == 0


def test_search_on_empty_index_returns_empty_arrays(tmp_path) -> None:
    store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=str(tmp_path))
    scores, ids = store.search(np.ones(8, dtype=np.float32), top_k=5)
    assert len(scores) == 0
    assert len(ids) == 0


def test_add_and_search_returns_self_as_top_match(tmp_path) -> None:
    store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=str(tmp_path))
    vectors = _random_unit_vectors(5, 8)
    ids = np.array([1000 + i for i in range(5)], dtype=np.int64)
    store.add_vectors(ids, vectors)

    scores, result_ids = store.search(vectors[2], top_k=1)
    assert result_ids[0] == ids[2]
    assert scores[0] == pytest.approx(1.0, abs=1e-4)


def test_search_respects_top_k(tmp_path) -> None:
    store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=str(tmp_path))
    vectors = _random_unit_vectors(10, 8)
    ids = np.arange(10, dtype=np.int64)
    store.add_vectors(ids, vectors)

    scores, result_ids = store.search(vectors[0], top_k=3)
    assert len(result_ids) == 3


def test_add_vectors_rejects_wrong_dimension(tmp_path) -> None:
    store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=str(tmp_path))
    wrong_dim_vectors = np.ones((2, 4), dtype=np.float32)
    with pytest.raises(VectorStoreError):
        store.add_vectors(np.array([1, 2], dtype=np.int64), wrong_dim_vectors)


def test_remove_vectors_decreases_count(tmp_path) -> None:
    store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=str(tmp_path))
    vectors = _random_unit_vectors(5, 8)
    ids = np.arange(5, dtype=np.int64)
    store.add_vectors(ids, vectors)

    removed = store.remove_vectors(np.array([2], dtype=np.int64))
    assert removed == 1
    assert store.ntotal == 4


def test_save_and_load_round_trip(tmp_path) -> None:
    storage_dir = str(tmp_path)
    store = FAISSVectorStore(dimension=8, embedding_model="test-model", storage_dir=storage_dir)
    vectors = _random_unit_vectors(3, 8)
    ids = np.array([10, 20, 30], dtype=np.int64)
    store.add_vectors(ids, vectors)
    store.save()

    reloaded = FAISSVectorStore(dimension=8, embedding_model="test-model", storage_dir=storage_dir)
    reloaded.load()
    assert reloaded.ntotal == 3

    scores, result_ids = reloaded.search(vectors[1], top_k=1)
    assert result_ids[0] == ids[1]


def test_load_with_no_persisted_files_stays_empty(tmp_path) -> None:
    store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=str(tmp_path))
    store.load()
    assert store.ntotal == 0


def test_load_recovers_gracefully_from_corrupted_index_file(tmp_path) -> None:
    storage_dir = str(tmp_path)
    store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=storage_dir)
    store.add_vectors(np.array([1], dtype=np.int64), _random_unit_vectors(1, 8))
    store.save()

    # Corrupt the index file in place.
    with open(store._index_path(), "w") as f:
        f.write("not a valid faiss index")

    recovered_store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=storage_dir)
    recovered_store.load()  # must not raise
    assert recovered_store.ntotal == 0


def test_load_recovers_gracefully_from_dimension_mismatch(tmp_path) -> None:
    storage_dir = str(tmp_path)
    store = FAISSVectorStore(dimension=8, embedding_model="model-a", storage_dir=storage_dir)
    store.add_vectors(np.array([1], dtype=np.int64), _random_unit_vectors(1, 8))
    store.save()

    mismatched_store = FAISSVectorStore(dimension=16, embedding_model="model-a", storage_dir=storage_dir)
    mismatched_store.load()  # must not raise, must not try to use the 8-dim index
    assert mismatched_store.ntotal == 0


def test_load_recovers_gracefully_from_model_name_mismatch(tmp_path) -> None:
    storage_dir = str(tmp_path)
    store = FAISSVectorStore(dimension=8, embedding_model="model-a", storage_dir=storage_dir)
    store.add_vectors(np.array([1], dtype=np.int64), _random_unit_vectors(1, 8))
    store.save()

    mismatched_store = FAISSVectorStore(dimension=8, embedding_model="model-b", storage_dir=storage_dir)
    mismatched_store.load()
    assert mismatched_store.ntotal == 0


def test_rebuild_empty_clears_the_index(tmp_path) -> None:
    store = FAISSVectorStore(dimension=8, embedding_model="test", storage_dir=str(tmp_path))
    store.add_vectors(np.array([1, 2], dtype=np.int64), _random_unit_vectors(2, 8))
    assert store.ntotal == 2

    store.rebuild_empty()
    assert store.ntotal == 0
