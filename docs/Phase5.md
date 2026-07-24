# Phase 5 — The Intelligence Layer (Orchestration)

**Status:** Written before implementation, per the mandatory Phase 5 process.

---

## 1. Multi-Agent Systems

A multi-agent system decomposes a large capability into several small,
independently testable units (agents), each responsible for one thing,
coordinated by something that decides *which* agents run, *in what order*,
and *what to do with their output*. Phases 2-4 already built three real
agents (`PDFParsingAgent`, `MetadataExtractionAgent`, `EmbeddingAgent`) —
but nothing coordinates them generically yet. Each one is invoked by
hand-written procedural code (`document_processing/pipeline.py`) that
hardcodes the sequence "parse, then extract metadata, then chunk, then
embed." That code works, and Phase 5 does not replace it — but it cannot
scale to Phase 6's agents (Literature Review, Writing, Citation, ...),
because every new agent would mean editing that pipeline function by hand.
Phase 5 builds the piece that makes adding agent #4, #5, #20 a matter of
*registering* them, not rewriting orchestration code.

## 2. Supervisor Architecture

The Supervisor is the one component allowed to decide "what should happen
next" — and, critically, the *only* thing it does. Per the explicit
constraint in this phase's brief, the Supervisor never parses a document,
never embeds a chunk, never answers a question. It receives a goal,
consults the `AgentRegistry` to see what capabilities exist, builds an
`ExecutionContext` (Section 6), produces an `ExecutionPlan` (Section 5),
and hands that plan to the `WorkflowEngine` (Section 8) to actually run.
This is a strict separation: the Supervisor plans, the engine executes,
the agents do the work. Conflating any two of those three roles is exactly
what makes a system hard to extend — the Supervisor doesn't need to change
when a new agent is added, and the engine doesn't need to change when a
new planning strategy is added.

## 3. Agent Orchestration

"Orchestration" here means: given a goal, determine an ordered (and
partially parallel) sequence of agent invocations, execute them, handle
failures without crashing the whole request, and produce one coherent
result plus a full explanation of what happened and why. This is
infrastructure, not intelligence in the LLM sense — every decision the
orchestration layer makes in this phase is rule-based and inspectable, not
learned or model-driven, which is the explicit "no LLM reasoning yet"
constraint. Section 4 explains exactly how planning works without an LLM.

## 4. Task Planning (Without an LLM)

Real task planning ordinarily means "figure out what steps solve this goal"
— a job LLMs are good at, and one this phase is explicitly forbidden from
using an LLM for. The planning this phase implements instead is
**capability-driven, declarative planning**: a goal specifies which
*capabilities* it needs (e.g., `["parse_document", "extract_metadata",
"generate_embeddings"]`), and `PlanBuilder` (Section 5) looks up which
registered agent provides each capability, and orders tasks according to
each capability's declared dependencies (a capability like
`generate_embeddings` declares that it depends on `parse_document` having
already run). This is deterministic, inspectable, and testable — exactly
what "no LLM reasoning" requires, and it is a real, common pattern in
production orchestration systems (Airflow DAGs, CI/CD pipeline configs)
that long predates LLM-based planning.

## 5. Message Passing

Per this phase's explicit requirement, agents never call each other
directly — no agent instance holds a reference to another agent instance.
All coordination flows through the `MessageBus` (Section 9): the
`WorkflowEngine` publishes `TASK_STARTED`/`TASK_COMPLETED`/`TASK_FAILED`/
`PROGRESS` messages as it drives execution, and anything that cares
(`ExecutionStateManager`, `EventLogger`) subscribes rather than being
called directly by the engine. This is the same Observer-pattern
discipline that keeps `middleware/error_handler.py` decoupled from every
route in the API layer (Phase 1) — nothing that produces an event needs to
know who's listening.

## 6. Context Building

