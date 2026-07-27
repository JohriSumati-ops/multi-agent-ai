"""
llm/prompts/templates.py — PROMPT TEMPLATES + STRUCTURED OUTPUT SCHEMA

WHY THIS FILE EXISTS
---------------------
Separates the FIXED part of a prompt (role instruction, grounding
constraint, output format requirement) from the PER-REQUEST part
(assembled context, the user's actual question) — see docs/Phase6.md
Section 2. A `PromptTemplate` is data, not a function; `PromptBuilder`
(llm/prompts/builder.py) is what combines a template with request-specific
data into an actual prompt string.

`StructuredAnswer` is the Pydantic schema every reasoning-layer LLM call
is instructed to produce (Section 8) and that `ResponseValidator`
validates against — defined here, next to the templates that reference its
shape in their instructions, so the two never drift out of sync silently.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


class SourceUsed(BaseModel):
    chunk_id: str
    document_title: str = ""
    relevance: str = ""


class StructuredAnswer(BaseModel):
    """
    The exact JSON shape every reasoning-layer prompt instructs the model
    to return. See docs/Phase6.md Section 8 for why `token_usage` and
    `latency_ms` are deliberately NOT part of this schema (measured by
    `LLMService` instead, not self-reported by the model).
    """

    answer: str
    sources_used: list[SourceUsed] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str
    memory_references: list[str] = Field(default_factory=list)


@dataclass
class PromptTemplate:
    name: str
    version: int
    system_instruction: str
    output_format_instruction: str

    def render_system_prompt(self) -> str:
        return f"{self.system_instruction}\n\n{self.output_format_instruction}"


_GROUNDING_CONSTRAINT = (
    "Answer ONLY using the information in the provided context below. "
    "Do not use outside knowledge. If the context does not contain enough "
    "information to answer, say so explicitly rather than guessing."
)

_OUTPUT_FORMAT_INSTRUCTION = (
    "Respond with ONLY a single JSON object (no other text, no markdown code "
    'fences) matching this exact shape: {"answer": str, "sources_used": '
    '[{"chunk_id": str, "document_title": str, "relevance": str}], '
    '"confidence": float between 0.0 and 1.0, "reasoning_summary": str, '
    '"memory_references": [str]}. Every chunk_id you reference in '
    "sources_used MUST be one of the chunk_ids given to you in the context "
    "— never invent one."
)

RESEARCH_QUERY_TEMPLATE = PromptTemplate(
    name="research_query",
    version=1,
    system_instruction=(
        "You are a research assistant answering questions using a user's own "
        f"uploaded documents and remembered context. {_GROUNDING_CONSTRAINT} "
        "When multiple sources are provided, synthesize across them and note "
        "if sources appear to disagree."
    ),
    output_format_instruction=_OUTPUT_FORMAT_INSTRUCTION,
)

QUESTION_ANSWERING_TEMPLATE = PromptTemplate(
    name="question_answering",
    version=1,
    system_instruction=(
        "You are answering a specific, narrow question using the provided "
        f"context only. {_GROUNDING_CONSTRAINT} Keep the answer focused and "
        "directly responsive to the question asked."
    ),
    output_format_instruction=_OUTPUT_FORMAT_INSTRUCTION,
)

SUMMARIZATION_TEMPLATE = PromptTemplate(
    name="summarization",
    version=1,
    system_instruction=(
        "You are summarizing the provided context faithfully and concisely. "
        f"{_GROUNDING_CONSTRAINT} Do not answer any implicit question — only "
        "summarize what the context says."
    ),
    output_format_instruction=_OUTPUT_FORMAT_INSTRUCTION,
)
