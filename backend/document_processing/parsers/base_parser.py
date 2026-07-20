"""
document_processing/parsers/base_parser.py

WHY THIS FILE EXISTS
---------------------
Four very different libraries (`pypdf`, `python-docx`, plain file reads,
and Markdown parsing) need to produce ONE common output shape so that
everything downstream — text cleaning, NLP preprocessing, chunking — can
be written once, against `ParsedDocument`, instead of once per file format.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
This is the Adapter pattern: each concrete parser adapts a
format-specific library's API to the same `BaseParser.parse()` contract.
Adding a fifth format later (e.g., HTML) means writing one new adapter, not
touching the pipeline that consumes it.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
`ParsedDocument.raw_text` is what `document_processing/text_cleaner.py`
cleans, and `ParsedDocument.pages` (when available) is what the Chunking
Engine uses to populate `DocumentChunk.page_number`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedPage:
    """One page of extracted text, for formats that have pages (PDF)."""

    page_number: int
    text: str


@dataclass
class ParsedDocument:
    """
    Universal output shape every parser produces, regardless of source
    format.
    """

    raw_text: str
    pages: list[ParsedPage] = field(default_factory=list)  # empty for non-paginated formats

    # Format-native metadata the parser could extract directly (e.g., PDF's
    # embedded /Author field, or docx's core properties). May be sparse or
    # empty — the Metadata Extraction Agent fills in the rest.
    native_title: str | None = None
    native_author: str | None = None
    page_count: int | None = None


class BaseParser(ABC):
    """Every format-specific parser implements this one method."""

    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        """
        Extract text (and structure, where available) from the file at
        `file_path`.

        Implementations are expected to raise the specific exceptions
        defined in `core/exceptions.py` (`CorruptedDocumentError`,
        `EncryptedDocumentError`, `EmptyDocumentError`) rather than letting
        a raw library exception (e.g., `pypdf.errors.PdfReadError`) escape
        — see each concrete parser for exactly which failures map to which
        exception.
        """
        raise NotImplementedError
