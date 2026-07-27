"""
tests/fakes.py

WHY THIS FILE EXISTS
---------------------
`retrieval/embedder.py::EmbeddingService` depends on the `EmbeddingBackend`
interface, not on `sentence_transformers.SentenceTransformer` directly
(see that module's docstring for the full rationale). `FakeEmbeddingBackend`
is the test-only implementation of that interface: deterministic,
dependency-free, and fast, so the entire Phase 3 test suite (caching,
batching, FAISS integration, ranking, the API layer) can run without
downloading or loading a real transformer model.

DETERMINISM
--------------
Each text is hashed (SHA-256) and the hash bytes are used to seed a NumPy
random generator, producing a reproducible pseudo-random unit vector for
that exact text. This gives the fake backend a property real embeddings
also have — identical input always produces identical output — which is
what several cache-behavior tests rely on, without needing the vectors to
carry any real semantic meaning.
"""

from __future__ import annotations

import hashlib

import numpy as np

FAKE_EMBEDDING_DIMENSION = 32


class FakeEmbeddingBackend:
    """Deterministic, dependency-free stand-in for a real embedding model."""

    def __init__(self, dimension: int = FAKE_EMBEDDING_DIMENSION) -> None:
        self.dimension = dimension
        self.encode_call_count = 0
        self.total_texts_encoded = 0

    def encode(self, texts: list[str]) -> np.ndarray:
        self.encode_call_count += 1
        self.total_texts_encoded += len(texts)

        vectors = np.empty((len(texts), self.dimension), dtype=np.float32)
        for i, text in enumerate(texts):
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(digest[:8], byteorder="big", signed=False)
            rng = np.random.default_rng(seed)
            vector = rng.normal(size=self.dimension).astype(np.float32)
            vector /= np.linalg.norm(vector)  # L2-normalize, matching the real backend's behavior
            vectors[i] = vector
        return vectors


class FakeLLMBackend:
    """
    Deterministic, dependency-free stand-in for `llm.providers.claude_provider.ClaudeProvider`
    — see docs/Phase6.md Section 18 for why the real provider can't be
    exercised in this build/test environment (no configured API
    credential), mirroring `FakeEmbeddingBackend`'s identical rationale
    for the embedding model in Phase 3.

    Returns a canned, valid `StructuredAnswer`-shaped JSON string by
    default, so every component built on top of `BaseLLM` (PromptBuilder,
    LLMService, ResponseValidator, SourceGrounding, CitationInjector,
    the five Phase 6 agents) can be tested end-to-end without a real
    model call. `queued_responses` lets a test override this for
    failure/retry/malformed-output scenarios.
    """

    provider_name = "fake"

    def __init__(self, model_name: str = "fake-model") -> None:
        self.model_name = model_name
        self.call_count = 0
        self.last_messages: list = []
        self.queued_responses: list = []  # list[LLMResponse | Exception], consumed in order
        self.queued_exception: Exception | None = None

    def _next_response(self, messages: list) -> "LLMResponse":
        from llm.base_llm import LLMResponse

        self.call_count += 1
        self.last_messages = messages

        if self.queued_responses:
            next_item = self.queued_responses.pop(0)
            if isinstance(next_item, Exception):
                raise next_item
            return next_item

        if self.queued_exception is not None:
            exc, self.queued_exception = self.queued_exception, None
            raise exc

        default_json = (
            '{"answer": "This is a fake answer grounded in the provided context.", '
            '"sources_used": [], "confidence": 0.8, '
            '"reasoning_summary": "Fake reasoning summary.", "memory_references": []}'
        )
        return LLMResponse(
            content=default_json,
            model_name=self.model_name,
            input_tokens=50,
            output_tokens=20,
            finish_reason="end_turn",
        )

    def generate(self, messages: list, *, temperature: float = 0.7, max_tokens: int = 1024, **kwargs) -> "LLMResponse":
        return self._next_response(messages)

    async def agenerate(
        self, messages: list, *, temperature: float = 0.7, max_tokens: int = 1024, **kwargs
    ) -> "LLMResponse":
        return self._next_response(messages)

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("FakeLLMBackend does not implement embeddings.")
