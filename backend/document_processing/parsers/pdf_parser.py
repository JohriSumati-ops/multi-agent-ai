"""
document_processing/parsers/pdf_parser.py

WHY THIS FILE EXISTS
---------------------
The lowest-level, library-specific PDF text extraction logic. Kept
separate from `agents/pdf_parsing_agent.py` deliberately: this file knows
about `pypdf`; the agent knows about the `BaseAgent` contract (timing,
logging, structured results) and calls this parser as one implementation
detail of `execute()`. That separation means the parsing logic here is
directly unit-testable without going through the agent machinery at all.

NLP / DOCUMENT PROCESSING CONCEPT
--------------------------------------
PDF text extraction is inherently lossy: PDF is a *layout* format (where
glyphs sit on a page), not a *text* format, so extraction libraries
reconstruct reading order heuristically. This is exactly why real systems
(Google Docs OCR, Microsoft's Immersive Reader, Perplexity's ingestion)
always follow extraction with a cleaning pass — see
`document_processing/text_cleaner.py` — rather than trusting raw
extracted text directly.

ERROR HANDLING
-----------------
Three failure modes are distinguished explicitly, per the Phase 2
requirement to handle corrupted, encrypted, and empty documents distinctly:
- Encrypted PDFs raise `EncryptedDocumentError` immediately (pypdf
  reports `reader.is_encrypted` without needing to attempt extraction).
- Malformed/corrupted files raise `CorruptedDocumentError`, wrapping
  whatever `pypdf` raised so the original cause isn't lost.
- A PDF that parses successfully but yields no extractable text raises
  `EmptyDocumentError` — common for scanned/image-only PDFs, which Phase 2
  deliberately does not attempt to OCR (see Architecture Section 12's
  Future Scope: OCR is a Future Scope item, not Phase 2).
"""

from __future__ import annotations

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from core.exceptions import CorruptedDocumentError, EmptyDocumentError, EncryptedDocumentError
from document_processing.parsers.base_parser import BaseParser, ParsedDocument, ParsedPage


class PDFParser(BaseParser):
    def parse(self, file_path: str) -> ParsedDocument:
        try:
            reader = PdfReader(file_path)
        except (PdfReadError, OSError, ValueError) as exc:
            raise CorruptedDocumentError(
                "The PDF file could not be opened — it may be corrupted or not a valid PDF.",
                details={"underlying_error": str(exc)},
            ) from exc

        if reader.is_encrypted:
            # Attempt an empty-password unlock, since some PDFs are
            # "encrypted" only in the sense of having owner-permission
            # restrictions with no user password.
            try:
                if reader.decrypt("") == 0:
                    raise EncryptedDocumentError(
                        "This PDF is password-protected and cannot be read."
                    )
            except Exception as exc:  # noqa: BLE001 — pypdf raises varied types here
                raise EncryptedDocumentError(
                    "This PDF is password-protected and cannot be read."
                ) from exc

        pages: list[ParsedPage] = []
        try:
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                pages.append(ParsedPage(page_number=i, text=text))
        except (PdfReadError, ValueError) as exc:
            raise CorruptedDocumentError(
                "The PDF's content could not be read — it may be corrupted.",
                details={"underlying_error": str(exc)},
            ) from exc

        raw_text = "\n\n".join(p.text for p in pages)

        if not raw_text.strip():
            raise EmptyDocumentError(
                "No extractable text was found in this PDF. It may be a scanned/image-only "
                "document — OCR is not supported in this phase."
            )

        metadata = reader.metadata or {}
        return ParsedDocument(
            raw_text=raw_text,
            pages=pages,
            native_title=getattr(metadata, "title", None),
            native_author=getattr(metadata, "author", None),
            page_count=len(pages),
        )
