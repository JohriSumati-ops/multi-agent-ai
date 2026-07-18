"""
llm/providers/gemma_provider.py

WHY THIS FILE EXISTS
---------------------
Stub implementation of BaseLLM for Google Gemma models.
Provided now so that the model abstraction layer has a concrete,
importable class per target provider from day one -- future phases fill in
the method bodies without touching any calling code (agents, services), and
without changing this file's public interface.

NO MODEL CALLS ARE IMPLEMENTED. Every method raises NotImplementedError by
design, per the Phase 1 scope ("Do NOT implement any model").

HOW FUTURE PHASES WILL USE THIS
---------------------------------
llm/factory.py (not yet written) will map settings.DEFAULT_LLM_PROVIDER ==
"gemma" to GemmaProvider, constructed with whatever
credentials/config that provider needs, and return it as a BaseLLM to
calling agents.
"""

from __future__ import annotations

from typing import Any

from llm.base_llm import BaseLLM, LLMMessage, LLMResponse


class GemmaProvider(BaseLLM):
    """Stub provider for Google Gemma models"""

    provider_name = "gemma"

    def __init__(self, model_name: str = "gemma-default", **config: Any) -> None:
        self.model_name = model_name
        self.config = config

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        raise NotImplementedError(
            f"{self.provider_name} provider is not implemented yet (Phase 1 is architecture-only)."
        )

    async def agenerate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        raise NotImplementedError(
            f"{self.provider_name} provider is not implemented yet (Phase 1 is architecture-only)."
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            f"{self.provider_name} provider does not implement embeddings yet."
        )
