"""
utils/text.py

WHY THIS FILE EXISTS
---------------------
Small, stateless, dependency-free helpers that don't belong to any specific
layer (agents, services, repositories). Per the folder-responsibility rule
in Architecture Section 3.2: if a function needs to know about the
database, agents, or the request/response cycle, it does NOT belong in
utils/.

Only two trivial helpers exist in Phase 1 (there's no text-heavy processing
yet); this file exists mainly to establish the pattern and location future
phases (chunking, prompt formatting) will keep using.
"""

from __future__ import annotations


def truncate(text: str, max_length: int = 200, *, suffix: str = "...") -> str:
    """Shorten `text` to at most `max_length` characters, preserving whole words where possible."""
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - len(suffix)].rsplit(" ", 1)[0]
    return f"{truncated}{suffix}"


def char_count(text: str | None) -> int:
    """
    Null-safe character count.

    WHY THIS EXISTS: `models/agent_execution_log.py`'s `input_size_chars` /
    `output_size_chars` fields (part of the Confidence Framework's
    performance metrics) will be populated using this helper once agents
    exist, so the "what counts as size" logic lives in exactly one place.
    """
    return len(text) if text else 0
