"""
tests/fakes.py

WHY THIS FILE EXISTS
---------------------
`retrieval/embedder.py::EmbeddingService` depends on the `EmbeddingBackend`
interface, not on `sentence_transformers.SentenceTransformer` directly
(see that module's docstring for the full rationale). `FakeEmbeddingBackend`
is the test-only implementation of that interface: deterministic,
dependency-free, and fast, so the entire Phase 3 test suite (caching,
batching, FAISS integration, ranking, the API layer) can run without
downloading or loading a real transformer model.

DETERMINISM
--------------
Each text is hashed (SHA-256) and the hash bytes are used to seed a NumPy
random generator, producing a reproducible pseudo-random unit vector for
that exact text. This gives the fake backend a property real embeddings
also have — identical input always produces identical output — which is
what several cache-behavior tests rely on, without needing the vectors to
carry any real semantic meaning.
"""

from __future__ import annotations

import hashlib

import numpy as np

FAKE_EMBEDDING_DIMENSION = 32


class FakeEmbeddingBackend:
    """Deterministic, dependency-free stand-in for a real embedding model."""

    def __init__(self, dimension: int = FAKE_EMBEDDING_DIMENSION) -> None:
        self.dimension = dimension
        self.encode_call_count = 0
        self.total_texts_encoded = 0

    def encode(self, texts: list[str]) -> np.ndarray:
        self.encode_call_count += 1
        self.total_texts_encoded += len(texts)

        vectors = np.empty((len(texts), self.dimension), dtype=np.float32)
        for i, text in enumerate(texts):
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(digest[:8], byteorder="big", signed=False)
            rng = np.random.default_rng(seed)
            vector = rng.normal(size=self.dimension).astype(np.float32)
            vector /= np.linalg.norm(vector)  # L2-normalize, matching the real backend's behavior
            vectors[i] = vector
        return vectors
