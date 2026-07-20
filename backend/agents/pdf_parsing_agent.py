"""
agents/pdf_parsing_agent.py — THE FIRST CONCRETE AGENT

WHY THIS FILE EXISTS
---------------------
Phase 1 built `BaseAgent` as an interface with zero implementations. This
is the first subclass — proof that the Template Method design from Phase 1
actually works: this class only implements `validate_input`, `execute`,
and `validate_output`; timing, logging, and structured error handling
(`run()`) are inherited for free.

Deliberately thin: all the real parsing logic lives in
`document_processing/parsers/pdf_parser.py`. This agent's job is narrower —
adapt that parser's output into the `BaseAgent`/`TaskContext` contract so
the (future) Supervisor can invoke it exactly like every other agent.

WHY THIS EXISTS AS AN AGENT AND NOT JUST A FUNCTION CALL
-------------------------------------------------------------
Wrapping parsing in the Agent interface — even though Phase 2 has no
Supervisor yet to invoke it — means every parse attempt is automatically
timed and written to `AgentExecutionLog` (once wired into the service
layer), giving the exact same observability a "real" reasoning agent gets
in later phases. This is the payoff of Phase 1's Template Method design
showing up immediately.

HOW GOOGLE / MICROSOFT / OPENAI / PERPLEXITY DO SOMETHING SIMILAR
------------------------------------------------------------------------
Every one of these systems treats document ingestion as a pipeline of
discrete, independently-retryable steps rather than one monolithic
function — exactly the "one agent per pipeline stage" shape used here —
because a PDF parsing failure and a downstream chunking failure need
different retry/error-reporting behavior.

HOW THIS PREPARES FOR PHASE 3
---------------------------------
The Embedding Agent (Phase 3) will be structured identically: a thin
`BaseAgent` subclass wrapping a lower-level module
(`retrieval/embedder.py`, not yet written), following the exact pattern
established here.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError
from document_processing.parsers.base_parser import ParsedDocument
from document_processing.parsers.factory import get_parser
from models.document import DocumentFormat


class PDFParsingAgent(BaseAgent):
    """
    Extracts text, per-page content, and any format-native metadata from a
    document at `context.intermediate_results["file_path"]`.

    Despite the name (kept for continuity with the Phase 0/1 architecture
    doc, which named this "PDF Parsing Agent" as agent #1), this agent
    dispatches through `document_processing.parsers.factory.get_parser`,
    so it transparently handles TXT/Markdown/DOCX as well as PDF — the
    factory is the seam that keeps this agent's code from needing an
    `if format == ...` branch per format.
    """

    name = "pdf_parsing_agent"

    def validate_input(self, context: TaskContext) -> None:
        if "file_path" not in context.intermediate_results:
            raise ValidationAppError("PDFParsingAgent requires 'file_path' in intermediate_results")
        if "file_format" not in context.intermediate_results:
            raise ValidationAppError("PDFParsingAgent requires 'file_format' in intermediate_results")

    def execute(self, context: TaskContext) -> ParsedDocument:
        file_path: str = context.intermediate_results["file_path"]
        file_format: DocumentFormat = context.intermediate_results["file_format"]

        parser = get_parser(file_format)
        parsed = parser.parse(file_path)

        # Make the parsed output available to whichever agent runs next in
        # this task (the Metadata Extraction Agent) without re-parsing.
        context.intermediate_results["parsed_document"] = parsed
        return parsed

    def validate_output(self, output: ParsedDocument) -> None:
        if not output.raw_text or not output.raw_text.strip():
            # Parsers already raise EmptyDocumentError themselves before
            # reaching here in the normal case — this is a defense-in-depth
            # check for any parser that doesn't.
            raise ValidationAppError("PDFParsingAgent produced no extractable text")
