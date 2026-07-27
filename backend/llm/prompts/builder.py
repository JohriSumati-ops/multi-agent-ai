"""
llm/prompts/builder.py — THE PROMPT BUILDER

WHY THIS FILE EXISTS
---------------------
The only place a `PromptTemplate` (fixed) and an `AssembledContext`
(per-request) are combined into the actual `list[LLMMessage]` sent to
`LLMService`. Kept separate from both so each can be tested independently
— a `PromptTemplate` test never needs a context object, an
`AssembledContext` test never needs a template, and this class's own
tests can assert the final assembled string without needing a live model.
"""

from __future__ import annotations

from llm.base_llm import LLMMessage
from llm.prompts.templates import PromptTemplate
from reasoning.context_assembler import AssembledContext


class PromptBuilder:
    def build(self, template: PromptTemplate, *, context: AssembledContext, query: str) -> list[LLMMessage]:
        system_prompt = template.render_system_prompt()
        user_prompt = (
            f"CONTEXT:\n{context.render_for_prompt()}\n\n"
            f"QUESTION:\n{query}"
        )
        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
