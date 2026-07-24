"""
tests/test_supervisor_agent.py

Exercises the SupervisorAgent through BaseAgent.run() exactly like every
other agent test in this project — proving Phase 1's Template Method
design generalizes even to an agent that orchestrates other agents.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.supervisor_agent import SupervisorAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError
from models.document import DocumentFormat
from orchestration.agent_registry import AgentRegistry, get_agent_registry
from orchestration.task import TaskStatus


class _EchoAgent(BaseAgent):
    name = "echo_agent"

    def execute(self, context):
        return "echoed"


def test_supervisor_requires_goal() -> None:
    context = TaskContext(original_query="")
    context.intermediate_results["capabilities"] = ["echo"]
    result = SupervisorAgent(AgentRegistry()).run(context)
    assert result.success is False
    assert result.error_code == "validation_error"


def test_supervisor_requires_capabilities() -> None:
    context = TaskContext(original_query="")
    context.intermediate_results["goal"] = "do something"
    result = SupervisorAgent(AgentRegistry()).run(context)
    assert result.success is False


def test_supervisor_executes_a_simple_goal() -> None:
    registry = AgentRegistry()
    registry.register("echo", _EchoAgent)

    context = TaskContext(original_query="")
    context.intermediate_results["goal"] = "echo something"
    context.intermediate_results["capabilities"] = ["echo"]

    result = SupervisorAgent(registry).run(context)
    assert result.success is True
    assert result.output.plan.tasks[0].status == TaskStatus.COMPLETED


def test_supervisor_never_directly_touches_document_processing(tmp_path) -> None:
    """
    Confirms the Supervisor orchestrates the real Phase 2/3 agents via the
    registry rather than importing/calling document_processing modules
    itself — the entire point of this phase's "never perform research
    itself" constraint, verified concretely.
    """
    import agents.supervisor_agent as supervisor_module

    source = open(supervisor_module.__file__).read()
    assert "document_processing" not in source
    assert "PDFParsingAgent" not in source
    assert "MetadataExtractionAgent" not in source
    assert "EmbeddingAgent" not in source


def test_supervisor_orchestrates_real_document_pipeline_agents(tmp_path) -> None:
    registry = get_agent_registry()
    file_path = tmp_path / "notes.txt"
    file_path.write_text("Hash tables provide average O(1) lookup performance for key-value data.")

    context = TaskContext(original_query="")
    context.intermediate_results["goal"] = "process a document"
    context.intermediate_results["capabilities"] = ["parse_document", "extract_metadata"]
    context.intermediate_results["payload"] = {
        "file_path": str(file_path),
        "file_format": DocumentFormat.TXT,
        "original_filename": "notes.txt",
    }

    result = SupervisorAgent(registry).run(context)
    assert result.success is True
    sup_result = result.output
    assert all(t.status == TaskStatus.COMPLETED for t in sup_result.plan.tasks)
    assert sup_result.trace.explanation is not None


def test_supervisor_produces_decision_trace_with_not_selected_capabilities() -> None:
    registry = get_agent_registry()  # has parse_document, extract_metadata, generate_embeddings

    context = TaskContext(original_query="")
    context.intermediate_results["goal"] = "just parse"
    context.intermediate_results["capabilities"] = ["parse_document"]
    context.intermediate_results["payload"] = {}

    # parse_document will fail (no real file), but we only care about
    # the trace/explainability structure here, not success.
    result = SupervisorAgent(registry).run(context)
    sup_result = result.output
    assert "generate_embeddings" in sup_result.trace.agents_not_selected
    assert "extract_metadata" in sup_result.trace.agents_not_selected


def test_supervisor_output_fails_validation_for_empty_plan() -> None:
    from agents.supervisor_agent import SupervisorResult
    from orchestration.execution_plan import ExecutionPlan

    empty_plan = ExecutionPlan(goal="nothing", tasks=[])
    supervisor = SupervisorAgent(AgentRegistry())
    try:
        supervisor.validate_output(SupervisorResult(plan=empty_plan, trace=None))
        assert False, "expected ValidationAppError"
    except ValidationAppError:
        pass
