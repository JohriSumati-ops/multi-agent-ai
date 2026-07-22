# Phase 3 — Semantic Retrieval Layer

**Status:** Written before implementation, per the mandatory Phase 3 process. Implementation follows in this same document's later sections once code exists (see the "Implementation Verification" section at the end, added after code was written and tested).

---

## 1. Objectives of Phase 3

Phase 2 turned raw files into cleaned, chunked text sitting in
PostgreSQL. That text is readable by a human scrolling through it, but a
computer has no way to answer "which of these 400 chunks, across 30
documents, is actually relevant to *this* question?" without either (a)
reading every chunk with an LLM on every query — slow and expensive — or
(b) keyword matching, which misses paraphrases entirely.

Phase 3's objective is narrow and specific: **build the retrieval layer
that can answer "which chunks are semantically relevant to this query,"
and nothing else.** No reasoning, no synthesis, no answer generation — an
explainable ranked list of chunks, with scores, is the entire output. This
is deliberately positioned as infrastructure that later phases (a
Supervisor, a Reading Agent that reasons over retrieved chunks) will sit
on top of, not infrastructure that reasons itself.

## 2. Why Semantic Search Is Needed

Phase 2 already stores chunk text in a queryable Postgres column — in
principle, `WHERE chunk_text LIKE '%binary search tree%'` "works." It fails
in exactly the cases that matter most for a study tool:

- A user asks "how does a self-balancing tree work?" and the source
  material says "AVL trees maintain balance via rotations" — zero shared
  keywords, same underlying concept.
- Keyword search has no notion of *how relevant* a match is beyond crude
  term-frequency heuristics; it can't rank "mostly about this topic" above
  "mentions this topic once in passing."

## 3. Keyword Search vs. Semantic Search

| | Keyword Search | Semantic Search |
|---|---|---|
| Matches on | Exact/fuzzy token overlap | Meaning, via vector similarity |
| Handles synonyms/paraphrase | No | Yes |
| Handles typos | Only with fuzzy matching add-ons | Reasonably, since meaning is preserved |
| Ranking basis | Term frequency (e.g., BM25) | Distance/similarity in embedding space |
| Needs a model | No | Yes (an embedding model) |
| Interpretability | High — the matched words are visible | Lower — needs an explicit "why" (Section 12) |

Phase 3 implements semantic search only. Hybrid search (combining both) is
explicitly reserved for a future phase — `retrieval/hybrid_search.py` was
named but left unwritten in the Phase 0 architecture doc for exactly this
reason.

## 4. What Embeddings Are

An embedding is a fixed-length vector of real numbers (for the model used
here, 384 numbers) that represents a piece of text's *meaning* as a point
in high-dimensional space. Texts with similar meaning end up as points
that are close together in that space; texts with unrelated meaning end up
far apart. Critically, "close together" is measured mathematically (see
Section 8), which is what makes ranking possible without an LLM reading
anything.

## 5. How Transformer Embedding Models Work (High Level)

The embedding model used here (`all-MiniLM-L6-v2`, a distilled
sentence-transformer built on a transformer encoder) works roughly as
follows:

1. **Tokenization** — text is split into subword tokens (unlike Phase 2's
   whitespace-based approximation — this is a real, model-specific
   tokenizer, exactly the gap Phase 2's documentation flagged as deferred
   to this phase).
2. **Contextual encoding** — each token is passed through several
   transformer layers, where *self-attention* lets every token's
   representation be influenced by every other token in the sequence. This
   is what lets the model tell "bank" (a river bank) apart from "bank" (a
   financial institution) based on surrounding context.
3. **Pooling** — the per-token representations are combined (mean-pooled,
   for this model) into one fixed-length vector representing the whole
   input, regardless of how many tokens it had.
4. **Normalization** — the resulting vector is scaled to unit length
   (L2-normalized), which is what makes cosine similarity and inner-product
   search equivalent (see Section 9).

This model was never fine-tuned on this project's data — it's used
entirely as a pretrained, general-purpose encoder. No training happens in
this phase.

## 6. Why Vector Databases Are Used

A brute-force approach — compute similarity between a query vector and
every stored vector, one at a time — works correctly but scales linearly
with corpus size. A vector database (FAISS, in this phase) exists to make
similarity search fast, and to handle the bookkeeping (persistence, adding
new vectors incrementally, removing vectors for deleted documents) that a
raw list of NumPy arrays doesn't give you for free.

At this project's scale (a personal study tool, not a web-scale search
engine), a brute-force flat index is actually the *correct* choice — see
Section 7 for why — but the same `VectorStore` interface this phase builds
is what would let a larger index type (IVF, HNSW) swap in later without
changing anything above it.

