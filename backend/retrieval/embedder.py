"""
retrieval/embedder.py — THE EMBEDDING PIPELINE

WHY THIS FILE EXISTS
---------------------
Every future agent or service that needs a text embedding (the Embedding
Agent, the Semantic Search Service, a future Retrieval Agent) must go
through one shared, correctly-configured, singleton model instance — not
each construct its own `SentenceTransformer`, which would multiply memory
usage and load time for no benefit.

ARCHITECTURE: BACKEND ABSTRACTION
--------------------------------------
`EmbeddingBackend` is a narrow interface (`encode(texts) -> np.ndarray`,
plus a `dimension` attribute) that `EmbeddingService` depends on, rather
than depending on `sentence_transformers.SentenceTransformer` directly.
`SentenceTransformerBackend` is the real, production implementation.

This isn't just an abstraction for its own sake: it is what makes
`EmbeddingService`'s caching, batching, thread-safety, and singleton
behavior independently testable without a loaded model at all — see
`tests/fakes.py::FakeEmbeddingBackend`. (This project's build/verification
environment additionally has no network path to the model hub the real
backend downloads weights from — see `docs/Phase3.md` Section 19 — which
made this abstraction necessary in practice, not just in principle. The
interface is the correct design regardless of that constraint.)

DEEP LEARNING CONCEPT
--------------------------
`all-MiniLM-L6-v2` is a distilled sentence-transformer: a smaller model
trained to mimic a larger transformer's output, trading a small amount of
accuracy for a large reduction in inference time and memory — a real,
common production tradeoff (the same idea behind DistilBERT, TinyBERT,
etc.), not specific to this project. See docs/Phase3.md Section 5 for the
full explanation of what happens inside the model.

THREAD SAFETY
-----------------
`get_instance()` uses double-checked locking so concurrent first-callers
(e.g., two simultaneous document uploads at startup) don't each construct
and load their own model instance. The cache is protected by its own lock
since reads/writes can happen from multiple request-handling threads
(FastAPI runs sync code in a thread pool — see docs/Phase2.md's
StaticPool bug writeup for a concrete example of this project already
being bitten by that once).

CACHING
----------
Embeddings are cached by a SHA-256 hash of their exact input text. This
means re-chunking or re-uploading identical source content never pays for
a redundant model inference call — a meaningful cost saving even for local
inference, since transformer forward passes are not free. The cache is a
bounded LRU (`collections.OrderedDict`-based) so memory usage doesn't grow
unbounded over a long-running process.
"""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict
from typing import Protocol

import numpy as np

from core.config import settings
from core.exceptions import EmbeddingGenerationError, InvalidEmbeddingError
from core.logging import get_logger

logger = get_logger("agent")


class EmbeddingBackend(Protocol):
    """The narrow interface EmbeddingService depends on — see module docstring."""

    dimension: int

    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerBackend:
    """
    Production `EmbeddingBackend` backed by a local SentenceTransformers
    model. Local inference only — no network call happens at embed time
    (only at first model load, to download/cache weights).
    """

    def __init__(self, model_name: str) -> None:
        # Imported lazily so importing this module never requires
        # `sentence_transformers` (and its heavy `torch` dependency) to be
        # installed unless this specific backend is actually constructed —
        # tests using `FakeEmbeddingBackend` never pay that import cost.
        from sentence_transformers import SentenceTransformer

        logger.info("Loading SentenceTransformer model '%s' (this may take a moment)...", model_name)
        self._model = SentenceTransformer(model_name)
        self.dimension: int = self._model.get_sentence_embedding_dimension()
        self.model_name = model_name
        logger.info("Model '%s' loaded — embedding dimension = %d", model_name, self.dimension)

    def encode(self, texts: list[str]) -> np.ndarray:
        # normalize_embeddings=True L2-normalizes every output vector,
        # which is what makes cosine similarity reduce to a plain inner
        # product later in the pipeline — see docs/Phase3.md Section 9.
        return self._model.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )


