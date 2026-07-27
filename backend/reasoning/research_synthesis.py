"""
reasoning/research_synthesis.py — MULTI-DOCUMENT SYNTHESIS

WHY THIS FILE EXISTS
---------------------
See docs/Phase6.md Section 15. Operates on `ContextAssembler`'s already
ranked, deduplicated evidence — no new retrieval here. Two genuinely
separate responsibilities live in this file: **evidence grouping**
(which sources agree/disagree on a topic, purely structural) and
**conflict detection** (a deliberately conservative lexical heuristic,
documented below with its known limitations).

CONFLICT DETECTION: WHAT IT IS AND ISN'T
----------------------------------------------
This is NOT semantic contradiction detection (that would require a
trained entailment model — explicitly future scope, see
docs/Phase6.md Section 20). It is a narrow, conservative heuristic:
two sources are flagged as a *possible* conflict only when they share at
least `MIN_SHARED_TERMS` significant words AND exactly one of them
contains an explicit negation marker near a shared term. This produces
few false positives (a real disagreement using negation language IS
usually flagged) but many false negatives (a disagreement expressed
without negation words — "X causes Y" vs. "Z causes Y" — is NOT caught).
This asymmetry is intentional: a missed conflict just means the LLM
synthesizes without an explicit heads-up (no worse than this feature not
existing); a FALSE conflict flag actively confuses the prompt. Erring
toward under-flagging is the safer failure mode.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from reasoning.context_assembler import ContextItem

_NEGATION_MARKERS = {"not", "no", "never", "cannot", "can't", "isn't", "doesn't", "won't", "unlikely"}
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "of", "and", "or",
    "for", "with", "this", "that", "it", "as", "by", "be", "has", "have", "had",
}
MIN_SHARED_TERMS = 2


@dataclass
class Conflict:
    item_a_id: str
    item_b_id: str
    shared_terms: list[str]
    note: str


@dataclass
class SynthesisResult:
    evidence_count: int
    conflicts: list[Conflict]
    average_relevance: float
    consensus_note: str


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 3}


def _has_negation(text: str) -> bool:
    words = set(re.findall(r"[a-zA-Z']+", text.lower()))
    return bool(words & _NEGATION_MARKERS)


def detect_conflicts(items: list[ContextItem]) -> list[Conflict]:
    """See module docstring for exactly what this heuristic does and doesn't catch."""
    conflicts = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            shared = _significant_words(a.text) & _significant_words(b.text)
            if len(shared) < MIN_SHARED_TERMS:
                continue
            if _has_negation(a.text) != _has_negation(b.text):
                conflicts.append(
                    Conflict(
                        item_a_id=a.source_id,
                        item_b_id=b.source_id,
                        shared_terms=sorted(shared),
                        note=(
                            f"Sources may disagree on shared topic(s) {sorted(shared)[:3]} "
                            "— one uses negation language, the other doesn't."
                        ),
                    )
                )
    return conflicts


def synthesize(items: list[ContextItem]) -> SynthesisResult:
    """
    Aggregates evidence-level statistics + conflict flags. Does NOT
    produce a natural-language synthesis — that's the LLM's job, informed
    by this function's `conflicts` list, per Section 15's "detecting is
    heuristic, resolving is reasoning" split.
    """
    conflicts = detect_conflicts(items)
    avg_relevance = sum(i.relevance_score for i in items) / len(items) if items else 0.0

    if not items:
        consensus_note = "No evidence available."
    elif conflicts:
        consensus_note = f"{len(conflicts)} potential conflict(s) detected among {len(items)} source(s)."
    else:
        consensus_note = f"No conflicts detected among {len(items)} source(s)."

    return SynthesisResult(
        evidence_count=len(items), conflicts=conflicts, average_relevance=avg_relevance, consensus_note=consensus_note
    )
