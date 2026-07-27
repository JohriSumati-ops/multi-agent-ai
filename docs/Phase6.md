# Phase 6 — LLM Intelligence & Research Reasoning Layer

**Status:** Written before implementation, per the mandatory Phase 6 process.

---

## 1. What Changes in This Phase

Every phase before this one was deliberately deterministic — classical
NLP (Phase 2), vector similarity math (Phase 3), rule-based memory
policy (Phase 4), capability-driven planning with zero free-text
understanding (Phase 5). This is the first phase where an actual language
model is called, and the first phase where output is genuinely
non-deterministic. Everything built so far doesn't get replaced by that —
it becomes the LLM's **input**. The `ResearchReasoningService` never
answers a question from the model's parametric knowledge alone; it
assembles retrieved chunks (Phase 3), relevant memory (Phase 4), and prior
orchestration context (Phase 5) into a bounded, ranked context window, and
the LLM's job is to reason *over that*, not to freelance.

## 2. Prompt Engineering

A prompt sent to the model here has a fixed shape, assembled by
`PromptBuilder`, not hand-written per call site:

1. A **system instruction** (from `PromptTemplate`) stating the model's
   role and, critically, its grounding constraint ("answer only using the
   provided sources; if the sources don't contain the answer, say so").
2. The **assembled context** (`ContextAssembler`'s output — ranked,
   deduplicated, budgeted chunks and memory).
3. The **user's question**.
4. An explicit **output format instruction** requiring a JSON object
   matching `StructuredAnswer`'s schema (Section 8).

Separating "prompt template" from "prompt instance" (a template plus the
request-specific data filled in) is what makes prompts versionable
(`PromptRegistry`, Section 9) and testable independently of any live model
call — a `PromptBuilder` test asserts the assembled prompt string contains
the right context, with no LLM involved at all.

## 3. LLM Orchestration

`LLMService` is the only thing in this codebase allowed to call a
`BaseLLM` backend (Phase 1's interface, five provider stubs, unimplemented
until now). Every reasoning agent goes through `LLMService`, never through
a provider directly — this is the exact same discipline Phase 3 applied to
`EmbeddingService` and FAISS, extended here to chat/completion calls.
`LLMService` adds what a raw provider call doesn't have on its own: retry
policy for transient failures, a timeout per call, and running token-usage
accounting persisted via `LLMUsageLog` (mirroring `AgentExecutionLog`'s
shape from Phase 1).

## 4. Grounding

"Grounding" means every factual claim in an answer must be traceable to a
specific piece of retrieved/remembered context, not the model's own
training data. This project enforces it in two layers, not one:

- **Prompt-level**: the system instruction explicitly forbids answering
  from outside the provided context and requires inline source
  references.
- **Post-hoc, code-level** (`SourceGrounding`): after the model responds,
  every `chunk_id` the model claims to have used is checked against the
  actual set of `chunk_id`s that were in the assembled context. A
  reference to a chunk that was never provided is impossible to fabricate
  past this check — it's not a prompting hope, it's a verifiable
  post-condition on the response.

## 5. Hallucination Mitigation

Beyond grounding (Section 4), `ResponseValidator` enforces: the response
must parse as valid `StructuredAnswer` JSON (a response that isn't even
structured correctly is rejected before it reaches a user, not
silently patched); `confidence` must fall in `[0, 1]`; and — the most
direct mitigation — if `ContextAssembler` finds no relevant chunks/memory
for a query, `ResearchReasoningService` **never calls the LLM at all** and
returns an explicit "insufficient context" response instead. An LLM asked
to answer with zero context is exactly what produces a fabricated,
unhallucinated-in-appearance-only answer — the cheapest and most reliable
mitigation is not asking that question in the first place.

## 6. Context Construction

`ContextAssembler` (in `reasoning/`) is the Context Layer this phase's
brief requires, and it introduces no new retrieval or memory logic —
per this project's established rule (Phase 4/5's "reuse, don't
duplicate"), it calls `SemanticSearchService` (Phase 3) and `MemoryManager`
(Phase 4) exactly as `orchestration/context_builder.py::ContextBuilder`
(Phase 5) already does, then applies four steps specific to LLM
consumption that `ContextBuilder` never needed:

1. **Ranking** — reuses `retrieval/ranking.py`'s scored, explainable
   ordering (Phase 3) rather than a new ranking scheme.
2. **Duplicate removal** — reuses `retrieval/ranking.py::deduplicate_candidates`
   directly; near-identical chunks (a known consequence of Phase 2's
   sliding-window chunking) shouldn't burn context-window budget twice.
3. **Token budgeting** — a hard cap (`LLM_CONTEXT_TOKEN_BUDGET`) on how
   much assembled context can enter the prompt; lower-ranked items are
   dropped once the budget is exhausted, highest-relevance first.
4. **Compression** — when a single chunk is large relative to the
   remaining budget, it's truncated to its first N tokens rather than
   dropped entirely, on the premise that the most relevant chunk's
   beginning is better than no chunk at all. This is a deliberately simple
   compression strategy (not a summarization model) — see Section 13 for
   why a learned compressor is future scope, not this phase's job.

## 7. Token Budgeting

Token counting here reuses Phase 2's documented, deliberate approximation
(`document_processing/nlp_preprocessor.count_words`) rather than a
model-specific tokenizer — the same reasoning Phase 2 gave for deferring a
real tokenizer applies again: `LLMService` is provider-agnostic, and a
real tokenizer is tied to one specific model's vocabulary. The word-count
approximation is conservative enough (real BPE tokens are usually *more*
numerous than words, not fewer) that budgeting against it errs toward
under-filling the context window, not overflowing it.

## 8. Structured Outputs

The model is asked to return exactly one JSON object per call, validated
against `StructuredAnswer`:

```
{
  "answer": str,
  "sources_used": [{"chunk_id": str, "document_title": str, "relevance": str}],
  "confidence": float,          # 0.0-1.0
  "reasoning_summary": str,      # short explanation of how the answer was derived
  "memory_references": [str],    # memory IDs that informed the answer, if any
}
```

`token_usage` and `latency_ms` are NOT part of the model's own output —
they're measured by `LLMService` around the call and merged in afterward,
since asking a model to self-report its own token count or latency is
unreliable by construction (it doesn't have privileged access to either).

## 9. Prompt Registry and Versioning

`PromptTemplate` objects are registered under a `(name, version)` key in
`PromptRegistry`. This exists for the same reason Phase 1's
`core/config.py` centralized settings: a prompt is a piece of the system's
behavior that changes independently of code, and pinning a specific
version at the call site (rather than always "whatever the latest template
is") is what makes a regression in prompt quality bisectable — exactly the
same value a database migration's version number provides for schema
changes.

## 10. Response Validation

`ResponseValidator` is the last gate before a response reaches
`ResearchReasoningService`'s caller. It never silently repairs a bad
response — an invalid response is either retried (bounded, via
`LLMService`'s retry policy) or surfaced as an explicit `LLMResponseError`
with the raw model output attached for debugging, never coerced into a
best-effort guess of what the model "probably meant."

## 11. Citation Generation

`CitationInjector` post-processes a validated `StructuredAnswer`,
resolving each `sources_used[].chunk_id` against the actual
`DocumentChunk`/`Memory` rows it came from (via the existing repositories
— no new lookup logic) to attach human-readable citation text
(document title, page number where available) — the model outputs an ID;
this project resolves that ID to a real, checkable citation, rather than
trusting the model to format citation text correctly itself.

## 12. Reasoning Pipeline

```
User query
     │
     ▼
ContextAssembler.assemble()      — rank, dedupe, budget, compress (Section 6)
     │
     ├── empty? ──▶ return "insufficient context" (no LLM call — Section 5)
     │
     ▼
PromptBuilder.build()             — template + context + query -> prompt (Section 2)
     │
     ▼
LLMService.generate_structured()  — retry/timeout-wrapped call (Section 3)
     │
     ▼
ResponseValidator.validate()      — schema + confidence bounds (Section 10)
     │
     ▼
SourceGrounding.verify()          — every cited chunk_id was actually provided (Section 4)
     │
     ▼
CitationInjector.inject()         — resolve chunk_ids to real citations (Section 11)
     │
     ▼
StructuredAnswer + full explainability trace returned to caller
```

## 13. Architecture / Folder Additions

No folder renamed. Additions only:

```
llm/
├── base_llm.py              EXISTING (Phase 1) — unmodified interface
├── llm_service.py            NEW — retry/timeout/token-accounting wrapper over BaseLLM
├── factory.py                 NEW — settings.DEFAULT_LLM_PROVIDER -> concrete BaseLLM instance
├── providers/
│   └── claude_provider.py    IMPLEMENTED FOR REAL (was a stub since Phase 1)
└── prompts/
    ├── templates.py            PromptTemplate, StructuredAnswer schema
    ├── builder.py               PromptBuilder
    └── registry.py               PromptRegistry (name+version -> template)

reasoning/                     NEW top-level package (mirrors orchestration/'s Phase 5 precedent
│                                — a genuinely new subsystem, not an extension of agents/services/core/)
├── context_assembler.py       ContextAssembler (Section 6)
├── response_validator.py       ResponseValidator (Section 10)
├── source_grounding.py          SourceGrounding (Section 4)
├── citation_injector.py          CitationInjector (Section 11)
├── research_synthesis.py          multi-document evidence aggregation, conflict detection, consensus
└── research_reasoning_service.py   the pipeline orchestrator (Section 12)

agents/
├── research_agent.py           NEW — BaseAgent subclass wrapping ResearchReasoningService
├── question_answering_agent.py  NEW
├── summarization_agent.py        NEW
├── citation_agent.py              NEW
└── reasoning_agent.py              NEW

models/
├── llm_usage_log.py            NEW — token accounting (mirrors AgentExecutionLog)
└── research_response.py         NEW — persisted Q&A history

repositories/
├── llm_usage_log_repository.py
└── research_response_repository.py

services/
└── research_service.py         NEW — thin API-facing wrapper (mirrors services/orchestration_service.py)

schemas/
└── research.py                  NEW — API request/response contracts

api/routes/
└── research.py                   NEW — 5 endpoints (Section 16)
```

## 14. The Five New Agents, and Why Five (Not One)

Per this phase's explicit requirement, and consistent with every prior
agent this project has built (one class, one responsibility):

- **`ResearchAgent`** — the general-purpose entry point: runs the full
  pipeline (Section 12) for an open research question.
- **`QuestionAnsweringAgent`** — narrower: answers a specific question
  against a specific, already-known document/context scope (no broad
  multi-document synthesis step).
- **`SummarizationAgent`** — condenses retrieved/remembered context
  without necessarily answering a question — "what does this document
  say," not "what is the answer to X."
- **`CitationAgent`** — standalone access to `CitationInjector` +
  `SourceGrounding` for a caller that already has a draft answer and
  needs it grounded/cited (e.g., a future Writing Agent's output).
- **`ReasoningAgent`** — standalone access to `research_synthesis.py`'s
  multi-document conflict detection / consensus generation, for a caller
  that wants evidence *analysis* without necessarily wanting a
  natural-language answer synthesized from it.

Each is a thin `BaseAgent` subclass wrapping one reasoning-layer
component — following exactly the "thin agent, real logic lives one layer
down" shape Phase 2's `PDFParsingAgent` established.

## 15. Multi-Document Synthesis, Conflict Detection, Consensus

`research_synthesis.py` operates on the ranked, deduplicated evidence
`ContextAssembler` already produced. **Conflict detection** here is
lexical/structural, not semantic-model-driven: when two sources both have
high relevance to the query but their text contains negation patterns
relative to each other on shared key terms (a deliberately conservative
heuristic, documented in the module itself with its false-negative-prone
limitations acknowledged), they're flagged as a potential conflict for
the LLM's prompt to explicitly address ("Sources 2 and 4 may disagree —
address this in your answer") rather than silently picking one.
**Consensus generation** and final synthesis judgment is left to the LLM
itself, given the flagged evidence — detecting a *possible* disagreement
is a task classical heuristics can approximate; *resolving* it requires
the reasoning this phase's LLM layer exists to provide.

## 16. New API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /research/query` | Full pipeline: open research question -> synthesized, cited answer |
| `POST /research/answer` | Narrower question-answering against a specific document/context scope |
| `POST /research/summarize` | Summarize retrieved/remembered context without answering a specific question |
| `POST /research/reason` | Evidence analysis only (conflict/consensus) — no natural-language answer synthesis |
| `POST /research/explain` | Full explainability trace for a previously generated `ResearchResponse` |

## 17. Explainability

Every response's trace includes: which evidence was selected and why
(`ContextAssembler`'s ranking + `Explanation` from Phase 1's framework,
reused, not reinvented), which was available but excluded (below the
token budget or the similarity threshold — an explicit, not silent,
exclusion reason), which memory informed the answer, which documents were
consulted, and the exact agent sequence (reusing
`orchestration/explainability.py::DecisionTrace`'s shape from Phase 5
where the research pipeline is itself run through the orchestration layer
— see Section 19).

## 18. Testing Strategy — and a Necessary, Disclosed Limitation

Every reasoning-layer component that does NOT require a live model call
(`PromptBuilder`, `ContextAssembler`, `ResponseValidator`,
`SourceGrounding`, `CitationInjector`, `research_synthesis.py`) is fully
unit tested with real logic, no mocking beyond what the component
inherently needs.

**`LLMService` and the five LLM agents, however, cannot be tested against
a real model in this build environment.** This project's earlier phases
already disclosed one such gap plainly (Phase 3, Section 19: no network
path to `huggingface.co` for the embedding model). The same category of
constraint applies here: this sandbox has no configured Anthropic API
credential, and Phase 4's explicit "no external API" instruction — while
not repeated verbatim in this phase's brief — means no prior phase ever
established or tested a live credential path either. `ClaudeProvider` is
implemented for real, production use (a real HTTP call via the official
`anthropic` SDK, real retry/error handling) — but it is tested via a
`FakeLLMBackend` (deterministic, offline, returns canned structured JSON),
following exactly the same `EmbeddingBackend`/`FakeEmbeddingBackend`
pattern Phase 3 established for the identical reason. The seam
(`BaseLLM`) is the same interface point a real credential would plug into
with zero code changes anywhere else in the system — this is disclosed
here and in the final Phase 6 summary, not discovered by a user later.

## 19. Integration with the Orchestration Layer (Phase 5)

`ResearchAgent` (and its four siblings) are registered in Phase 5's
`AgentRegistry` under new capabilities (`research_query`,
`answer_question`, `summarize_context`, `inject_citations`,
`analyze_evidence`) — the Supervisor can orchestrate this phase's agents
exactly like Phase 2/3's, with zero changes to `WorkflowEngine`,
`PlanBuilder`, or `AgentScheduler`. This is the concrete payoff of Phase
5's "why this architecture scales" claim, now tested against a real new
agent family rather than only the three that existed when Phase 5 was
built.

## 20. Future Extensibility

- `LLMService`/`BaseLLM` means a second real provider (Llama via a local
  inference server, for instance) is a new `LlamaProvider` implementation
  plus one config change (`DEFAULT_LLM_PROVIDER`), not a rewrite.
- `research_synthesis.py`'s conflict-detection heuristic is intentionally
  simple and documented as a candidate for replacement by a learned
  entailment/contradiction model in a future phase — the interface
  (`detect_conflicts(evidence) -> list[Conflict]`) doesn't change either way.
- `PromptRegistry`'s versioning is what would support future A/B testing
  of prompt variants without touching any calling code.
