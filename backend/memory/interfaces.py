"""
memory/interfaces.py — MEMORY FOUNDATION

WHY THIS FILE EXISTS
---------------------
`models/memory.py` defines how memory is STORED (one table, discriminated
by `memory_type`). This file defines how memory is READ AND WRITTEN — the
policy layer. Architecture Section 3.2 is explicit that this distinction
matters: repositories store bytes, `memory/` decides what's worth
remembering and how it should be retrieved.

No retrieval logic is implemented here (per the Phase 1 constraint) — these
are abstract interfaces only, one per memory category, so each category's
eventual implementation (Phase 2 for short-term/conversation memory, Phase
5 for long-term memory) can be developed independently against a fixed
contract.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Interface Segregation: rather than one giant `MemoryManager` interface with
methods for all four categories, each category gets its own small
interface. A future `ShortTermMemoryStore` implementation doesn't need to
know or care about the long-term memory contract, and vice versa.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
- `ShortTermMemory`: implemented in Phase 2 by the Conversation Agent's
  supporting code; backed by `Memory` rows with `memory_type=SHORT_TERM`
  and a short `expires_at`.
- `LongTermMemory`: implemented in Phase 5 by the Memory Agent; backed by
  `memory_type=LONG_TERM` rows with no expiry.
- `ConversationMemory` / `DocumentMemory`: thin, scoped views over the same
  table, filtered by `conversation_id` / `document_id` respectively.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseMemoryStore(ABC):
    """Shared shape for all four memory interfaces below."""

    @abstractmethod
    def write(self, user_id: str, content: str, *, importance_score: float = 0.5, **scope: Any) -> None:
        """Persist a new memory entry. Concrete signature refined per subtype."""
        raise NotImplementedError

    @abstractmethod
    def read(self, user_id: str, **filters: Any) -> list[Any]:
        """Retrieve relevant memory entries for a user, optionally filtered."""
        raise NotImplementedError


class ShortTermMemory(BaseMemoryStore):
    """
    Memory scoped to the current session only — expected to expire quickly
    (see `Memory.expires_at`). Used for things like "the user just asked
    about DFS, so 'explain that again' refers to DFS."
    """


class LongTermMemory(BaseMemoryStore):
    """
    Durable, cross-session memory about the learner — synthesized patterns
    like "struggles with recursive base cases," not raw transcripts. Feeds
    the Learning Profile and Recommendation Agent.
    """


class ConversationMemory(BaseMemoryStore):
    """
    Memory scoped to a specific conversation thread — e.g., clarifying
    questions asked earlier in the same thread that should influence later
    answers in that same thread, but not others.
    """


class DocumentMemory(BaseMemoryStore):
    """
    Memory scoped to a specific document — e.g., "the user has revisited
    this document's Trees section three times," used to prioritize review
    recommendations tied to that specific source.
    """
