"""
llm/prompts/registry.py — THE PROMPT REGISTRY

WHY THIS FILE EXISTS
---------------------
See docs/Phase6.md Section 9. Templates are registered under
`(name, version)`, mirroring `orchestration/agent_registry.py`'s
capability-string lookup pattern from Phase 5 — callers ask for a template
by name (and, optionally, a pinned version), never importing a template
constant directly, which is what would let a future prompt A/B test swap
versions without touching call sites.
"""

from __future__ import annotations

from core.exceptions import AppException
from llm.prompts.templates import (
    QUESTION_ANSWERING_TEMPLATE,
    RESEARCH_QUERY_TEMPLATE,
    SUMMARIZATION_TEMPLATE,
    PromptTemplate,
)


class PromptTemplateNotFoundError(AppException):
    status_code = 404
    error_code = "prompt_template_not_found"


class PromptRegistry:
    def __init__(self) -> None:
        self._templates: dict[tuple[str, int], PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> None:
        self._templates[(template.name, template.version)] = template

    def get(self, name: str, version: int | None = None) -> PromptTemplate:
        """
        Returns the requested template. When `version` is omitted, returns
        the highest registered version for that name — "latest" is always
        an explicit choice a caller opts into, never an implicit default
        that silently changes behavior when a new version is registered.
        """
        if version is not None:
            template = self._templates.get((name, version))
            if template is None:
                raise PromptTemplateNotFoundError(f"No template registered for '{name}' version {version}")
            return template

        matching = [t for (n, _v), t in self._templates.items() if n == name]
        if not matching:
            raise PromptTemplateNotFoundError(f"No template registered under name '{name}'")
        return max(matching, key=lambda t: t.version)

    def list_names(self) -> list[str]:
        return sorted({name for name, _version in self._templates})


_instance: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    """
    Process-wide singleton, pre-populated with this project's built-in
    templates — mirroring `orchestration/agent_registry.py::get_agent_registry`'s
    "singleton with defaults registered on first access" pattern.
    """
    global _instance
    if _instance is None:
        _instance = PromptRegistry()
        _instance.register(RESEARCH_QUERY_TEMPLATE)
        _instance.register(QUESTION_ANSWERING_TEMPLATE)
        _instance.register(SUMMARIZATION_TEMPLATE)
    return _instance


def reset_prompt_registry() -> None:
    """Test-only: clears the singleton so the next get_prompt_registry() rebuilds it with defaults."""
    global _instance
    _instance = None