Before the Supervisor can plan anything, it needs to know what's already
known: what's in working memory for this request, what short-term/
long-term memory exists for this user, what documents are semantically
relevant to the request, the raw request text, and recent conversation
history. `ContextBuilder` collects all of this into one
`ExecutionContext` object by calling Phase 3/4's existing services
(`MemoryManager`, `SemanticSearchService`) — it introduces no new memory or
retrieval logic of its own, per this project's established rule (Phase 4's
"do not duplicate embedding logic") extended here to "do not duplicate
memory/retrieval logic."

## 7. Execution Graph

An `ExecutionPlan` is a directed acyclic graph (DAG) of `Task` objects,
each declaring which other tasks it depends on. Representing this as an
explicit graph (rather than a flat ordered list) is what makes parallel
execution possible: two tasks with no dependency relationship between them
can run concurrently, and the `AgentScheduler` (Section 10) is the
component that computes which tasks are eligible to run at any given
point by checking whether all of a task's dependencies have completed.

## 8. Task Lifecycle

Every `Task` moves through a fixed set of states:

```
QUEUED -> RUNNING -> COMPLETED
                   -> FAILED -> RETRYING -> RUNNING (loop, up to max retries)
                              -> FAILED (retries exhausted)
QUEUED -> CANCELLED   (if cancelled before it starts)
RUNNING -> CANCELLED  (if cancelled mid-flight)
QUEUED -> WAITING     (blocked on an unfinished dependency)
```

`ExecutionStateManager` (Section 11) is the single source of truth for
which state every task is currently in, and validates that only legal
transitions occur (e.g., a `COMPLETED` task can never transition back to
`RUNNING`).

## 9. Agent Registry

The Supervisor never constructs an agent directly (`PDFParsingAgent()`) —
it asks the `AgentRegistry` for "whichever agent provides capability X."
This one indirection is what makes agents replaceable: swapping which
concrete class provides `generate_embeddings` is a `registry.register()`
call, not a change anywhere in the Supervisor or WorkflowEngine. The
registry also exposes `health()` (can this agent currently run — e.g., is
its underlying model loaded) and `capabilities()` (introspection for the
planner), following the same "ask the abstraction, not the concrete
class" discipline as Phase 1's `BaseLLM`/`BaseAgent` interfaces.

## 10. Workflow Engine

The `WorkflowEngine` is the only component that actually invokes an
agent's `run()` method. It consumes an `ExecutionPlan`, asks the
`AgentScheduler` which tasks are currently runnable (dependencies
satisfied), executes them — sequentially or, when a scheduling "wave"
contains multiple independent tasks, in parallel via a thread pool (agents
here are lightweight, I/O-adjacent classical/DL agents, not GPU-bound
training jobs, so a thread pool is the right tool, not a process pool) —
applies retry policy on failure, enforces per-task timeouts, and continues
executing whatever remains runnable even if one branch of the graph fails
(partial completion / graceful degradation), rather than aborting the
entire plan.

## 11. Failure Recovery

Three distinct mechanisms, not one:
- **Retries**: a failed task is retried up to `Task.max_retries` times,
  with a short fixed backoff between attempts — appropriate for this
  phase's classical/DL agents, where failures are usually transient
  (a corrupted file, a momentary resource issue) rather than requiring
  exponential backoff tuned for a flaky network service.
- **Fallback / graceful degradation**: when a task exhausts its retries,
  the `WorkflowEngine` marks it `FAILED`, marks every task that depended
  on it `SKIPPED` (not silently dropped — recorded, with a reason), and
  **continues executing every other independent branch of the plan**. A
  plan with 5 independent tasks where 1 fails still returns 4 real
  results, not zero.
- **Partial completion**: `WorkflowEngine.execute()` always returns a
  result, listing exactly which tasks succeeded, failed, or were skipped
  — there is no "the whole plan threw an exception" failure mode.

## 12. Explainability

Every execution produces a `DecisionTrace`: which agent was selected for
each task and why (which capability match), which agents were *available
but not selected* and why not, the full task timeline (start/end times per
task), each task's confidence (from its underlying `AgentResult`, Phase
1's Confidence Framework — populated for real, by this system, for a
fourth time now), and which memory/retrieval sources fed the execution
context. This directly reuses `schemas/explainability.py`'s `Explanation`
shape from Phase 1, rather than inventing a parallel structure.

