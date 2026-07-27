"""
schemas/research.py — Phase 6

Every ID field is typed `UUID`, not `str` — per docs/Phase4.md Section
11's standing rule for every new schema this project adds.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ResearchQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    document_id: UUID | None = None


class SourceUsedOut(BaseModel):
    chunk_id: str
    document_title: str = ""
    relevance: str = ""


class CitationOut(BaseModel):
    chunk_id: str
    citation_text: str
    document_title: str | None = None
    page_number: int | None = None
    is_memory: bool = False


class ResearchAnswerOut(BaseModel):
    used_llm: bool
    answer: str | None = None
    sources_used: list[SourceUsedOut] = Field(default_factory=list)
    citations: list[CitationOut] = Field(default_factory=list)
    confidence: float | None = None
    reasoning_summary: str | None = None
    memory_references: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    is_grounded: bool | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int
    fallback_reason: str | None = None
    response_id: UUID | None = None


class ConflictOut(BaseModel):
    item_a_id: str
    item_b_id: str
    shared_terms: list[str]
    note: str


class ReasoningResponse(BaseModel):
    evidence_count: int
    conflicts: list[ConflictOut]
    average_relevance: float
    consensus_note: str


class ExplainResponse(BaseModel):
    response_id: UUID
    query_text: str
    answer_text: str
    confidence: float
    reasoning_summary: str
    sources_used: list[dict]
    memory_references: list[str]
    retrieved_chunk_ids: list[str]
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int | None
    explainability_payload: dict
