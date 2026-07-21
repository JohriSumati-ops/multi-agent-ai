"""
retrieval/vector_store.py — THE VECTOR STORE

WHY THIS FILE EXISTS
---------------------
This is the one file in the whole codebase allowed to import `faiss`
directly — every other module (the retrieval repository, the semantic
search service) talks to it through this class's methods, never to FAISS's
own API. This is the Repository Pattern's exact same rationale (Phase 1),
applied to a non-SQL data store: if FAISS is ever replaced (Milvus, Qdrant,
a different FAISS index type), this is the only file that changes.

INDEX TYPE: WHY IndexFlatIP + IndexIDMap
---------------------------------------------
See docs/Phase3.md Sections 7 and 9 for the full reasoning. In short:
`IndexFlatIP` gives exact (non-approximate) inner-product search, which
equals cosine similarity because every vector this project stores is
L2-normalized before it arrives here (see retrieval/embedder.py).
`IndexIDMap` wraps it so vectors can be addressed and removed by an
explicit 64-bit ID instead of FAISS's default insertion-order position —
without this wrapper, deleting a document's chunks would require rebuilding
the entire index.

VECTOR ID DERIVATION
------------------------
FAISS IDs here are derived deterministically from a chunk's UUID:
`vector_id = uuid.int % (2**63 - 1)`. This means the mapping never needs a
separate counter file to stay in sync with the database — the ID is always
re-derivable from the UUID alone. The collision probability at this
project's realistic scale (a personal document library — hundreds to low
thousands of chunks, not billions) is negligible enough to not warrant the
complexity of collision detection; `EmbeddingRepository`'s
`UniqueConstraint("vector_id")` (see models/embedding.py) would surface a
collision loudly via a database integrity error rather than silently
corrupting data, if one ever did occur.

PERSISTENCE FORMAT
----------------------
Two files live in `settings.VECTOR_STORE_URL`:
- `index.faiss` — the raw FAISS index, written via `faiss.write_index`.
- `index_metadata.json` — a sidecar describing the index: embedding model
  name, dimension, vector count, and a schema version number, used both
  for basic sanity-checking on load and for future migration logic.

CORRUPTION RECOVERY
-----------------------
If the index file is missing, unreadable, or its metadata doesn't match
the currently configured embedding model/dimension, `load()` logs a
warning and starts a fresh empty index rather than crashing the
application on startup — an empty, rebuildable index is always preferable
to an application that won't boot. `POST /retrieval/rebuild` (the API
layer) is the operator-facing recovery path that repopulates it from the
database's `Embedding` rows... except vectors themselves are NOT stored in
the database (only in FAISS) — see that endpoint's docstring for how
rebuild actually re-derives vectors by re-embedding chunk text, since a
truly corrupted FAISS file means the vectors are genuinely gone and must
be recomputed, not just re-indexed.

THREAD SAFETY
-----------------
A single `threading.Lock` guards every mutating operation (add, remove,
save). FAISS's Python bindings are not documented as thread-safe for
concurrent writes, and this project's request-handling threads (see
docs/Phase2.md's StaticPool writeup) are exactly the kind of concurrent
callers this lock protects against.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import faiss
import numpy as np

from core.exceptions import VectorStoreError
from core.logging import get_logger

logger = get_logger("agent")

INDEX_SCHEMA_VERSION = 1
INDEX_FILENAME = "index.faiss"
METADATA_FILENAME = "index_metadata.json"

# FAISS IDs must fit in a signed 64-bit integer.
_ID_MASK = (2**63) - 1


def chunk_uuid_to_vector_id(chunk_id: uuid.UUID) -> int:
    """Deterministically derive a FAISS-compatible int64 ID from a chunk's UUID."""
    return chunk_id.int % _ID_MASK


@dataclass
class IndexMetadata:
    schema_version: int
    embedding_model: str
    dimension: int
    vector_count: int
    created_at: str
    updated_at: str


