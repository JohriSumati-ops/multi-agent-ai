"""
agents/embedding_agent.py — THE FIRST DEEP LEARNING BASED AGENT

WHY THIS FILE EXISTS
---------------------
Phase 2 built two agents (PDF Parsing, Metadata Extraction) that are both
classical/rule-based — no learned model runs inside either. This is the
first agent whose `execute()` step invokes an actual neural network
(`retrieval/embedder.py::EmbeddingService`, backed by a transformer). It
follows the exact same `BaseAgent` Template Method shape Phase 2
established: this class only implements `validate_input`, `execute`, and
`validate_output` — timing, logging, and error containment are inherited
from Phase 1's `run()`.

RESPONSIBILITIES (per the Phase 3 spec)
--------------------------------------------
Receive cleaned chunks -> generate embeddings -> validate vectors -> return
embedding results. Validation happens twice, deliberately at two different
layers: `EmbeddingService._validate_vectors` checks the raw numerical
output (shape, finiteness) immediately after the model call; this agent's
`validate_output` checks the *result count* matches the *input count* —
a distinct, agent-level invariant not because the numbers could be wrong
(that's already been checked) but because a partial batch failure
upstream should never silently produce fewer embeddings than chunks
without the caller knowing.

HOW THIS PREPARES FOR PHASE 4+
-----------------------------------
A future Knowledge Graph Agent's concept-extraction step could reuse the
same `EmbeddingService` singleton this agent uses (e.g., to embed
extracted concept names for similarity-based deduplication) — the
singleton pattern means that reuse costs nothing extra.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError
from retrieval.embedder import EmbeddingService


@dataclass
class ChunkEmbeddingInput:
    chunk_id: str
    text: str


@dataclass
class EmbeddingResult:
    chunk_id: str
    vector: np.ndarray
    dimension: int
    model_name: str


class EmbeddingAgent(BaseAgent):
    """
    Generates embeddings for a batch of cleaned chunks using the shared
    `EmbeddingService` singleton.

    Input contract: `context.intermediate_results["chunks_to_embed"]` must
    be a `list[ChunkEmbeddingInput]`. Output: `list[EmbeddingResult]`, in
    the same order as the input.
    """

    name = "embedding_agent"

    def validate_input(self, context: TaskContext) -> None:
        chunks = context.intermediate_results.get("chunks_to_embed")
        if chunks is None:
            raise ValidationAppError("EmbeddingAgent requires 'chunks_to_embed' in intermediate_results")
        if not isinstance(chunks, list) or not all(isinstance(c, ChunkEmbeddingInput) for c in chunks):
            raise ValidationAppError("'chunks_to_embed' must be a list[ChunkEmbeddingInput]")

    def execute(self, context: TaskContext) -> list[EmbeddingResult]:
        chunks: list[ChunkEmbeddingInput] = context.intermediate_results["chunks_to_embed"]
        if not chunks:
            return []

        service = EmbeddingService.get_instance()
        vectors = service.embed_texts([c.text for c in chunks])

        results = [
            EmbeddingResult(
                chunk_id=chunk.chunk_id,
                vector=vector,
                dimension=service.dimension,
                model_name=getattr(service.backend, "model_name", "unknown"),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]

        # Count invariant checked here (not in validate_output) because
        # both the input chunk count and the output result count are in
        # scope at this point without needing to stash state on `self` —
        # BaseAgent.validate_output only receives the output, by design,
        # to keep agents stateless/reentrant (see agents/base_agent.py).
        if len(results) != len(chunks):
            raise ValidationAppError(
                f"EmbeddingAgent produced {len(results)} results for {len(chunks)} input chunks"
            )

        context.intermediate_results["embedding_results"] = results
        return results

    def validate_output(self, output: list[EmbeddingResult]) -> None:
        for result in output:
            if result.vector is None or result.vector.shape[0] != result.dimension:
                raise ValidationAppError(
                    f"EmbeddingAgent produced an invalid vector for chunk {result.chunk_id}"
                )
            if not np.all(np.isfinite(result.vector)):
                raise ValidationAppError(
                    f"EmbeddingAgent produced a non-finite vector for chunk {result.chunk_id}"
                )
