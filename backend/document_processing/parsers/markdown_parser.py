"""
document_processing/parsers/markdown_parser.py

WHY THIS FILE EXISTS
---------------------
Markdown is treated as text-with-syntax rather than rendered to HTML and
stripped: for a study-notes use case, the raw Markdown (headings, bullet
points, code fences) carries real structural signal that's worth
preserving into the cleaning/chunking stages, rather than being thrown away
by an HTML-round-trip. Heavier markup normalization (if ever needed) is a
`document_processing/text_cleaner.py` concern, not this parser's.
"""

from __future__ import annotations

from core.exceptions import EmptyDocumentError
from document_processing.parsers.base_parser import BaseParser, ParsedDocument


class MarkdownParser(BaseParser):
    def parse(self, file_path: str) -> ParsedDocument:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        if not raw_text.strip():
            raise EmptyDocumentError("This Markdown file is empty.")

        # Use the first Markdown heading (`# Title`) as a native title hint
        # when present — a cheap, high-signal win the Metadata Extraction
        # Agent can use instead of falling back to the filename.
        native_title = None
        for line in raw_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                native_title = stripped.removeprefix("# ").strip()
                break

        return ParsedDocument(raw_text=raw_text, native_title=native_title)