## 7. FAISS Architecture (as used in this phase)

FAISS (Facebook AI Similarity Search) provides multiple index types
trading off speed, memory, and exactness. This phase uses:

- **`IndexFlatIP`** — a flat (brute-force) index using inner product as
  the similarity metric. "Flat" means no approximation — every search
  compares the query against every stored vector, guaranteeing exact
  results. This is the right tradeoff for a corpus of hundreds to low
  thousands of chunks (a personal document library, not a web-scale
  corpus) — approximate indexes (IVF, HNSW) start paying off in accuracy
  vs. speed only at a much larger scale, and add real complexity
  (training, tuning) this project doesn't yet need.
- **`IndexIDMap`** — wraps the flat index to associate each vector with an
  explicit 64-bit integer ID (rather than FAISS's default "position in
  insertion order" addressing), which is what makes both targeted removal
  and a stable mapping back to a specific `DocumentChunk` possible.

## 8. Similarity Search

Given a query vector, FAISS returns the `k` stored vectors with the
highest similarity score, sorted descending, without the caller needing to
implement the comparison loop, sorting, or top-k selection themselves —
that's the entire value FAISS adds at this index type; the numerical
comparison itself is described next.

## 9. Cosine Similarity

Cosine similarity measures the angle between two vectors, ignoring their
magnitude — it is defined as:

```
cosine_similarity(A, B) = (A · B) / (‖A‖ × ‖B‖)
```

Because every embedding produced by this phase's `EmbeddingService` is
L2-normalized (‖A‖ = 1) before being stored or searched, the denominator
becomes 1, and cosine similarity reduces to a plain dot product:

```
cosine_similarity(A, B) = A · B      (when ‖A‖ = ‖B‖ = 1)
```

This is precisely why `IndexFlatIP` (inner product) is used instead of
`IndexFlatL2` (Euclidean distance) — with normalized vectors, inner
product search *is* cosine similarity search, and FAISS's inner-product
index is more efficient than computing Euclidean distance and converting.

## 10. Storage Pipeline

```
DocumentChunk rows (from Phase 2, status=CHUNKED)
        │
        ▼
EmbeddingAgent (BaseAgent subclass)
        │  batches chunk_text -> EmbeddingService.embed_texts()
        ▼
FAISS VectorStore.add_vectors(vector_ids, embeddings)
        │
        ▼
Embedding table row per chunk (vector_id <-> chunk_id <-> document_id mapping)
        │
        ▼
Document.status = READY
```

## 11. Retrieval Pipeline

```
User query (text)
        │
        ▼
SemanticSearchService
        │  EmbeddingService.embed_query()
        ▼
RetrievalRepository.vector_search()  — FAISS top-K by cosine similarity
        │
        ▼
RetrievalRepository metadata lookup  — vector_id -> Embedding -> DocumentChunk -> Document
        │
        ▼
Ranking (retrieval/ranking.py) — threshold filter, dedup, document grouping, explanation
        │
        ▼
SearchResult list (score, rank, document, page, chunk, reason) returned to client
```

## 12. Explainability

No retrieval result is returned without: its raw similarity score, its
rank among the result set, which document and chunk it came from, and a
plain-language reason string (e.g., "Matched because this chunk's content
is semantically similar to your query, with a cosine similarity of 0.82").
This mirrors the Confidence/Explainability frameworks Phase 1 built and
left unused — this is the first phase to populate them for real.

## 13. Folder Modifications

No folder is renamed. Additions only:

```
retrieval/
├── embedder.py       NEW — EmbeddingService, backend abstraction, caching
├── vector_store.py   NEW — FAISS wrapper (create/persist/load/add/remove/recover)
└── ranking.py        NEW — cosine ranking, threshold, dedup, grouping, explanation

agents/
└── embedding_agent.py NEW — first Deep Learning based agent

models/
└── embedding.py       NEW — Embedding table (chunk_id <-> vector_id <-> document_id)

repositories/
├── embedding_repository.py  NEW
└── retrieval_repository.py  NEW — composes FAISS search + DB metadata lookup

services/
└── semantic_search_service.py NEW

schemas/
└── retrieval.py        NEW — SearchRequest/SearchResult/etc.

api/routes/
└── retrieval.py         NEW — 5 endpoints (Section 15)
```

`services/document_service.py` gains one new internal pipeline stage
(embedding, using the already-reserved `EMBEDDING`/`READY`
`DocumentStatus` values from Phase 1) — this is the one existing file
modified, and it was reserved for exactly this purpose since Phase 1.

## 14. New Services, Repositories, Agents

- **`EmbeddingAgent`** (`agents/embedding_agent.py`) — the first Deep
  Learning based agent: receives cleaned chunks, generates embeddings via
  `EmbeddingService`, validates vector shape/finiteness, returns results —
  inherits `BaseAgent` exactly like Phase 2's two agents.
- **`EmbeddingRepository`** / **`RetrievalRepository`** — the former is
  plain CRUD over the `embeddings` table (Repository Pattern, unchanged
  from Phase 1); the latter composes vector search (FAISS, not SQL) with
  metadata lookups (SQL, via the other repositories) behind one interface,
  which is what lets `SemanticSearchService` stay ignorant of FAISS
  entirely.
- **`SemanticSearchService`** — orchestrates query embedding, retrieval,
  and ranking; the only new service in this phase.

## 15. New API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /retrieval/search` | Semantic search by free-text query |
| `POST /retrieval/similar` | "More like this chunk" — search by an existing chunk's vector |
| `GET /retrieval/document/{id}` | Retrieval-relevant metadata for one document (embedding status, chunk/vector counts) |
| `GET /retrieval/chunks/{id}` | A single chunk's stored vector metadata (not the raw vector) |
| `POST /retrieval/reindex` | Re-embed one document (e.g., after a model change) |
| `POST /retrieval/rebuild` | Rebuild the entire FAISS index from the database (corruption recovery / model migration) |

## 16. Testing Strategy

Unit tests for `VectorStore` (index math, persistence, corruption
recovery) need no model at all — pure NumPy vectors suffice. Unit tests for
`EmbeddingService`'s caching/batching/singleton behavior are written
against an injectable `EmbeddingBackend` interface rather than the real
`SentenceTransformer`, specifically so they run in any environment,
including one with no network access to a model hub — see Section 19 for
why this matters concretely in this project's build environment, and why
it's a legitimate design choice independent of that constraint.

## 17. Design Decisions

- **Local inference only, no cloud embedding APIs** — matches the Phase 3
  prompt's explicit constraint and keeps the project runnable offline once
  the model is cached locally.
- **`IndexFlatIP` over an approximate index** — see Section 7.
- **UUID-derived FAISS IDs** rather than an auto-increment counter file —
  `vector_id = chunk_id.int % (2**63 - 1)` is deterministic and needs no
  separate state to stay in sync with the database; the (astronomically
  unlikely, at this project's scale) collision case is documented in
  `vector_store.py`.
- **Singleton embedding model** — loading a transformer model is expensive
  (seconds, real memory); every agent/service needing embeddings shares one
  loaded instance rather than each constructing its own.
- **Embedding cache keyed by content hash** — re-uploading or re-chunking
  the same source text should not force a redundant model inference call.

## 18. Future Extensibility

- The `VectorStore` interface doesn't assume `IndexFlatIP` — swapping to
  an IVF or HNSW index (or a networked engine like Milvus/Qdrant, matching
  Section 11.2/11.3 of the Phase 0 architecture doc's scaling plan) is
  contained to `vector_store.py`.
- `retrieval/hybrid_search.py` and `retrieval/reranker.py` (named but
  unwritten since Phase 0) are the natural next additions — the
  `RetrievalRepository` boundary this phase establishes is exactly where a
  BM25 keyword-search branch would be composed alongside vector search.
- The `EmbeddingBackend` abstraction means a fine-tuned or larger model can
  replace `all-MiniLM-L6-v2` via one config change (`EMBEDDING_MODEL_NAME`),
  without any caller-side code change.

## 19. Implementation Verification Notes (added after implementation)

This build environment's network egress does not include
`huggingface.co`, which is where `sentence-transformers` downloads model
weights from on first use. This means the real `all-MiniLM-L6-v2` model
could not be downloaded or run end-to-end inside this particular sandbox.

This was handled honestly, not silently worked around: `EmbeddingService`
is built against an `EmbeddingBackend` interface (Section 16), with
`SentenceTransformerBackend` as the real production implementation and a
deterministic `FakeEmbeddingBackend` (test-only, living in `tests/fakes.py`)
used to verify every other piece of Phase 3 — caching, batching,
thread-safety, FAISS integration, ranking, the API layer — end to end
without needing the real model weights. The seam between them is a single
constructor argument; no production code path is different because of
this. Anyone running this project with normal internet access gets the
real model with zero code changes. See `docs/Phase3.md`'s testing section
and the final Phase 3 changelog for the full, itemized account of what was
and wasn't run against the real model in this environment.
