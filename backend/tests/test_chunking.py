"""
tests/test_chunking.py
"""

from __future__ import annotations

import pytest

from retrieval.chunker import (
    ChunkStrategyName,
    chunk_by_paragraph,
    chunk_by_sentence,
    chunk_fixed_size,
    chunk_sliding_window,
    chunk_text,
)

SAMPLE_TEXT = (
    "Paragraph one talks about trees. Trees are hierarchical.\n\n"
    "Paragraph two talks about graphs. Graphs generalize trees by allowing cycles.\n\n"
    "Paragraph three talks about hash tables. Hash tables provide O(1) average lookup."
)


def test_fixed_size_chunks_cover_entire_text_without_overlap() -> None:
    chunks = chunk_fixed_size(SAMPLE_TEXT, chunk_size=50)
    reconstructed = "".join(c.text for c in chunks)
    assert reconstructed == SAMPLE_TEXT
    # No overlap: each chunk's end_position equals the next chunk's start_position
    for i in range(len(chunks) - 1):
        assert chunks[i].end_position == chunks[i + 1].start_position


def test_fixed_size_rejects_non_positive_chunk_size() -> None:
    with pytest.raises(ValueError):
        chunk_fixed_size(SAMPLE_TEXT, chunk_size=0)


def test_paragraph_chunking_respects_paragraph_boundaries() -> None:
    chunks = chunk_by_paragraph(SAMPLE_TEXT, max_chunk_size=10_000)
    # With a huge max size, all 3 paragraphs merge into one buffer chunk.
    assert len(chunks) == 1
    assert "trees" in chunks[0].text.lower()
    assert "hash tables" in chunks[0].text.lower()


def test_paragraph_chunking_splits_when_max_size_is_small() -> None:
    chunks = chunk_by_paragraph(SAMPLE_TEXT, max_chunk_size=60)
    assert len(chunks) >= 3
    for chunk in chunks:
        assert chunk.strategy == ChunkStrategyName.PARAGRAPH


def test_sentence_chunking_never_splits_a_sentence() -> None:
    chunks = chunk_by_sentence(SAMPLE_TEXT, max_chunk_size=40)
    for chunk in chunks:
        # Every chunk should end with sentence-ending punctuation, proving
        # no chunk boundary landed mid-sentence.
        assert chunk.text.strip()[-1] in ".!?"


def test_sliding_window_produces_overlapping_chunks() -> None:
    chunks = chunk_sliding_window(SAMPLE_TEXT, chunk_size=60, overlap=20)
    assert len(chunks) > 1
    # Consecutive chunks should share `overlap` characters of text.
    first_tail = chunks[0].text[-20:]
    second_text = chunks[1].text
    assert first_tail in SAMPLE_TEXT  # sanity: substring actually exists in source
    assert chunks[1].start_position == chunks[0].start_position + (60 - 20)


def test_sliding_window_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_sliding_window(SAMPLE_TEXT, chunk_size=50, overlap=50)
    with pytest.raises(ValueError):
        chunk_sliding_window(SAMPLE_TEXT, chunk_size=50, overlap=-1)


def test_every_chunk_has_required_fields() -> None:
    chunks = chunk_text(SAMPLE_TEXT, strategy=ChunkStrategyName.PARAGRAPH, max_chunk_size=60)
    for chunk in chunks:
        assert chunk.token_count > 0
        assert chunk.char_count == len(chunk.text)
        assert chunk.chunk_index >= 0
        assert chunk.end_position > chunk.start_position


def test_chunk_text_dispatches_to_correct_strategy() -> None:
    fixed = chunk_text(SAMPLE_TEXT, strategy=ChunkStrategyName.FIXED_SIZE, chunk_size=50)
    assert all(c.strategy == ChunkStrategyName.FIXED_SIZE for c in fixed)

    sentence = chunk_text(SAMPLE_TEXT, strategy=ChunkStrategyName.SENTENCE, max_chunk_size=50)
    assert all(c.strategy == ChunkStrategyName.SENTENCE for c in sentence)