## 13. Why This Architecture Scales

Every piece of new capability Phase 6 adds (a Literature Review Agent, a
Citation Agent, ...) requires exactly one new step: implement `BaseAgent`
and call `registry.register()`. Nothing in `SupervisorAgent`,
`WorkflowEngine`, `AgentScheduler`, or `PlanBuilder` needs to change,
because none of them know about concrete agent classes — they only know
about capabilities and the `BaseAgent`/`AgentResult` interfaces Phase 1
already established. This is Dependency Inversion applied at the system
level, not just the class level.

## 14. Why This Architecture Is Modular

Each of the twelve components in Section headers above has exactly one
responsibility and depends only on abstractions below it:
`AgentRegistry` doesn't know about `WorkflowEngine`; `WorkflowEngine`
doesn't know about `ContextBuilder`; `ContextBuilder` doesn't know about
`SupervisorAgent`. `SupervisorAgent` is the only component that composes
all of them — and even it does so through constructor-injected
dependencies (Dependency Injection, exactly as `api/deps.py` has done for
every service since Phase 1), so each piece is independently unit
testable and independently replaceable.

---

## 15. Folder / File Additions

No folder renamed. One new top-level package (orchestration is a genuinely
new subsystem, not an extension of `agents/`, `services/`, or `core/` —
each of those already has an established, different responsibility):

```
orchestration/
├── __init__.py
├── task.py               Task, TaskStatus, TaskPriority, TaskResult, TaskError
├── agent_registry.py      AgentRegistry (singleton — see Section 9)
├── execution_plan.py      ExecutionPlan, PlanBuilder (capability-driven planning, Section 4)
├── context_builder.py     ContextBuilder, ExecutionContext
├── message_bus.py         MessageBus, Message, MessageType (Section 5)
├── agent_scheduler.py     AgentScheduler (dependency-wave computation, Section 7)
├── state_manager.py       ExecutionStateManager (Section 8)
├── workflow_engine.py     WorkflowEngine (Section 10)
├── explainability.py      DecisionTrace, ExplainabilityBuilder (Section 12)
└── event_logger.py        EventLogger (persists orchestration events)

models/
└── orchestration_event.py   NEW — OrchestrationEvent (mirrors AgentExecutionLog's shape)

repositories/
└── orchestration_event_repository.py   NEW

agents/
└── supervisor_agent.py    NEW — the one new concrete agent (BaseAgent subclass)

services/
└── orchestration_service.py   NEW — thin API-facing wrapper composing the above for api/deps.py
```

## 16. What Phase 5 Deliberately Does Not Include

No Literature Review Agent, Writing Agent, Quiz Agent, Citation Agent,
Research Planner, Presentation Agent, or Gap Analysis Agent — those are
Phase 6. This phase's `SupervisorAgent` is demonstrated and tested against
the three agents that already exist (PDF Parsing, Metadata Extraction,
Embedding), proving the orchestration layer works end-to-end, without
building any new domain agent. It does not replace Phase 2's
`document_processing/pipeline.py` — that hand-written pipeline keeps
working exactly as it did, untouched; the orchestration layer is new,
parallel infrastructure that Phase 6's agents will use, not a mandatory
migration of Phase 2/3's already-tested code paths.

## 17. Testing Strategy

Same layered approach as every previous phase: pure unit tests for
`Task`/`TaskStatus` transitions, `AgentRegistry`, `PlanBuilder`,
`MessageBus`, and `AgentScheduler` (no database, no agents actually
running); integration tests for `WorkflowEngine` executing a real plan
against the three existing registered agents (using temp files, exactly
like Phase 2/3's agent tests); and a full `SupervisorAgent` test exercising
the complete goal -> context -> plan -> execution -> explainability
pipeline. Regression: the full Phase 1-4 suite (200 tests) must stay green.
