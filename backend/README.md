# Multi-Agent Research Assistant — Backend (Phase 1 through Phase 6)

Production-quality backend. Phase 1 is pure architecture. Phase 2 adds
the Document Intelligence Pipeline. Phase 3 adds the Semantic Retrieval
Layer. Phase 4 adds the Memory System. Phase 5 adds the Intelligence
Layer (Supervisor/orchestration). **Phase 6 adds the first real LLM
reasoning layer** — question answering, research synthesis, and
citation-aware, grounded response generation, built entirely on top of
the deterministic infrastructure from Phases 1-5.

See `docs/Phase1.md` through `docs/Phase6.md` for full write-ups, and
`docs/PROJECT_STRUCTURE.md` / `docs/PHASE_1_LEARNING_NOTES.md` for the
original folder map and learning notes.

**Note on network access (Phase 3/4 embeddings, and now Phase 6 LLM
calls):** `sentence-transformers` downloads model weights from Hugging
Face Hub on first use, and `ClaudeProvider` (Phase 6) calls the real
Anthropic API and requires `ANTHROPIC_API_KEY` to be set. Neither is
required to run the test suite — see `docs/Phase3.md` Section 19 and
`docs/Phase6.md` Section 18 for the fake-backend testing strategy used
throughout this project for exactly this reason.

## LLM Reasoning Architecture (Phase 6)

`ResearchReasoningService` is the pipeline every research endpoint runs
through: assemble context (ranked, deduplicated, token-budgeted,
compressed — reusing Phase 3/4's retrieval and memory services
unmodified) → skip the LLM entirely if no relevant context exists (the
primary hallucination mitigation) → build a prompt from a versioned
template → call the model through `LLMService` (retries, timeout, token
accounting) → validate the response against a strict JSON schema → verify
every cited source was actually provided (never trust the model's word
for it) → resolve citations to real, checkable text.

```
POST /research/query {query, document_id?}
        │
        ▼
ContextAssembler.assemble()   — rank, dedupe, token-budget, compress (Phase 3/4 reused)
        │
        ├── empty? ──▶ return "insufficient context" (NO LLM call)
        │
        ▼
PromptBuilder.build()          — versioned template + context + query
        │
        ▼
LLMService.generate()           — retry + timeout + token accounting
        │
        ▼
ResponseValidator.validate()     — strict JSON schema, confidence bounds
        │
        ▼
SourceGrounding.verify()          — every cited chunk_id was actually provided
        │
        ▼
CitationInjector.inject()          — resolve chunk_ids to real citation text
        │
        ▼
Persisted as ResearchResponse, returned with full explainability
```

### Research API Endpoints (all require a Bearer token)

```
POST /api/v1/research/query               {query, document_id?}   full pipeline, multi-document synthesis
POST /api/v1/research/answer               {query, document_id?}   narrower Q&A, single-scope
POST /api/v1/research/summarize            {query, document_id?}   condense context, no specific answer
POST /api/v1/research/reason               {query, document_id?}   evidence conflict/consensus analysis only, NO LLM call
GET  /api/v1/research/explain/{response_id}                        full explainability trace for a past response
```

### Example

```bash
curl -X POST http://localhost:8000/api/v1/research/query \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query": "How does recursion handle base cases?"}'
```

### Configuration (Phase 6)

| Setting | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | Real credential required for live calls — falls back to the SDK's own env lookup |
| `LLM_MODEL_NAME` | `claude-sonnet-4-5` | Model used by `ClaudeProvider` |
| `LLM_MAX_TOKENS` / `LLM_TEMPERATURE` | `1024` / `0.3` | Default generation parameters |
| `LLM_TIMEOUT_SECONDS` / `LLM_MAX_RETRIES` | `60.0` / `2` | `LLMService`'s retry/timeout policy |
| `LLM_CONTEXT_TOKEN_BUDGET` | `4000` | Max approximate tokens of assembled context per prompt |
| `LLM_MIN_CONFIDENCE` | `0.0` | `ResponseValidator` rejects answers below this |

## Orchestration Architecture (Phase 5)

The `SupervisorAgent` never parses a document, embeds a chunk, or answers
a question — it only plans and coordinates. Given a goal and a list of
requested **capabilities** (not free-text intent — there's no LLM yet to
parse that), it:

1. Builds an `ExecutionContext` (working/short-term/long-term memory +
   semantic document retrieval + conversation history) via `ContextBuilder`
   — reusing Phase 3/4's services unmodified.
2. Builds an `ExecutionPlan` (a dependency graph of `Task`s) via
   `PlanBuilder`, resolving each capability to its registered agent
   through the `AgentRegistry` — the Supervisor never instantiates an
   agent class directly.
3. Hands the plan to the `WorkflowEngine`, which executes tasks in
   dependency order (parallelizing independent tasks via a thread pool),
   retries transient failures, enforces per-task timeouts, and propagates
   failure to dependents (`SKIPPED`) while letting independent branches
   keep running (partial completion).
