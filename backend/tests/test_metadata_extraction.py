"""
tests/test_metadata_extraction.py

Exercises the two Phase 2 agents chained through a shared TaskContext,
exactly as `document_processing/pipeline.py` uses them — proving the
Phase 1 `BaseAgent` design (validate -> execute -> validate, with timing
and error containment for free) works for real, concrete agents.
"""

from __future__ import annotations

import pytest

from agents.metadata_extraction_agent import ExtractedMetadata, MetadataExtractionAgent
from agents.pdf_parsing_agent import PDFParsingAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError
from models.document import DocumentFormat


def _run_pipeline_agents(file_path: str, file_format: DocumentFormat, filename: str) -> TaskContext:
    context = TaskContext(user_id="test-user", original_query="")
    context.intermediate_results["file_path"] = file_path
    context.intermediate_results["file_format"] = file_format
    context.intermediate_results["original_filename"] = filename

    parse_result = PDFParsingAgent().run(context)
    assert parse_result.success, parse_result.error_message

    metadata_result = MetadataExtractionAgent().run(context)
    assert metadata_result.success, metadata_result.error_message

    return context


def test_metadata_agent_falls_back_to_filename_when_no_native_title(tmp_path) -> None:
    file_path = tmp_path / "graph_algorithms_notes.txt"
    file_path.write_text(
        "A graph is a set of nodes connected by edges. "
        "Graphs can be directed or undirected, weighted or unweighted."
    )
    context = _run_pipeline_agents(str(file_path), DocumentFormat.TXT, "graph_algorithms_notes.txt")
    metadata: ExtractedMetadata = context.intermediate_results["extracted_metadata"]

    assert metadata.title == "Graph Algorithms Notes"
    assert metadata.language == "en"
    assert metadata.word_count > 0
    assert metadata.reading_time_minutes >= 0.0


def test_metadata_agent_prefers_markdown_h1_over_filename(tmp_path) -> None:
    file_path = tmp_path / "untitled.md"
    file_path.write_text(
        "# Recursion Fundamentals\n\nRecursion is when a function calls itself "
        "to solve smaller instances of the same problem."
    )
    context = _run_pipeline_agents(str(file_path), DocumentFormat.MARKDOWN, "untitled.md")
    metadata: ExtractedMetadata = context.intermediate_results["extracted_metadata"]

    assert metadata.title == "Recursion Fundamentals"


def test_metadata_agent_records_execution_trace_on_context() -> None:
    context = TaskContext(user_id="test-user", original_query="")
    context.intermediate_results["file_path"] = "/nonexistent/path.txt"
    context.intermediate_results["file_format"] = DocumentFormat.TXT
    context.intermediate_results["original_filename"] = "path.txt"

    result = PDFParsingAgent().run(context)

    assert result.success is False
    assert result.error_message is not None
    assert context.execution_trace[-1]["agent"] == "pdf_parsing_agent"
    assert context.execution_trace[-1]["summary"] == "failed"


def test_metadata_agent_requires_upstream_parsed_document() -> None:
    context = TaskContext(user_id="test-user", original_query="")
    # Deliberately skip running PDFParsingAgent first.
    with pytest.raises(ValidationAppError):
        MetadataExtractionAgent().validate_input(context)