class _LRUCache:
    """Simple thread-safe bounded LRU cache, keyed by content hash -> vector."""

    def __init__(self, max_size: int) -> None:
        self._max_size = max_size
        self._store: OrderedDict[str, np.ndarray] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> np.ndarray | None:
        with self._lock:
            if key not in self._store:
                return None
            self._store.move_to_end(key)
            return self._store[key]

    def put(self, key: str, value: np.ndarray) -> None:
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingService:
    """
    Singleton service wrapping an `EmbeddingBackend` with caching, batching,
    validation, and progress logging.

    Obtained via `EmbeddingService.get_instance()`, never constructed
    directly by callers other than tests (which use `reset_instance()` to
    swap in a `FakeEmbeddingBackend` for isolation).
    """

    _instance: "EmbeddingService | None" = None
    _instance_lock = threading.Lock()

    def __init__(self, backend: EmbeddingBackend, cache_size: int | None = None) -> None:
        self.backend = backend
        self.dimension = backend.dimension
        self._cache = _LRUCache(cache_size or settings.EMBEDDING_CACHE_SIZE)

    @classmethod
    def get_instance(cls, backend: EmbeddingBackend | None = None) -> "EmbeddingService":
        """
        Returns the process-wide singleton, constructing it on first call.

        `backend` is only used on the *first* call (subsequent calls
        ignore it and return the existing singleton) — this is
        intentional: it lets tests pass a `FakeEmbeddingBackend` once at
        the start of a test session via `reset_instance()` + `get_instance(fake)`,
        without every call site needing to know about the test double.
        """
        if cls._instance is not None:
            return cls._instance
        with cls._instance_lock:
            if cls._instance is None:
                resolved_backend = backend or SentenceTransformerBackend(settings.EMBEDDING_MODEL_NAME)
                cls._instance = cls(resolved_backend)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Test-only: clears the singleton so the next get_instance() rebuilds it."""
        with cls._instance_lock:
            cls._instance = None

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        Embed a batch of texts, using the cache for any text seen before
        and only calling the backend for cache misses. Returns an array of
        shape (len(texts), self.dimension), in the same order as `texts`.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        results: list[np.ndarray | None] = [None] * len(texts)
        misses: list[tuple[int, str]] = []

        for i, text in enumerate(texts):
            cached = self._cache.get(_hash_text(text))
            if cached is not None:
                results[i] = cached
            else:
                misses.append((i, text))

        if misses:
            logger.info(
                "Embedding %d texts (%d cache hits, %d cache misses)",
                len(texts),
                len(texts) - len(misses),
                len(misses),
            )
            miss_texts = [t for _, t in misses]
            try:
                vectors = self.backend.encode(miss_texts)
            except Exception as exc:  # noqa: BLE001 — wrap any backend failure uniformly
                raise EmbeddingGenerationError(f"Embedding model failed to encode text: {exc}") from exc

            self._validate_vectors(vectors, expected_count=len(miss_texts))

            for (i, text), vector in zip(misses, vectors, strict=True):
                results[i] = vector
                self._cache.put(_hash_text(text), vector)

        return np.stack(results).astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query string — a thin convenience wrapper over embed_texts."""
        return self.embed_texts([text])[0]

    def _validate_vectors(self, vectors: np.ndarray, *, expected_count: int) -> None:
        """
        Validates the backend's raw output before it enters the cache or
        the vector store — the "Validate vectors" step the Embedding Agent
        (agents/embedding_agent.py) delegates to this method.
        """
        if vectors.shape[0] != expected_count:
            raise InvalidEmbeddingError(
                f"Embedding backend returned {vectors.shape[0]} vectors for {expected_count} inputs"
            )
        if vectors.shape[1] != self.dimension:
            raise InvalidEmbeddingError(
                f"Embedding backend returned dimension {vectors.shape[1]}, expected {self.dimension}"
            )
        if not np.all(np.isfinite(vectors)):
            raise InvalidEmbeddingError("Embedding backend returned NaN or infinite values")

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def clear_cache(self) -> None:
        self._cache.clear()
