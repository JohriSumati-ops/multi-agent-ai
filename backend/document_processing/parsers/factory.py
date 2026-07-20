"""
document_processing/parsers/factory.py

WHY THIS FILE EXISTS
---------------------
Something needs to know "given a `DocumentFormat`, which concrete parser
handles it" — without this, that mapping would be duplicated wherever
parsing is triggered. Centralizing it here means adding a fifth format
later is a one-line addition to `_PARSERS`, not a hunt through the
codebase for every `if format == "pdf"` check.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Simple Factory pattern — callers ask for "a parser for this format" and
get back something satisfying `BaseParser`, without needing to know which
concrete class that is.
"""

from __future__ import annotations

from core.exceptions import UnsupportedFileTypeError
from document_processing.parsers.base_parser import BaseParser
from document_processing.parsers.docx_parser import DOCXParser
from document_processing.parsers.markdown_parser import MarkdownParser
from document_processing.parsers.pdf_parser import PDFParser
from document_processing.parsers.txt_parser import TXTParser
from models.document import DocumentFormat

_PARSERS: dict[DocumentFormat, type[BaseParser]] = {
    DocumentFormat.PDF: PDFParser,
    DocumentFormat.TXT: TXTParser,
    DocumentFormat.MARKDOWN: MarkdownParser,
    DocumentFormat.DOCX: DOCXParser,
}


def get_parser(file_format: DocumentFormat) -> BaseParser:
    parser_cls = _PARSERS.get(file_format)
    if parser_cls is None:
        raise UnsupportedFileTypeError(f"No parser is registered for format '{file_format}'.")
    return parser_cls()
