"""
tests/test_embedding_agent.py

Exercises the first Deep Learning based agent through the same
`BaseAgent.run()` machinery Phase 2's agents used, proving the Template
Method design generalizes to an agent whose `execute()` calls a model
(here, `FakeEmbeddingBackend` — see docs/Phase3.md Section 19).
"""

from __future__ import annotations

from agents.embedding_agent import ChunkEmbeddingInput, EmbeddingAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError


def test_embedding_agent_produces_one_result_per_chunk() -> None:
    context = TaskContext(original_query="")
    context.intermediate_results["chunks_to_embed"] = [
        ChunkEmbeddingInput(chunk_id="c1", text="Binary trees support O(log n) lookup."),
        ChunkEmbeddingInput(chunk_id="c2", text="Graphs generalize trees by allowing cycles."),
    ]
    result = EmbeddingAgent().run(context)

    assert result.success is True
    assert len(result.output) == 2
    assert result.output[0].chunk_id == "c1"
    assert result.output[1].chunk_id == "c2"
    assert result.output[0].vector.shape[0] == result.output[0].dimension


def test_embedding_agent_handles_empty_input() -> None:
    context = TaskContext(original_query="")
    context.intermediate_results["chunks_to_embed"] = []
    result = EmbeddingAgent().run(context)

    assert result.success is True
    assert result.output == []


def test_embedding_agent_fails_gracefully_on_missing_input() -> None:
    context = TaskContext(original_query="")
    # Deliberately omit 'chunks_to_embed'.
    result = EmbeddingAgent().run(context)

    assert result.success is False
    assert result.error_code == "validation_error"


def test_embedding_agent_validate_input_rejects_wrong_type() -> None:
    context = TaskContext(original_query="")
    context.intermediate_results["chunks_to_embed"] = ["not a ChunkEmbeddingInput"]
    try:
        EmbeddingAgent().validate_input(context)
        assert False, "expected ValidationAppError"
    except ValidationAppError:
        pass


def test_embedding_agent_stores_results_on_context() -> None:
    context = TaskContext(original_query="")
    context.intermediate_results["chunks_to_embed"] = [ChunkEmbeddingInput(chunk_id="c1", text="hello")]
    EmbeddingAgent().run(context)

    assert "embedding_results" in context.intermediate_results
    assert len(context.intermediate_results["embedding_results"]) == 1


def test_embedding_agent_records_execution_trace() -> None:
    context = TaskContext(original_query="")
    context.intermediate_results["chunks_to_embed"] = [ChunkEmbeddingInput(chunk_id="c1", text="hello")]
    EmbeddingAgent().run(context)

    assert context.execution_trace[-1]["agent"] == "embedding_agent"
    assert context.execution_trace[-1]["summary"] == "completed successfully"
