"""
llm/providers/claude_provider.py

WHY THIS FILE EXISTS
---------------------
Real implementation of BaseLLM for Anthropic Claude models, via the
official `anthropic` Python SDK. This was a stub from Phase 1 through
Phase 5 (every method raised NotImplementedError) — Phase 6 is the first
phase with an actual reasoning layer to call it.

CONFIGURATION
-----------------
Reads `settings.ANTHROPIC_API_KEY` (falls back to the SDK's own
`ANTHROPIC_API_KEY` environment variable lookup if unset here) and
`settings.LLM_MODEL_NAME`. No credential is hardcoded anywhere in this
file or committed to the repository — see config/.env.example.

WHY generate() AND agenerate() ARE THIN
---------------------------------------------
Retry policy, timeout enforcement, and token-usage accounting are
deliberately NOT implemented here — that's `llm/llm_service.py`'s job
(see its docstring). This class's only responsibility is "translate
BaseLLM's generic interface into one real Anthropic API call and back" —
adding retry/timeout logic at this layer too would duplicate policy that
belongs in exactly one place, the same reasoning `retrieval/embedder.py`
gave for keeping `SentenceTransformerBackend` thin and putting caching/
batching policy in `EmbeddingService` instead.

TESTING DISCLOSURE
----------------------
This class is NOT exercised against the real Anthropic API in this
project's test suite — see docs/Phase6.md Section 18 for the full,
disclosed reason (no API credential configured in this build/test
environment). It is tested for construction and message-translation
correctness only; the actual HTTP call path is covered by
`tests/fakes.py::FakeLLMBackend`-based tests of everything built on top
of `BaseLLM`, exactly mirroring Phase 3's `SentenceTransformerBackend` /
`FakeEmbeddingBackend` split.
"""

from __future__ import annotations

import time
from typing import Any

from core.config import settings
from core.exceptions import LLMProviderError
from llm.base_llm import BaseLLM, LLMMessage, LLMResponse


class ClaudeProvider(BaseLLM):
    """Real provider for Anthropic Claude models, via the official SDK."""

    provider_name = "claude"

    def __init__(self, model_name: str | None = None, **config: Any) -> None:
        self.model_name = model_name or settings.LLM_MODEL_NAME
        self.config = config
        self._client = None
        self._async_client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            api_key = settings.ANTHROPIC_API_KEY or None  # None -> SDK falls back to env var lookup
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _get_async_client(self):
        if self._async_client is None:
            import anthropic

            api_key = settings.ANTHROPIC_API_KEY or None
            self._async_client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._async_client

    @staticmethod
    def _split_system_and_messages(messages: list[LLMMessage]) -> tuple[str, list[dict]]:
        """
        Anthropic's API takes a `system` prompt as a separate top-level
        parameter, not as a message with role="system" — this splits
        BaseLLM's generic message list into the two shapes the SDK expects.
        """
        system_parts = [m.content for m in messages if m.role == "system"]
        conversation = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        return "\n\n".join(system_parts), conversation

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        import anthropic

        system, conversation = self._split_system_and_messages(messages)
        client = self._get_client()

        started = time.perf_counter()
        try:
            response = client.messages.create(
                model=self.model_name,
                system=system or anthropic.NOT_GIVEN,
                messages=conversation,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except anthropic.APIError as exc:
            raise LLMProviderError(f"Claude API call failed: {exc}") from exc
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return LLMResponse(
            content=text,
            model_name=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason,
            raw_metadata={"latency_ms": elapsed_ms, "response_id": response.id},
        )

    async def agenerate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        import anthropic

        system, conversation = self._split_system_and_messages(messages)
        client = self._get_async_client()

        started = time.perf_counter()
        try:
            response = await client.messages.create(
                model=self.model_name,
                system=system or anthropic.NOT_GIVEN,
                messages=conversation,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except anthropic.APIError as exc:
            raise LLMProviderError(f"Claude API call failed: {exc}") from exc
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return LLMResponse(
            content=text,
            model_name=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason,
            raw_metadata={"latency_ms": elapsed_ms, "response_id": response.id},
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Claude's API is chat/completion-only — it does not expose an
        # embeddings endpoint (that's SentenceTransformerBackend's job,
        # see retrieval/embedder.py). Raising explicitly here is the
        # correct behavior per BaseLLM's own docstring, not a gap.
        raise NotImplementedError(
            "ClaudeProvider does not implement embeddings — use retrieval.embedder.EmbeddingService instead."
        )
