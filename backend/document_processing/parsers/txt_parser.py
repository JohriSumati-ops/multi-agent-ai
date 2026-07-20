"""
document_processing/parsers/txt_parser.py

The simplest parser: plain text files have no layout to reconstruct and no
embedded metadata. This adapter exists mainly so `.txt` uploads flow
through the exact same `ParsedDocument` contract as every other format —
consistency, not complexity, is the point here.
"""

from __future__ import annotations

from core.exceptions import EmptyDocumentError
from document_processing.parsers.base_parser import BaseParser, ParsedDocument


class TXTParser(BaseParser):
    def parse(self, file_path: str) -> ParsedDocument:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        if not raw_text.strip():
            raise EmptyDocumentError("This text file is empty.")

        return ParsedDocument(raw_text=raw_text)
