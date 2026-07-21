"""
retrieval/ranking.py — RANKING & EXPLAINABILITY

WHY THIS FILE EXISTS
---------------------
FAISS returns raw (score, vector_id) pairs — the mechanical part of
retrieval. This module turns that into what a caller actually wants: a
ranked, deduplicated, threshold-filtered list of `RankedResult` objects
that populate the Confidence/Explainability fields Phase 1 defined and
left unused (`schemas/agent_response.py`, `schemas/explainability.py`).

WHY DEDUPLICATION AND GROUPING MATTER HERE SPECIFICALLY
--------------------------------------------------------------
Because Phase 2's chunking strategies can produce overlapping chunks
(sliding window, deliberately — see docs/Phase2.md), the same underlying
sentence can appear near-verbatim in two adjacent chunks. Without
deduplication, a single highly-relevant passage could occupy 3 of a 5-slot
top-K result list, crowding out genuinely different relevant content. This
module's dedup step collapses near-identical chunk text (by normalized
text hash) before ranking, keeping only the highest-scoring occurrence.

EXPLAINABILITY, CONCRETELY
------------------------------
Every `RankedResult` carries a human-readable `reason` string generated
here — never left to the caller to construct — so the explanation logic
lives in exactly one place and stays consistent across every endpoint that
uses it (`/retrieval/search`, `/retrieval/similar`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from document_processing.text_cleaner import normalize_whitespace


@dataclass
class RetrievalCandidate:
    """Raw input to the ranking step — one FAISS hit, joined with its DB metadata."""

    chunk_id: str
    document_id: str
    document_title: str
    chunk_text: str
    page_number: int | None
    chunk_index: int
    similarity_score: float


@dataclass
class RankedResult:
    """Fully explainable, ranked retrieval result — what every retrieval API returns."""

    rank: int
    chunk_id: str
    document_id: str
    document_title: str
    chunk_text: str
    page_number: int | None
    chunk_index: int
    similarity_score: float
    confidence: float
    reason: str


def _normalize_for_dedup(text: str) -> str:
    """Collapse whitespace/case differences so near-identical chunks hash the same."""
    return normalize_whitespace(text).lower().strip()


def deduplicate_candidates(candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
    """
    Collapse candidates with identical (normalized) text, keeping only the
    highest-scoring occurrence of each. Order of the *input* list does not
    matter — the highest scorer always wins regardless of position.
    """
    best_by_text: dict[str, RetrievalCandidate] = {}
    for candidate in candidates:
        key = _normalize_for_dedup(candidate.chunk_text)
        existing = best_by_text.get(key)
        if existing is None or candidate.similarity_score > existing.similarity_score:
            best_by_text[key] = candidate
    return list(best_by_text.values())


def _build_reason(candidate: RetrievalCandidate) -> str:
    """
    Constructs a plain-language explanation for why this chunk was
    retrieved. Deliberately references the concrete score, not just a
    qualitative label — see schemas/explainability.py's rationale for
    preferring structured, traceable data over vague language.
    """
    page_note = f" (page {candidate.page_number})" if candidate.page_number else ""
    return (
        f"Matched chunk {candidate.chunk_index} of '{candidate.document_title}'{page_note} "
        f"with a cosine similarity of {candidate.similarity_score:.3f} to the query."
    )


def rank_candidates(
    candidates: list[RetrievalCandidate],
    *,
    top_k: int,
    similarity_threshold: float = 0.0,
    deduplicate: bool = True,
) -> list[RankedResult]:
    """
    The full ranking pipeline: optional deduplication -> threshold filter
    -> sort by score descending -> truncate to top_k -> attach rank,
    confidence, and an explanation to each surviving candidate.

    `confidence` is currently set equal to `similarity_score` (both are
    already 0.0-1.0 for L2-normalized cosine similarity) — kept as a
    separate field rather than aliased, per schemas/agent_response.py's
    `AgentResult` precedent, so a future ranking refinement (e.g., boosting
    confidence for results appearing in multiple chunks of the same
    document) can diverge from the raw score without a schema change.
    """
    pool = deduplicate_candidates(candidates) if deduplicate else list(candidates)
    filtered = [c for c in pool if c.similarity_score >= similarity_threshold]
    filtered.sort(key=lambda c: c.similarity_score, reverse=True)
    top = filtered[:top_k]

    return [
        RankedResult(
            rank=i + 1,
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_title=c.document_title,
            chunk_text=c.chunk_text,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            similarity_score=c.similarity_score,
            confidence=c.similarity_score,
            reason=_build_reason(c),
        )
        for i, c in enumerate(top)
    ]


@dataclass
class DocumentGroup:
    """One document's worth of ranked results, grouped for a document-centric view."""

    document_id: str
    document_title: str
    results: list[RankedResult] = field(default_factory=list)
    best_score: float = 0.0


def group_by_document(results: list[RankedResult]) -> list[DocumentGroup]:
    """
    Groups a flat ranked-result list by source document — used by callers
    that want "which documents are relevant" rather than "which chunks are
    relevant" (e.g., a future Document Library relevance view). Groups are
    sorted by their best-scoring chunk, descending.
    """
    groups: dict[str, DocumentGroup] = {}
    for result in results:
        group = groups.get(result.document_id)
        if group is None:
            group = DocumentGroup(document_id=result.document_id, document_title=result.document_title)
            groups[result.document_id] = group
        group.results.append(result)
        group.best_score = max(group.best_score, result.similarity_score)

    return sorted(groups.values(), key=lambda g: g.best_score, reverse=True)