class FAISSVectorStore:
    """
    Wraps a single FAISS `IndexIDMap(IndexFlatIP)` with persistence and
    incremental update support.

    One instance corresponds to one embedding model/dimension — mixing
    vectors from two different models in one index would make similarity
    scores meaningless, which is why `dimension` is fixed at construction
    and enforced on every `add_vectors` call.
    """

    def __init__(self, dimension: int, embedding_model: str, storage_dir: str) -> None:
        self.dimension = dimension
        self.embedding_model = embedding_model
        self.storage_dir = storage_dir
        self._lock = threading.Lock()
        self._index = self._new_empty_index()
        self._metadata: IndexMetadata | None = None

    def _new_empty_index(self) -> faiss.Index:
        return faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))

    # ------------------------------------------------------------------ #
    # Mutation
    # ------------------------------------------------------------------ #
    def add_vectors(self, vector_ids: np.ndarray, vectors: np.ndarray) -> None:
        """
        Add vectors under explicit IDs. Adding an ID that already exists in
        the index does NOT overwrite it (FAISS's IndexIDMap allows duplicate
        IDs) — callers that need "replace" semantics (e.g., re-embedding a
        document) must call `remove_vectors` first, which
        `services/document_service.py`'s reindex path does.
        """
        if vectors.shape[0] == 0:
            return
        if vectors.shape[1] != self.dimension:
            raise VectorStoreError(
                f"Vector dimension {vectors.shape[1]} does not match index dimension {self.dimension}"
            )
        with self._lock:
            self._index.add_with_ids(vectors.astype(np.float32), vector_ids.astype(np.int64))
        logger.info("Added %d vectors to FAISS index (total now %d)", vectors.shape[0], self._index.ntotal)

    def remove_vectors(self, vector_ids: np.ndarray) -> int:
        """Remove vectors by ID. Returns the number of vectors actually removed."""
        if vector_ids.shape[0] == 0:
            return 0
        with self._lock:
            selector = faiss.IDSelectorBatch(vector_ids.astype(np.int64))
            removed = self._index.remove_ids(selector)
        logger.info("Removed %d vectors from FAISS index (total now %d)", removed, self._index.ntotal)
        return removed

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    def search(self, query_vector: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        """
        Search for the `top_k` nearest vectors to `query_vector`.

        Returns `(scores, vector_ids)`, both shape `(top_k,)`, sorted by
        descending similarity. Empty-index searches return empty arrays
        rather than raising — an empty result set is a valid, expected
        outcome for a fresh installation with no documents yet.
        """
        if self._index.ntotal == 0:
            return np.array([], dtype=np.float32), np.array([], dtype=np.int64)

        query = query_vector.astype(np.float32).reshape(1, -1)
        if query.shape[1] != self.dimension:
            raise VectorStoreError(
                f"Query vector dimension {query.shape[1]} does not match index dimension {self.dimension}"
            )

        k = min(top_k, self._index.ntotal)
        with self._lock:
            scores, ids = self._index.search(query, k)

        scores, ids = scores[0], ids[0]
        # FAISS pads with -1 IDs if fewer than k results exist; filter those out.
        valid = ids != -1
        return scores[valid], ids[valid]

    @property
    def ntotal(self) -> int:
        return self._index.ntotal

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _index_path(self) -> str:
        return os.path.join(self.storage_dir, INDEX_FILENAME)

    def _metadata_path(self) -> str:
        return os.path.join(self.storage_dir, METADATA_FILENAME)

    def save(self) -> None:
        os.makedirs(self.storage_dir, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            faiss.write_index(self._index, self._index_path())
            metadata = IndexMetadata(
                schema_version=INDEX_SCHEMA_VERSION,
                embedding_model=self.embedding_model,
                dimension=self.dimension,
                vector_count=self._index.ntotal,
                created_at=(self._metadata.created_at if self._metadata else now),
                updated_at=now,
            )
            with open(self._metadata_path(), "w") as f:
                json.dump(asdict(metadata), f, indent=2)
            self._metadata = metadata
        logger.info("Saved FAISS index (%d vectors) to %s", self.ntotal, self.storage_dir)

    def load(self) -> None:
        """
        Load a persisted index. On any failure — missing files, an
        unreadable/corrupted index file, or a metadata mismatch against
        this instance's configured model/dimension — logs a warning and
        resets to a fresh empty index rather than raising. See module
        docstring's "Corruption Recovery" section for why this is the
        correct default behavior for an application startup path.
        """
        index_path, metadata_path = self._index_path(), self._metadata_path()

        if not (os.path.exists(index_path) and os.path.exists(metadata_path)):
            logger.info("No persisted FAISS index found at %s — starting with an empty index.", self.storage_dir)
            return

        try:
            with open(metadata_path) as f:
                raw_metadata = json.load(f)
            metadata = IndexMetadata(**raw_metadata)

            if metadata.dimension != self.dimension or metadata.embedding_model != self.embedding_model:
                logger.warning(
                    "Persisted index metadata (model=%s, dim=%d) does not match the currently "
                    "configured model (model=%s, dim=%d) — starting with an empty index. "
                    "Run POST /retrieval/rebuild to re-populate it.",
                    metadata.embedding_model,
                    metadata.dimension,
                    self.embedding_model,
                    self.dimension,
                )
                return

            loaded_index = faiss.read_index(index_path)
        except Exception:
            logger.exception(
                "Failed to load FAISS index from %s — starting with an empty index. "
                "Run POST /retrieval/rebuild to recover.",
                self.storage_dir,
            )
            return

        with self._lock:
            self._index = loaded_index
            self._metadata = metadata
        logger.info("Loaded FAISS index (%d vectors) from %s", self.ntotal, self.storage_dir)

    def rebuild_empty(self) -> None:
        """Discard the current in-memory index and start fresh — used by POST /retrieval/rebuild."""
        with self._lock:
            self._index = self._new_empty_index()
            self._metadata = None
        logger.info("FAISS index reset to empty (dimension=%d)", self.dimension)


# --------------------------------------------------------------------- #
# Process-wide singleton, mirroring retrieval/embedder.py::EmbeddingService's
# pattern — one loaded FAISS index shared by every service/repository,
# rather than each opening/loading its own copy of the persisted files.
# --------------------------------------------------------------------- #
_instance: FAISSVectorStore | None = None
_instance_lock = threading.Lock()


def get_vector_store(dimension: int | None = None, embedding_model: str | None = None) -> FAISSVectorStore:
    """
    Returns the process-wide `FAISSVectorStore` singleton, constructing
    and loading it on first call. `dimension`/`embedding_model` are only
    used on the first call (see EmbeddingService.get_instance's identical
    rationale) — primarily for tests, which construct the singleton with a
    small fake dimension rather than the real model's 384.
    """
    global _instance
    if _instance is not None:
        return _instance
    with _instance_lock:
        if _instance is None:
            from core.config import settings
            from retrieval.embedder import EmbeddingService

            resolved_dimension = dimension or EmbeddingService.get_instance().dimension
            resolved_model = embedding_model or settings.EMBEDDING_MODEL_NAME
            store = FAISSVectorStore(
                dimension=resolved_dimension,
                embedding_model=resolved_model,
                storage_dir=settings.VECTOR_STORE_URL,
            )
            store.load()
            _instance = store
    return _instance


def reset_vector_store() -> None:
    """Test-only: clears the singleton so the next get_vector_store() rebuilds it."""
    global _instance
    with _instance_lock:
        _instance = None