4. Returns a `DecisionTrace`: which agent was selected for each task and
   why, which capabilities were available but not used, the full
   timeline, and overall confidence.

Every component communicates through an in-process `MessageBus` (agents
never call each other directly) — `ExecutionStateManager` and
`EventLogger` both subscribe to it independently, with zero awareness of
each other.

### Orchestration Flow

```
POST /orchestration/execute {goal, capabilities, payload}
        │
        ▼
ContextBuilder.build()          — memory + retrieval (Phase 3/4, reused)
        │
        ▼
PlanBuilder.build_plan()         — capability -> agent + dependency resolution (AgentRegistry)
        │
        ▼
WorkflowEngine.execute()          — dependency-ordered, parallel-where-possible execution
        │   publishes task.started / task.completed / task.failed / plan.completed
        ├──▶ ExecutionStateManager   (current state, in-memory)
        └──▶ EventLogger             (persisted history, OrchestrationEvent rows)
        │
        ▼
ExplainabilityBuilder.build_trace() — DecisionTrace returned to the client
```

### Orchestration API Endpoints (all require a Bearer token)

```
POST /api/v1/orchestration/execute        {goal, capabilities, payload?, request_text?}
GET  /api/v1/orchestration/capabilities    list every registered capability + its agent + dependencies
GET  /api/v1/orchestration/health          health check for every registered agent
```

### Example

```bash
curl -X POST http://localhost:8000/api/v1/orchestration/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "goal": "process a document",
    "capabilities": ["parse_document", "extract_metadata"],
    "payload": {"file_path": "/path/to/file.txt", "file_format": "txt", "original_filename": "file.txt"}
  }'
```

### Configuration (Phase 5)

| Setting | Default | Meaning |
|---|---|---|
| `ORCHESTRATION_MAX_WORKERS` | `4` | Thread pool size for parallel task execution within one dependency wave |
| `ORCHESTRATION_DEFAULT_TASK_TIMEOUT_SECONDS` | `30.0` | Default per-task timeout |
| `ORCHESTRATION_DEFAULT_MAX_RETRIES` | `2` | Default per-task retry count |

## Memory Architecture (Phase 4)

Four memory types, each with a distinct lifecycle:

| Type | Lifetime | Storage | Semantically searchable |
|---|---|---|---|
| Working | One request | In-process only, never persisted | No |
| Short-term | Configurable TTL (default 7 days) + size cap | PostgreSQL (`memory` table, `memory_type=short_term`) | No |
| Long-term | Indefinite (pruned explicitly, not by timer) | PostgreSQL + a dedicated FAISS index | Yes |
| Session | Until ended or TTL inactivity (default 30 min) | In-process, singleton, keyed by client-supplied `session_id` | No |

`MemoryManager` (`services/memory_manager.py`) is the single facade
composing all four — every memory endpoint goes through it, not through
the individual memory services directly.

### Memory Flow

```
Write:  MemoryManager.remember() -> dedup check -> Short/LongTermMemoryService.write()
                                                          │ (long-term only)
                                                          ▼
                                          EmbeddingService.embed_query() (Phase 3, reused)
                                                          │
                                                          ▼
                                          Memory FAISS index (separate from the document index)

Read:   GET /memory/history | /memory/recent  -> plain SQL, filtered by user + type + not-expired
Search: GET /memory/search  -> embed query -> memory FAISS search -> rank (retrieval/ranking.py, reused)
```

### Memory API Endpoints (all require a Bearer token)

```
POST   /api/v1/memory/store                        {content, persist_long_term?, importance_score?, conversation_id?, document_id?}
GET    /api/v1/memory/history?memory_type=&limit=   structured recall
GET    /api/v1/memory/recent?limit=                 most recent across all types
GET    /api/v1/memory/search?query=&top_k=&similarity_threshold=   semantic recall
GET    /api/v1/memory/session?session_id=           read session state
GET    /api/v1/memory/statistics                    usage/storage/access metrics
DELETE /api/v1/memory/session?session_id=           end a session
DELETE /api/v1/memory/history?memory_type=          delete memories (optionally filtered)
DELETE /api/v1/memory/prune?keep_top_n_long_term=    run expiration + pruning + archiving
POST   /api/v1/memory/clear                          danger zone: delete everything for this user
```

### Example: store then search

```bash
# Store a long-term memory (semantically indexed immediately)
curl -X POST http://localhost:8000/api/v1/memory/store \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content": "User consistently struggles with recursion base cases", "persist_long_term": true, "importance_score": 0.9}'

# Search by meaning
curl "http://localhost:8000/api/v1/memory/search?query=recursion+difficulties" \
  -H "Authorization: Bearer $TOKEN"
```

### Configuration (Phase 4)

