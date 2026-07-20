"""
document_processing/text_cleaner.py

WHY THIS FILE EXISTS
---------------------
Raw extracted text is dirty in predictable ways: inconsistent whitespace,
Unicode variants of the same visual character, repeated headers/footers on
every PDF page, bare page numbers left over from pagination, and blank
lines. Every downstream step (sentence segmentation, chunking) produces
better results on cleaned text — this module is the single place that
cleaning happens, so it's tuned and tested once rather than reimplemented
ad hoc in the chunker or the metadata agent.

NLP CONCEPTS USED
----------------------
1. **Whitespace normalization** — collapsing runs of spaces/tabs and
   normalizing line endings. Extracted PDF text frequently contains
   multiple consecutive spaces from column layouts.
2. **Unicode normalization (NFKC)** — canonicalizes visually-identical but
   differently-encoded characters (e.g., "ﬁ" the ligature vs. "f" + "i",
   curly quotes vs. straight quotes) so downstream tokenization treats them
   consistently. This is a standard first step in almost every real NLP
   pipeline, precisely because raw text "in the wild" is Unicode-inconsistent.
3. **Header/footer removal (heuristic)** — a line that repeats identically
   across a large fraction of a document's pages is almost certainly a
   running header/footer, not content, and is removed.
4. **Page number removal (heuristic)** — a line that is *only* a number
   (optionally with surrounding dashes, e.g., "- 4 -") is treated as a
   page number artifact.
5. **Empty line cleanup** — collapsing 3+ consecutive blank lines down to
   a single paragraph break, so paragraph segmentation later doesn't
   produce spurious empty "paragraphs."

HOW GOOGLE / MICROSOFT / OPENAI / PERPLEXITY DO SOMETHING SIMILAR
------------------------------------------------------------------------
Every production document-ingestion pipeline (Google Docs OCR
post-processing, Microsoft's Immersive Reader, OpenAI's file-search
ingestion, Perplexity's web-page cleaning before indexing) runs some form
of this same cleaning pass before anything resembling "understanding"
happens — because a language model or a search index built on top of dirty
text inherits every artifact in that dirt (a repeated footer line, indexed
thousands of times, meaningfully pollutes both keyword and embedding-based
search).

HOW THIS PREPARES FOR PHASE 3
---------------------------------
Embeddings are only as good as the text fed into them — a chunk containing
"Page 4 of 12\n\n" as a leading artifact produces a measurably worse
embedding than the same chunk without it. This module is what guarantees
Phase 3 never has to deal with that.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

_WHITESPACE_RUN = re.compile(r"[ \t]+")
_MULTI_BLANK_LINES = re.compile(r"\n{3,}")
_PAGE_NUMBER_LINE = re.compile(r"^\s*[-–—]?\s*\d{1,4}\s*[-–—]?\s*$")


def normalize_unicode(text: str) -> str:
    """NFKC-normalize text — see module docstring, concept #2."""
    return unicodedata.normalize("NFKC", text)


def normalize_whitespace(text: str) -> str:
    """
    Collapse runs of horizontal whitespace and normalize line endings —
    see module docstring, concept #1.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_WHITESPACE_RUN.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(lines)


def remove_page_number_lines(text: str) -> str:
    """
    Drop lines that are purely a page number (optionally dash-flanked) —
    see module docstring, concept #4.
    """
    kept_lines = [line for line in text.split("\n") if not _PAGE_NUMBER_LINE.match(line)]
    return "\n".join(kept_lines)


def remove_repeated_lines(pages_text: list[str], *, min_repetition_ratio: float = 0.6) -> list[str]:
    """
    Heuristic header/footer removal across a multi-page document — see
    module docstring, concept #3.

    A non-empty line appearing on at least `min_repetition_ratio` of pages
    is treated as a running header/footer and stripped from every page it
    appears on. Requires at least 3 pages to avoid false positives on very
    short documents (a 2-page document sharing one line is not evidence of
    a "repeated" header — it's just a document, and stripping it would
    likely destroy real content).
    """
    if len(pages_text) < 3:
        return pages_text

    line_page_counts: Counter[str] = Counter()
    for page in pages_text:
        # Use a set so a line repeated twice *within* one page only counts once.
        for line in {ln.strip() for ln in page.split("\n") if ln.strip()}:
            line_page_counts[line] += 1

    threshold = max(2, int(len(pages_text) * min_repetition_ratio))
    boilerplate_lines = {line for line, count in line_page_counts.items() if count >= threshold}

    if not boilerplate_lines:
        return pages_text

    cleaned_pages = []
    for page in pages_text:
        kept = [ln for ln in page.split("\n") if ln.strip() not in boilerplate_lines]
        cleaned_pages.append("\n".join(kept))
    return cleaned_pages


def collapse_empty_lines(text: str) -> str:
    """Collapse 3+ consecutive blank lines to exactly one paragraph break — concept #5."""
    return _MULTI_BLANK_LINES.sub("\n\n", text).strip()


def clean_text(raw_text: str, *, pages_text: list[str] | None = None) -> str:
    """
    Full cleaning pipeline, applied in a deliberate order:
    header/footer removal (needs per-page text) -> Unicode normalization ->
    whitespace normalization -> page-number-line removal -> empty-line
    collapse.

    `pages_text`, when provided (PDF only), enables step 1; single-page /
    non-paginated formats skip straight to Unicode normalization.
    """
    if pages_text:
        pages_text = remove_repeated_lines(pages_text)
        text = "\n\n".join(pages_text)
    else:
        text = raw_text

    text = normalize_unicode(text)
    text = normalize_whitespace(text)
    text = remove_page_number_lines(text)
    text = collapse_empty_lines(text)
    return text
