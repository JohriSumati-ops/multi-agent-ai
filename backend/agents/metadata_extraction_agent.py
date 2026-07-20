"""
agents/metadata_extraction_agent.py

WHY THIS FILE EXISTS
---------------------
Phase 2 requirement: a dedicated agent that produces the structured
metadata (title, author, page count, language, upload time, file size,
document type) that the frontend's Document Library page and every future
personalization feature (Gap Analysis, Recommendation) will read.

Deliberately separate from `PDFParsingAgent`: parsing extracts raw content;
this agent derives *facts about* that content. Splitting them means a
future improvement to metadata heuristics (e.g., better title detection)
never risks touching the parsing logic, and vice versa.

NLP CONCEPT USED
---------------------
Combines format-native metadata (when the source format embeds it, e.g., a
PDF's /Title field or a DOCX's core properties) with statistically-derived
metadata (language detection, word/char counts, reading time — see
`document_processing/nlp_preprocessor.py`) and cheap heuristic fallbacks
(using a Markdown H1 or the filename when no native title exists). This
"prefer authoritative source, fall back to heuristic, fall back to
filename" cascade is a standard pattern in real metadata-extraction
pipelines.

HOW GOOGLE / MICROSOFT / OPENAI / PERPLEXITY DO SOMETHING SIMILAR
------------------------------------------------------------------------
Google Drive's file preview, Microsoft's document properties panel, and
every search engine's snippet generation all run some version of this same
cascade — trust embedded metadata first, because it's cheap and often
author-provided, and only fall back to inference when it's missing or
low-quality.

HOW THIS PREPARES FOR PHASE 3
---------------------------------
`language` gates whether Phase 3 uses a multilingual embedding model for
this document. `word_count`/`char_count` inform default chunk-size
selection (a very short document doesn't need aggressive chunking).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError
from document_processing.nlp_preprocessor import compute_statistics
from document_processing.parsers.base_parser import ParsedDocument


@dataclass
class ExtractedMetadata:
    title: str
    author: str | None
    page_count: int | None
    language: str | None
    word_count: int
    char_count: int
    reading_time_minutes: float


class MetadataExtractionAgent(BaseAgent):
    """
    Derives `ExtractedMetadata` from a `ParsedDocument` (produced upstream
    by `PDFParsingAgent`) plus the original filename, using the
    prefer-native / fall-back-to-heuristic cascade described in the module
    docstring.
    """

    name = "metadata_extraction_agent"

    def validate_input(self, context: TaskContext) -> None:
        if "parsed_document" not in context.intermediate_results:
            raise ValidationAppError(
                "MetadataExtractionAgent requires 'parsed_document' in intermediate_results "
                "(run PDFParsingAgent first)"
            )
        if "original_filename" not in context.intermediate_results:
            raise ValidationAppError(
                "MetadataExtractionAgent requires 'original_filename' in intermediate_results"
            )

    def execute(self, context: TaskContext) -> ExtractedMetadata:
        parsed: ParsedDocument = context.intermediate_results["parsed_document"]
        original_filename: str = context.intermediate_results["original_filename"]

        title = self._resolve_title(parsed, original_filename)
        stats = compute_statistics(parsed.raw_text)

        metadata = ExtractedMetadata(
            title=title,
            author=parsed.native_author,
            page_count=parsed.page_count,
            language=stats.language,
            word_count=stats.word_count,
            char_count=stats.char_count,
            reading_time_minutes=stats.reading_time_minutes,
        )
        context.intermediate_results["extracted_metadata"] = metadata
        return metadata

    @staticmethod
    def _resolve_title(parsed: ParsedDocument, original_filename: str) -> str:
        """
        Cascade: native title (from PDF/DOCX metadata or a Markdown H1) ->
        filename without its extension, title-cased for readability.
        """
        if parsed.native_title and parsed.native_title.strip():
            return parsed.native_title.strip()

        stem = os.path.splitext(original_filename)[0]
        return stem.replace("_", " ").replace("-", " ").strip().title() or original_filename

    def validate_output(self, output: ExtractedMetadata) -> None:
        if not output.title:
            raise ValidationAppError("MetadataExtractionAgent failed to resolve a document title")