| Setting | Default | Meaning |
|---|---|---|
| `MEMORY_VECTOR_STORE_URL` | `./storage/memory_vector_store` | FAISS index directory for memory (separate from `VECTOR_STORE_URL`) |
| `SHORT_TERM_MEMORY_TTL_DAYS` | `7` | Expiry window for short-term memory |
| `SHORT_TERM_MEMORY_MAX_ITEMS` | `50` | Per-user short-term memory size cap |
| `SESSION_MEMORY_TTL_MINUTES` | `30` | Inactivity window before session memory is reclaimed |
| `LONG_TERM_MEMORY_MAX_ITEMS` | `5000` | Soft cap before `DELETE /memory/prune` trims low-importance entries |

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp config/.env.example .env
# edit .env — at minimum set DATABASE_URL to a real Postgres instance
#             and set SECRET_KEY to a long random string
```

## Run

```bash
uvicorn main:app --reload
```

Then visit:
- `http://localhost:8000/` — root
- `http://localhost:8000/docs` — interactive OpenAPI docs
- `http://localhost:8000/api/v1/health` — health check (verifies DB connectivity)
- `http://localhost:8000/api/v1/version` — version info

### Phase 2 endpoints (all require a Bearer token except register/login)

```
POST   /api/v1/auth/register          {email, password, full_name?}
POST   /api/v1/auth/login             {email, password} -> {access_token}
POST   /api/v1/documents/upload       multipart file (pdf/txt/md/docx)
GET    /api/v1/documents              list current user's documents
GET    /api/v1/documents/{id}         one document's metadata
DELETE /api/v1/documents/{id}         delete a document + its chunks + file
GET    /api/v1/documents/{id}/chunks  list a document's chunks
```

### Phase 3 endpoints (all require a Bearer token)

```
POST /api/v1/retrieval/search              {query, top_k?, similarity_threshold?, document_id?}
POST /api/v1/retrieval/similar             {chunk_id, top_k?, similarity_threshold?}
GET  /api/v1/retrieval/document/{id}       embedding status for one document
GET  /api/v1/retrieval/chunks/{id}         vector metadata for one chunk
POST /api/v1/retrieval/reindex?document_id={id}   (re-)embed one document
POST /api/v1/retrieval/rebuild             rebuild the entire FAISS index from the database
```

A document must reach `status: "chunked"` (Phase 2) before it can be
reindexed. Uploading does **not** automatically embed a document — call
`/retrieval/reindex` explicitly afterward. See `docs/Phase3.md` for why
this is a deliberate design decision, not an oversight.

## Test

Tests run against an in-memory SQLite database — no Postgres required.

```bash
pytest tests/ -v
```

## Seed sample data (requires a real Postgres connection)

```bash
python -m scripts.seed_dev_data
```

## What's implemented vs. reserved

| Implemented (Phase 1-6) | Reserved for later phases |
|---|---|
| FastAPI app, routing, DI, middleware, config, logging, exceptions | Literature Review, Writing, Quiz, Gap Analysis, Presentation agents |
| PostgreSQL models + repositories + service layer (14 tables) | Streaming responses (the abstraction exists in `BaseLLM`; not wired end-to-end to the API yet) |
| Auth (register/login routes + JWT) | Second real LLM provider (Llama/Mistral/Qwen/Gemma remain stubs) |
| Document upload, parsing (PDF/TXT/MD/DOCX), classical NLP, chunking | Learned semantic conflict detection (current heuristic is lexical/negation-based, documented as such) |
| `BaseAgent` interface + 9 concrete agents (parsing, metadata, embedding, Supervisor, Research, Q&A, Summarization, Citation, Reasoning) | Role-based access control |
| **`BaseLLM` interface — `ClaudeProvider` now REAL** (official SDK, real HTTP calls); 4 remaining provider stubs | Multi-turn conversational reasoning (each research call is currently independent, not a chat session) |
| Local embedding generation (SentenceTransformers) + 2 FAISS indexes (documents + memory) | Prompt A/B testing (the versioning infrastructure — `PromptRegistry` — exists; no experimentation harness yet) |
| Full Memory System + full Orchestration Layer (Supervisor, `WorkflowEngine`, `AgentScheduler`, `MessageBus`, `EventLogger`) | |
| **Full LLM Reasoning Layer**: `LLMService` (retry/timeout/token accounting), `PromptBuilder`/`PromptRegistry`, `ContextAssembler` (ranking/dedup/budgeting/compression), `ResponseValidator`, `SourceGrounding`, `CitationInjector`, multi-document conflict detection | |
| Explainable, grounded, cited Q&A over a user's own documents and memory — with the LLM **never** called when there's no relevant context (primary hallucination mitigation) | |

Every "reserved" item above has a docstring at its intended location
explaining exactly how a future phase will fill it in — see
`knowledge_graph/__init__.py`, `retrieval/__init__.py`'s remaining
unwritten modules (`hybrid_search.py`, `reranker.py`), and the
`NotImplementedError` bodies in `llm/providers/llama_provider.py` (and
the three other still-stubbed providers).
