"""
schemas/explainability.py — THE EXPLAINABILITY FRAMEWORK

WHY THIS FILE EXISTS
---------------------
Architecture Section 6.2 defines an Explainability Agent whose entire job is
producing a human-readable justification for another agent's output. That
agent doesn't exist yet, but the *shape* of an explanation is a contract
worth fixing now: every future agent that makes a non-obvious decision
(Recommendation Agent, Gap Analysis Agent, Quiz Agent's difficulty
calibration) can populate this same structure.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Decision provenance as data, not prose baked into a single string. Storing
`evidence` and `decision_path` as structured lists (rather than one long
paragraph) means the frontend can render them as a checklist or a
traceable path graph later, and means the Explainability Agent can
programmatically inspect what a decision was based on rather than having to
re-derive it.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
`Recommendation Agent` (Phase 5) will populate `Explanation.reason` +
`Explanation.evidence` when it recommends a topic. `Gap Analysis Agent`
will populate `decision_path` to show the chain of quiz results that led to
a "weak topic" verdict. The Knowledge Graph frontend page can render
`retrieved_documents` as citation chips next to any explanation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """One piece of supporting evidence behind a decision or answer."""

    description: str
    source: str | None = None  # e.g., a document title, a quiz attempt ID
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class RetrievedDocumentRef(BaseModel):
    """
    Lightweight citation reference — deliberately NOT the full document
    content, just enough to link back to it. The Retrieval Agent (once it
    exists) is what populates lists of these.
    """

    document_id: str
    document_title: str
    chunk_id: str | None = None
    relevance_score: float | None = None


class DecisionStep(BaseModel):
    """One step in the reasoning chain that produced a decision."""

    step_description: str
    agent_name: str | None = None


class Explanation(BaseModel):
    """
    The full explainability record for a single agent decision or answer.

    This is intentionally more detailed than `AgentResult.reason` (which is
    a one-line summary) — `Explanation` is what backs a "Why am I seeing
    this?" expandable panel in the UI.
    """

    reason: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    retrieved_documents: list[RetrievedDocumentRef] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    decision_path: list[DecisionStep] = Field(default_factory=list)
