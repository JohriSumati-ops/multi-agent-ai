"""
reasoning/citation_injector.py — CITATION GENERATION

WHY THIS FILE EXISTS
---------------------
See docs/Phase6.md Section 11. The model outputs a `chunk_id` (an opaque
identifier); this class resolves it to a real, human-readable citation by
looking up the actual `DocumentChunk`/`Memory` row — via the existing
repositories, no new lookup logic — rather than trusting the model to
generate correctly formatted citation text itself (a model has no
reliable way to know a chunk's real page number or a document's real
title beyond what was already in its context, and asking it to format
citation strings is one more place for it to fabricate details).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from repositories.document_chunk_repository import DocumentChunkRepository
from repositories.document_repository import DocumentRepository
from repositories.memory_repository import MemoryRepository


@dataclass
class Citation:
    chunk_id: str
    citation_text: str
    document_title: str | None = None
    page_number: int | None = None
    is_memory: bool = False


class CitationInjector:
    def __init__(self, *, document_chunks: DocumentChunkRepository, documents: DocumentRepository, memories: MemoryRepository) -> None:
        self.document_chunks = document_chunks
        self.documents = documents
        self.memories = memories

    def inject(self, chunk_ids: list[str]) -> list[Citation]:
        citations = []
        for raw_id in chunk_ids:
            try:
                uuid_id = UUID(raw_id)
            except ValueError:
                continue

            chunk = self.document_chunks.get(uuid_id)
            if chunk is not None:
                document = self.documents.get(chunk.document_id)
                title = document.title if document else "Unknown document"
                page_note = f", page {chunk.page_number}" if chunk.page_number else ""
                citations.append(
                    Citation(
                        chunk_id=raw_id,
                        citation_text=f"{title}{page_note} (chunk {chunk.chunk_index})",
                        document_title=title,
                        page_number=chunk.page_number,
                        is_memory=False,
                    )
                )
                continue

            memory = self.memories.get(uuid_id)
            if memory is not None:
                citations.append(
                    Citation(
                        chunk_id=raw_id,
                        citation_text=f"Remembered context ({memory.memory_type.value})",
                        is_memory=True,
                    )
                )

        return citations
