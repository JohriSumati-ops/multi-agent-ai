"""
llm/base_llm.py — THE MODEL ABSTRACTION LAYER

WHY THIS FILE EXISTS
---------------------
Requirement added after Phase 0 review: no agent or service should ever
import a specific model SDK (anthropic, together, ollama, ...) directly.
Every call to "generate text from an LLM" must go through this interface,
so swapping Claude for a local Llama model — or routing different agents to
different models — is a configuration change, not a code change.

NO MODEL IS IMPLEMENTED HERE. This file defines the contract only. See
llm/providers/ for provider stub classes that raise NotImplementedError,
ready for Phase 2+ to fill in.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
This is the Strategy pattern (interchangeable algorithm implementations
behind one interface) combined with Dependency Inversion: high-level code
(agents, services) depends on the `BaseLLM` abstraction, never on a
concrete provider — the concrete provider is injected at the composition
root (see core/config.py's DEFAULT_LLM_PROVIDER).

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Every agent's `run()` implementation will call `self.llm.generate(...)`
where `self.llm: BaseLLM` was injected by the Supervisor/service layer.
Which concrete provider `self.llm` actually is depends on
`settings.DEFAULT_LLM_PROVIDER` and a not-yet-written `llm/factory.py`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    """One turn in a conversation sent to an LLM provider."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """
    Normalized response shape returned by every provider, regardless of
    that provider's native API response format.
    """

    content: str
    model_name: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class BaseLLM(ABC):
    """
    Abstract interface every LLM provider must implement.

    Concrete subclasses: ClaudeProvider, LlamaProvider, MistralProvider,
    QwenProvider, GemmaProvider (see llm/providers/) — all currently stubs
    that raise NotImplementedError, per the "no model implementation yet"
    Phase 1 constraint.
    """

    #: Set by each subclass; used for logging and AgentExecutionLog metadata.
    provider_name: str = "base"

    @abstractmethod
    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """Synchronously generate a completion for the given message history."""
        raise NotImplementedError

    @abstractmethod
    async def agenerate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """Async variant of `generate` — required for FastAPI's async routes."""
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Return embeddings for a batch of texts, if this provider supports
        embeddings. Not every provider needs to (a pure chat model might
        not) — providers that don't support it should raise
        `NotImplementedError` explicitly rather than silently returning
        nonsense.
        """
        raise NotImplementedError
