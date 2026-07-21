"""
tests/test_embedding_service.py

Exercises EmbeddingService's caching, batching, singleton, and validation
behavior against `FakeEmbeddingBackend` — see tests/fakes.py and
docs/Phase3.md Section 19 for why the real model isn't used here.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.exceptions import EmbeddingGenerationError, InvalidEmbeddingError
from retrieval.embedder import EmbeddingService, _hash_text
from tests.fakes import FakeEmbeddingBackend


def test_embed_texts_returns_correct_shape() -> None:
    backend = FakeEmbeddingBackend(dimension=16)
    EmbeddingService.reset_instance()
    service = EmbeddingService.get_instance(backend)

    vectors = service.embed_texts(["hello", "world", "foo"])
    assert vectors.shape == (3, 16)


def test_embed_texts_is_deterministic_for_identical_input() -> None:
    backend = FakeEmbeddingBackend()
    EmbeddingService.reset_instance()
    service = EmbeddingService.get_instance(backend)

    v1 = service.embed_query("binary search trees")
    v2 = service.embed_query("binary search trees")
    assert np.allclose(v1, v2)


def test_embed_texts_uses_cache_on_repeated_text() -> None:
    backend = FakeEmbeddingBackend()
    EmbeddingService.reset_instance()
    service = EmbeddingService.get_instance(backend)

    service.embed_texts(["alpha", "beta"])
    assert backend.total_texts_encoded == 2

    service.embed_texts(["alpha", "beta", "gamma"])
    # Only "gamma" should hit the backend the second time.
    assert backend.total_texts_encoded == 3


def test_embed_texts_empty_list_returns_empty_array() -> None:
    backend = FakeEmbeddingBackend(dimension=8)
    EmbeddingService.reset_instance()
    service = EmbeddingService.get_instance(backend)

    result = service.embed_texts([])
    assert result.shape == (0, 8)


def test_get_instance_returns_same_singleton() -> None:
    EmbeddingService.reset_instance()
    service_a = EmbeddingService.get_instance(FakeEmbeddingBackend())
    service_b = EmbeddingService.get_instance(FakeEmbeddingBackend())
    assert service_a is service_b


def test_validate_vectors_rejects_wrong_dimension() -> None:
    backend = FakeEmbeddingBackend(dimension=8)
    EmbeddingService.reset_instance()
    service = EmbeddingService.get_instance(backend)

    bad_vectors = np.ones((1, 4), dtype=np.float32)  # wrong dimension
    with pytest.raises(InvalidEmbeddingError):
        service._validate_vectors(bad_vectors, expected_count=1)


def test_validate_vectors_rejects_non_finite_values() -> None:
    backend = FakeEmbeddingBackend(dimension=4)
    EmbeddingService.reset_instance()
    service = EmbeddingService.get_instance(backend)

    bad_vectors = np.array([[1.0, float("nan"), 0.5, 0.2]], dtype=np.float32)
    with pytest.raises(InvalidEmbeddingError):
        service._validate_vectors(bad_vectors, expected_count=1)


def test_backend_failure_raises_embedding_generation_error() -> None:
    class BrokenBackend:
        dimension = 8

        def encode(self, texts):
            raise RuntimeError("model exploded")

    EmbeddingService.reset_instance()
    service = EmbeddingService.get_instance(BrokenBackend())

    with pytest.raises(EmbeddingGenerationError):
        service.embed_texts(["this will fail"])


def test_cache_size_reports_unique_entries() -> None:
    backend = FakeEmbeddingBackend()
    EmbeddingService.reset_instance()
    service = EmbeddingService.get_instance(backend)

    service.embed_texts(["one", "two", "one"])
    assert service.cache_size == 2


def test_clear_cache_empties_the_cache() -> None:
    backend = FakeEmbeddingBackend()
    EmbeddingService.reset_instance()
    service = EmbeddingService.get_instance(backend)

    service.embed_texts(["one", "two"])
    assert service.cache_size == 2
    service.clear_cache()
    assert service.cache_size == 0


def test_hash_text_is_stable() -> None:
    assert _hash_text("hello") == _hash_text("hello")
    assert _hash_text("hello") != _hash_text("world")
