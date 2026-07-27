"""
llm/factory.py — THE LLM PROVIDER FACTORY

WHY THIS FILE EXISTS
---------------------
`llm/base_llm.py`'s docstring anticipated this file since Phase 1: "Which
concrete provider `self.llm` actually is depends on
`settings.DEFAULT_LLM_PROVIDER` and a not-yet-written `llm/factory.py`."
This is that file. It's the single place that maps a provider name string
to a concrete `BaseLLM` subclass — exactly the Simple Factory pattern
`document_processing/parsers/factory.py` already established for parser
selection in Phase 2, applied here to LLM provider selection.

WHY THIS IS NOT A SINGLETON
--------------------------------
Unlike `EmbeddingService` (expensive model load, worth sharing) or
`AgentRegistry` (shared registration state), a `BaseLLM` provider instance
here is cheap to construct — `ClaudeProvider.__init__` does no network
call, only lazy client construction on first real use (see its docstring).
Constructing a fresh provider per `LLMService` (itself constructed fresh
per request, like every other service) costs nothing and avoids any
shared-mutable-state concerns across concurrent requests.
"""

from __future__ import annotations

from core.config import settings
from core.exceptions import ConfigurationError
from llm.base_llm import BaseLLM

_PROVIDER_NAMES = {"claude", "llama", "mistral", "qwen", "gemma"}


def get_llm_provider(provider_name: str | None = None, *, model_name: str | None = None) -> BaseLLM:
    """
    Returns a fresh `BaseLLM` instance for the requested provider (or
    `settings.DEFAULT_LLM_PROVIDER` if unspecified). Only "claude" is a
    real implementation as of this phase — the other four remain the
    stub classes from Phase 1, and constructing one succeeds (their
    `__init__` still works) but calling `generate`/`agenerate` on them
    raises `NotImplementedError`, exactly as documented since Phase 1.
    """
    resolved_name = (provider_name or settings.DEFAULT_LLM_PROVIDER).lower()

    if resolved_name not in _PROVIDER_NAMES:
        raise ConfigurationError(
            f"Unknown LLM provider '{resolved_name}'. Valid options: {sorted(_PROVIDER_NAMES)}"
        )

    if resolved_name == "claude":
        from llm.providers.claude_provider import ClaudeProvider

        return ClaudeProvider(model_name=model_name)
    if resolved_name == "llama":
        from llm.providers.llama_provider import LlamaProvider

        return LlamaProvider(model_name=model_name or "llama-default")
    if resolved_name == "mistral":
        from llm.providers.mistral_provider import MistralProvider

        return MistralProvider(model_name=model_name or "mistral-default")
    if resolved_name == "qwen":
        from llm.providers.qwen_provider import QwenProvider

        return QwenProvider(model_name=model_name or "qwen-default")
    from llm.providers.gemma_provider import GemmaProvider

    return GemmaProvider(model_name=model_name or "gemma-default")
