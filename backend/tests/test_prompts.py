"""
tests/test_prompts.py
"""

from __future__ import annotations

from llm.prompts.builder import PromptBuilder
from llm.prompts.registry import PromptRegistry, PromptTemplateNotFoundError, get_prompt_registry
from llm.prompts.templates import PromptTemplate, RESEARCH_QUERY_TEMPLATE, StructuredAnswer
from reasoning.context_assembler import AssembledContext, ContextItem


def test_structured_answer_requires_confidence_in_bounds() -> None:
    import pydantic

    try:
        StructuredAnswer(answer="x", confidence=1.5, reasoning_summary="y")
        assert False, "expected a validation error"
    except pydantic.ValidationError:
        pass


def test_structured_answer_defaults() -> None:
    answer = StructuredAnswer(answer="x", confidence=0.5, reasoning_summary="y")
    assert answer.sources_used == []
    assert answer.memory_references == []


def test_prompt_template_renders_system_and_format_instruction() -> None:
    template = PromptTemplate(name="t", version=1, system_instruction="Be helpful.", output_format_instruction="Return JSON.")
    rendered = template.render_system_prompt()
    assert "Be helpful." in rendered
    assert "Return JSON." in rendered


def test_registry_register_and_get_latest_version() -> None:
    registry = PromptRegistry()
    v1 = PromptTemplate(name="t", version=1, system_instruction="v1", output_format_instruction="fmt")
    v2 = PromptTemplate(name="t", version=2, system_instruction="v2", output_format_instruction="fmt")
    registry.register(v1)
    registry.register(v2)

    assert registry.get("t").version == 2  # latest, when unspecified
    assert registry.get("t", version=1).version == 1


def test_registry_raises_for_unknown_template() -> None:
    registry = PromptRegistry()
    try:
        registry.get("nonexistent")
        assert False, "expected PromptTemplateNotFoundError"
    except PromptTemplateNotFoundError:
        pass


def test_default_registry_includes_builtin_templates() -> None:
    registry = get_prompt_registry()
    assert "research_query" in registry.list_names()
    assert "question_answering" in registry.list_names()
    assert "summarization" in registry.list_names()


def test_prompt_builder_includes_context_and_query() -> None:
    context = AssembledContext(query="q")
    context.items.append(
        ContextItem(source_type="document_chunk", source_id="c1", title="Notes", text="Trees are hierarchical.", relevance_score=0.9)
    )
    messages = PromptBuilder().build(RESEARCH_QUERY_TEMPLATE, context=context, query="Explain trees")

    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert "Trees are hierarchical." in messages[1].content
    assert "Explain trees" in messages[1].content
    assert "c1" in messages[1].content  # chunk_id visible for the model to cite


def test_prompt_builder_handles_empty_context() -> None:
    context = AssembledContext(query="q")
    messages = PromptBuilder().build(RESEARCH_QUERY_TEMPLATE, context=context, query="anything")
    assert "No relevant context" in messages[1].content
