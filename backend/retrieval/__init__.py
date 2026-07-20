"""
retrieval/ — CHUNKING (Phase 2) + RESERVED FOR PHASE 3 (search/reranking)

WHY THIS FOLDER EXISTS
--------------------------
This package holds chunking strategy (`chunker.py`, built in Phase 2),
plus embedding orchestration, hybrid (vector + keyword) search, and
reranking -- the "RAG" learning core of the project (see Architecture
Section 3.2 and Section 9's Phase 2/3 learning goals) -- reserved for
Phase 3.

PHASE 2 STATUS: `chunker.py` is implemented -- pure text-splitting logic,
zero embeddings, zero model calls. Chunking is a document-structuring
step, not a retrieval step, which is why it belongs here architecturally
even though it ships in the phase before real retrieval exists.

PHASE 3 STATUS: `hybrid_search.py` and `reranker.py` do not exist yet --
those require embeddings, which Phase 2 explicitly excludes.
"""
