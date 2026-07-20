"""
retrieval/chunker.py — THE CHUNKING ENGINE

WHY THIS FILE EXISTS
---------------------
Retrieval (Phase 3) operates on chunks, never whole documents — a whole
"Data Structures.pdf" is too large and topically diverse to embed as one
unit and expect similarity search to work well. This module produces those
chunks. It is deliberately embedding-free: chunking is a text-structuring
decision, made using the sentence/paragraph boundaries
`document_processing/nlp_preprocessor.py` already computed — no model
inference happens here.

FOUR STRATEGIES, AND WHY EACH EXISTS
------------------------------------------
1. **Fixed-size** — split into chunks of approximately N characters,
   regardless of sentence/paragraph boundaries. Simplest, most predictable
   chunk-size distribution; used as the baseline every other strategy is
   compared against.
2. **Paragraph** — one chunk per paragraph (or merged small paragraphs up
   to a max size). Preserves the author's own structural units, which
   tends to keep semantically coherent ideas together — usually the best
   default for well-formatted study notes.
3. **Sentence** — groups whole sentences up to a target chunk size, never
   splitting a sentence across two chunks. A middle ground between
   fixed-size's simplicity and paragraph's structure-awareness, useful for
   source material with poor/inconsistent paragraph formatting (common in
   PDF-extracted text).
4. **Sliding window** — fixed-size chunks with deliberate overlap between
   consecutive chunks (e.g., last 20% of chunk N repeated at the start of
   chunk N+1). This is the standard RAG technique for reducing the chance
   that a concept explained right at a chunk boundary gets split so badly
   that neither resulting chunk contains the full idea — directly relevant
   once Phase 3 measures retrieval quality.

NLP CONCEPT USED
---------------------
Chunk boundary selection is fundamentally a tradeoff between "chunk small
enough to be topically focused" and "chunk large enough to contain a
complete idea" — this tradeoff is *the* central design decision in every
production RAG system's ingestion pipeline (Perplexity, NotebookLM, and
enterprise search-over-documents products all expose some version of these
same four strategies, often under different names).

HOW THIS PREPARES FOR PHASE 3
---------------------------------
Every `Chunk` produced here becomes one row in `document_chunks`
(`models/document_chunk.py`). Phase 3's Embedding Agent iterates over
those rows and calls `BaseLLM.embed(chunk.chunk_text)` for each — this
module's output is Phase 3's entire input.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from document_processing.nlp_preprocessor import count_words, segment_paragraphs, segment_sentences


class ChunkStrategyName(str, enum.Enum):
    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class Chunk:
    """
    In-memory chunk representation produced by this module. Mapped 1:1 to
    `models.document_chunk.DocumentChunk` columns by the caller (see
    `services/document_service.py`) — kept as a plain dataclass here so
    chunking logic has zero dependency on the ORM and is trivially unit
    testable.
    """

    text: str
    chunk_index: int
    start_position: int
    end_position: int
    token_count: int
    char_count: int
    strategy: ChunkStrategyName
    page_number: int | None = None
    extra_metadata: dict = field(default_factory=dict)


def _make_chunk(
    text: str,
    *,
    index: int,
    start: int,
    strategy: ChunkStrategyName,
    page_number: int | None = None,
    extra_metadata: dict | None = None,
) -> Chunk:
    return Chunk(
        text=text,
        chunk_index=index,
        start_position=start,
        end_position=start + len(text),
        token_count=count_words(text),
        char_count=len(text),
        strategy=strategy,
        page_number=page_number,
        extra_metadata=extra_metadata or {},
    )


def chunk_fixed_size(text: str, *, chunk_size: int = 1000) -> list[Chunk]:
    """
    Strategy 1: split into non-overlapping chunks of `chunk_size`
    characters. The simplest, most predictable strategy — a good
    default when speed/simplicity matters more than boundary quality.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    chunks: list[Chunk] = []
    for index, start in enumerate(range(0, len(text), chunk_size)):
        piece = text[start : start + chunk_size]
        if piece.strip():
            chunks.append(_make_chunk(piece, index=index, start=start, strategy=ChunkStrategyName.FIXED_SIZE))
    return chunks


