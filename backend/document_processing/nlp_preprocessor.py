"""
document_processing/nlp_preprocessor.py

WHY THIS FILE EXISTS
---------------------
This is the "classical NLP" core of Phase 2 — everything here is
rule-based / statistical, deliberately with zero embeddings or learned
models. The explicit Phase 2 constraint ("teach me classical NLP") is what
this file exists to satisfy: sentence and paragraph segmentation, and
basic corpus statistics, using well-understood, inspectable algorithms
rather than black-box models.

NLP CONCEPTS USED
----------------------
1. **Sentence segmentation** — splitting text into sentences is harder
   than "split on '.'" because periods are ambiguous (abbreviations,
   decimals, ellipses, initials). We use `pysbd` (Python Sentence
   Boundary Disambiguation), a rule-based segmenter — a good midpoint
   between naive regex splitting and a full learned model, and exactly the
   kind of tool real pipelines used before (and often still alongside)
   learned segmenters.
2. **Paragraph segmentation** — simpler than sentence segmentation:
   paragraphs are separated by blank lines in cleaned text, so this is a
   structural split, not a linguistic one.
3. **Tokenization / word counting** — a whitespace + punctuation-aware
   regex tokenizer (`\\w+`). This is deliberately NOT a subword/BPE
   tokenizer (like an LLM would use) — see the `token_count` docstring
   below for why that distinction matters and is deferred to Phase 3.
4. **Character counting** — trivial, but included because "character
   count" is a real, commonly-needed metric (e.g., respecting an LLM
   provider's context window, which is ultimately bounded in characters
   as a rough proxy before real tokenization).
5. **Reading time estimation** — word_count / average adult silent
   reading speed (established HCI/UX convention: ~200-250 words per
   minute; 225 is used here as a reasonable midpoint), rounded to a
   sensible display granularity.
6. **Language detection** — statistical n-gram-based detection via
   `langdetect` (a Python port of Google's language-detection library).
   This is *not* a deep learning model — it's a classical Bayesian
   classifier over character n-gram frequency profiles, which is exactly
   why it belongs in Phase 2 and not Phase 3.

TOKEN COUNT: WHY THIS IS AN APPROXIMATION
---------------------------------------------
`token_count` in this module counts whitespace-delimited words, NOT the
subword tokens an actual LLM tokenizer (e.g., a BPE or SentencePiece
tokenizer) would produce. Real LLM tokenizers split words into subword
units and can't be reproduced with a regex. This approximation is
intentionally used in Phase 2 because introducing a real tokenizer here
would require depending on a specific model's tokenizer before Phase 3 has
even chosen an embedding model — the exact "NO Embeddings" boundary the
Phase 2 spec draws. `Chunk.token_count` will be recomputed with a real
tokenizer once Phase 3 selects an embedding model.

HOW GOOGLE / MICROSOFT / OPENAI / PERPLEXITY DO SOMETHING SIMILAR
------------------------------------------------------------------------
Every one of these systems computes lightweight corpus statistics (word
count, reading time, language) as metadata *before* any embedding call,
both to power UI features (Google Docs' word count, Medium's "X min read")
and, crucially, as cheap signals used to route documents (e.g., skip
embedding empty or non-target-language documents) before spending money on
model inference — which is exactly why this step exists prior to Phase 3.

HOW THIS PREPARES FOR PHASE 3
---------------------------------
Sentence and paragraph boundaries computed here are exactly what
`retrieval/chunker.py`'s SENTENCE and PARAGRAPH strategies consume. Phase 3
does not re-derive them — it reuses this module's output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pysbd
from langdetect import LangDetectException, detect as _langdetect_detect

_WORD_PATTERN = re.compile(r"\w+", re.UNICODE)
_AVERAGE_READING_SPEED_WPM = 225


@dataclass
class TextStatistics:
    word_count: int
    char_count: int
    sentence_count: int
    paragraph_count: int
    reading_time_minutes: float
    language: str | None


def segment_sentences(text: str, language: str = "en") -> list[str]:
    """
    Split `text` into sentences using pysbd's rule-based segmenter — see
    module docstring, concept #1.

    `language` uses pysbd's ISO 639-1 language codes; unsupported codes
    fall back to English rules rather than raising, since a slightly
    imperfect segmentation is far better than a crash on an edge-case
    language detection result.
    """
    try:
        segmenter = pysbd.Segmenter(language=language, clean=False)
    except Exception:  # noqa: BLE001 — pysbd raises on unsupported language codes
        segmenter = pysbd.Segmenter(language="en", clean=False)
    return [s.strip() for s in segmenter.segment(text) if s.strip()]


def segment_paragraphs(text: str) -> list[str]:
    """
    Split cleaned text into paragraphs on blank-line boundaries — see
    module docstring, concept #2. Assumes `text` has already passed
    through `text_cleaner.clean_text`, which guarantees paragraph breaks
    are exactly `\\n\\n`.
    """
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def count_words(text: str) -> int:
    """Whitespace/punctuation-aware word count — see module docstring, concept #3."""
    return len(_WORD_PATTERN.findall(text))


def count_characters(text: str) -> int:
    """See module docstring, concept #4."""
    return len(text)


def estimate_reading_time_minutes(word_count: int) -> float:
    """See module docstring, concept #5."""
    if word_count <= 0:
        return 0.0
    minutes = word_count / _AVERAGE_READING_SPEED_WPM
    return round(minutes, 1)


def detect_language(text: str) -> str | None:
    """
    Detect the dominant language of `text` as an ISO 639-1 code (e.g.,
    "en") — see module docstring, concept #6.

    Returns None rather than raising when detection isn't possible (e.g.,
    text too short, or entirely numeric/symbolic) — language detection
    failing is not a document-processing failure, just a missing metadata
    field.
    """
    sample = text.strip()
    if len(sample) < 20:  # too short for reliable statistical detection
        return None
    try:
        return _langdetect_detect(sample)
    except LangDetectException:
        return None


def compute_statistics(text: str, *, language_hint: str | None = None) -> TextStatistics:
    """
    Compute the full Phase 2 statistics bundle for a cleaned document's
    text in one pass, avoiding redundant re-tokenization/re-segmentation
    across separate calls.
    """
    language = language_hint or detect_language(text)
    word_count = count_words(text)
    char_count = count_characters(text)
    sentence_count = len(segment_sentences(text, language=language or "en"))
    paragraph_count = len(segment_paragraphs(text))

    return TextStatistics(
        word_count=word_count,
        char_count=char_count,
        sentence_count=sentence_count,
        paragraph_count=paragraph_count,
        reading_time_minutes=estimate_reading_time_minutes(word_count),
        language=language,
    )
