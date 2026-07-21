"""
tests/test_ranking.py
"""

from __future__ import annotations

from retrieval.ranking import RetrievalCandidate, deduplicate_candidates, group_by_document, rank_candidates


def _candidate(chunk_id, doc_id, title, text, score, page=None, index=0):
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=doc_id,
        document_title=title,
        chunk_text=text,
        page_number=page,
        chunk_index=index,
        similarity_score=score,
    )


def test_rank_candidates_sorts_by_score_descending() -> None:
    candidates = [
        _candidate("c1", "d1", "Doc", "text a", 0.5),
        _candidate("c2", "d1", "Doc", "text b", 0.9),
        _candidate("c3", "d1", "Doc", "text c", 0.7),
    ]
    results = rank_candidates(candidates, top_k=10, similarity_threshold=0.0)
    assert [r.chunk_id for r in results] == ["c2", "c3", "c1"]
    assert [r.rank for r in results] == [1, 2, 3]


def test_rank_candidates_respects_top_k() -> None:
    candidates = [_candidate(f"c{i}", "d1", "Doc", f"text {i}", score=i / 10) for i in range(10)]
    results = rank_candidates(candidates, top_k=3, similarity_threshold=0.0)
    assert len(results) == 3


def test_rank_candidates_filters_by_threshold() -> None:
    candidates = [
        _candidate("c1", "d1", "Doc", "high relevance text", 0.8),
        _candidate("c2", "d1", "Doc", "low relevance text", 0.1),
    ]
    results = rank_candidates(candidates, top_k=10, similarity_threshold=0.5)
    assert len(results) == 1
    assert results[0].chunk_id == "c1"


def test_deduplicate_candidates_keeps_highest_scorer() -> None:
    candidates = [
        _candidate("c1", "d1", "Doc", "  Identical   text.  ", 0.6),
        _candidate("c2", "d1", "Doc", "Identical text.", 0.9),
    ]
    deduped = deduplicate_candidates(candidates)
    assert len(deduped) == 1
    assert deduped[0].chunk_id == "c2"


def test_deduplicate_candidates_is_case_insensitive() -> None:
    candidates = [
        _candidate("c1", "d1", "Doc", "Binary Trees", 0.5),
        _candidate("c2", "d1", "Doc", "binary trees", 0.7),
    ]
    deduped = deduplicate_candidates(candidates)
    assert len(deduped) == 1
    assert deduped[0].chunk_id == "c2"


def test_rank_candidates_can_disable_deduplication() -> None:
    candidates = [
        _candidate("c1", "d1", "Doc", "same text", 0.6),
        _candidate("c2", "d1", "Doc", "same text", 0.9),
    ]
    results = rank_candidates(candidates, top_k=10, similarity_threshold=0.0, deduplicate=False)
    assert len(results) == 2


def test_ranked_result_includes_explainability_fields() -> None:
    candidates = [_candidate("c1", "d1", "Trees Notes", "some content", 0.777, page=3, index=2)]
    results = rank_candidates(candidates, top_k=1, similarity_threshold=0.0)
    result = results[0]
    assert result.confidence == 0.777
    assert "Trees Notes" in result.reason
    assert "page 3" in result.reason
    assert "0.777" in result.reason


def test_group_by_document_groups_and_sorts_by_best_score() -> None:
    candidates = [
        _candidate("c1", "d1", "Doc A", "text 1", 0.9),
        _candidate("c2", "d1", "Doc A", "text 2", 0.6),
        _candidate("c3", "d2", "Doc B", "text 3", 0.95),
    ]
    results = rank_candidates(candidates, top_k=10, similarity_threshold=0.0)
    groups = group_by_document(results)

    assert groups[0].document_title == "Doc B"  # highest best_score first
    assert groups[1].document_title == "Doc A"
    assert len(groups[1].results) == 2


def test_empty_candidate_list_produces_empty_results() -> None:
    assert rank_candidates([], top_k=5, similarity_threshold=0.0) == []