def chunk_by_paragraph(text: str, *, max_chunk_size: int = 1500) -> list[Chunk]:
    """
    Strategy 2: one chunk per paragraph, merging consecutive small
    paragraphs together up to `max_chunk_size` so very short paragraphs
    (a lone heading, a one-line note) don't each become their own
    near-empty chunk.
    """
    paragraphs = segment_paragraphs(text)
    chunks: list[Chunk] = []
    buffer = ""
    buffer_start = 0
    index = 0
    cursor = 0

    for paragraph in paragraphs:
        # Locate this paragraph's real offset in the original text so
        # start/end positions are meaningful for citation purposes.
        found_at = text.find(paragraph, cursor)
        if found_at == -1:
            found_at = cursor
        cursor = found_at + len(paragraph)

        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= max_chunk_size:
            if not buffer:
                buffer_start = found_at
            buffer = candidate
        else:
            if buffer:
                chunks.append(_make_chunk(buffer, index=index, start=buffer_start, strategy=ChunkStrategyName.PARAGRAPH))
                index += 1
            buffer = paragraph
            buffer_start = found_at

    if buffer.strip():
        chunks.append(_make_chunk(buffer, index=index, start=buffer_start, strategy=ChunkStrategyName.PARAGRAPH))

    return chunks


def chunk_by_sentence(text: str, *, max_chunk_size: int = 1000, language: str = "en") -> list[Chunk]:
    """
    Strategy 3: group whole sentences up to `max_chunk_size` characters,
    never splitting a sentence across a chunk boundary.
    """
    sentences = segment_sentences(text, language=language)
    chunks: list[Chunk] = []
    buffer = ""
    buffer_start = 0
    index = 0
    cursor = 0

    for sentence in sentences:
        found_at = text.find(sentence, cursor)
        if found_at == -1:
            found_at = cursor
        cursor = found_at + len(sentence)

        candidate = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(candidate) <= max_chunk_size:
            if not buffer:
                buffer_start = found_at
            buffer = candidate
        else:
            if buffer:
                chunks.append(_make_chunk(buffer, index=index, start=buffer_start, strategy=ChunkStrategyName.SENTENCE))
                index += 1
            buffer = sentence
            buffer_start = found_at

    if buffer.strip():
        chunks.append(_make_chunk(buffer, index=index, start=buffer_start, strategy=ChunkStrategyName.SENTENCE))

    return chunks


def chunk_sliding_window(text: str, *, chunk_size: int = 1000, overlap: int = 200) -> list[Chunk]:
    """
    Strategy 4: fixed-size chunks with `overlap` characters repeated
    between consecutive chunks — see module docstring for why overlap
    matters for retrieval quality.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not (0 <= overlap < chunk_size):
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    step = chunk_size - overlap
    chunks: list[Chunk] = []
    index = 0
    start = 0

    while start < len(text):
        piece = text[start : start + chunk_size]
        if piece.strip():
            chunks.append(
                _make_chunk(
                    piece,
                    index=index,
                    start=start,
                    strategy=ChunkStrategyName.SLIDING_WINDOW,
                    extra_metadata={"overlap": overlap},
                )
            )
            index += 1
        start += step

    return chunks


_STRATEGY_DISPATCH = {
    ChunkStrategyName.FIXED_SIZE: chunk_fixed_size,
    ChunkStrategyName.PARAGRAPH: chunk_by_paragraph,
    ChunkStrategyName.SENTENCE: chunk_by_sentence,
    ChunkStrategyName.SLIDING_WINDOW: chunk_sliding_window,
}


def chunk_text(text: str, *, strategy: ChunkStrategyName = ChunkStrategyName.PARAGRAPH, **kwargs) -> list[Chunk]:
    """
    Single entry point used by the document processing pipeline — dispatches
    to the requested strategy function. `**kwargs` are forwarded to the
    chosen strategy (e.g., `chunk_size`, `overlap`, `max_chunk_size`).
    """
    strategy_fn = _STRATEGY_DISPATCH[strategy]
    return strategy_fn(text, **kwargs)
