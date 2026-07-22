# Phase 1 — Backend Foundation

**Status:** Complete and verified (6/6 tests passing, app boots against both PostgreSQL and SQLite).

---

## 1. Phase Objective

Phase 1's goal was to build a production-quality backend **skeleton** that
every future phase could extend without requiring architectural change —
with zero AI logic. Concretely, it achieved:

- A running FastAPI application with structured configuration, logging,
  exception handling, and request middleware.
- A working PostgreSQL connection through SQLAlchemy, with a clean
  Repository Pattern isolating all query logic.
- Seven database models covering users, documents (metadata only),
  conversations, messages, learning profiles, memory, and agent execution
  logs — the full schema every later phase writes into.
- Interfaces (not implementations) for the two biggest unknowns future
  phases depend on: an LLM provider abstraction (`BaseLLM`) and an agent
  abstraction (`BaseAgent`), plus the Confidence and Explainability
  response frameworks those future agents will return.
- A fully wired dependency-injection chain (`api/deps.py`) and a test suite
  that runs without needing a live database.

Nothing in Phase 1 calls an LLM, parses a document, generates an embedding,
or runs an agent. It is entirely plumbing — deliberately.

---

## 2. Folder Structure

| Folder | Why it exists |
|---|---|
| `api/` | The only layer allowed to know about HTTP. Routers translate requests into service calls and service results into responses — no business logic lives here. Keeping this thin means the transport layer (REST today) could be replaced without touching anything else. |
| `core/` | Cross-cutting concerns every other layer depends on: typed configuration (`config.py`), centralized logging (`logging.py`), a domain exception hierarchy (`exceptions.py`), auth primitives (`security.py`), and the shared agent-communication contract (`agent_bus.py`). |
| `database/` | Connection and session lifecycle management (`session.py`) and the shared SQLAlchemy declarative base (`base.py`). The only place `create_engine` is called. |
| `repositories/` | The **only** code allowed to write SQLAlchemy queries. Each model gets one repository; a generic `BaseRepository` supplies common CRUD so every repository isn't reinventing get/list/create/delete. |
| `services/` | Business orchestration that spans more than one repository (e.g., registering a user also provisions their Learning Profile). Routers call services; services call repositories — never the reverse. |
| `schemas/` | The API's actual contract with clients — Pydantic models, deliberately separate from ORM models, so a database column can change without silently changing what a client receives. Also home to the Confidence and Explainability frameworks used by future agents. |
| `models/` | The ORM / database schema itself — what's stored, not what's transmitted. |
| `middleware/` | Cross-request concerns that shouldn't be duplicated in every route: a global exception handler translating every exception type into one consistent JSON shape, and request logging. |
| `memory/` | Abstract interfaces for the four memory categories (short-term, long-term, conversation-scoped, document-scoped) the system will eventually use for personalization — policy, not storage (storage is the `Memory` table + `MemoryRepository`). |
| `llm/` | The model abstraction layer — `BaseLLM` plus five provider stub classes (Claude, Llama, Mistral, Qwen, Gemma), all raising `NotImplementedError`. No agent or service is allowed to import a model SDK directly; everything goes through this interface. |
| `agents/` | The agent abstraction — `BaseAgent`'s Template Method skeleton (`run()`: validate → execute → validate → log) that every future concrete agent will inherit, plus the activity-timeline helper that will back the frontend's agent execution visualization. |
| `utils/` | Small, stateless, dependency-free helpers with no awareness of the database, agents, or HTTP. |

---

## 3. Design Patterns Used

### Repository Pattern
All database access is centralized behind repository classes. **Why:**
without this, SQL/query logic ends up scattered across routers and
services, making it impossible to swap PostgreSQL for another engine, or a
table for a differently-shaped one, without a system-wide search-and-replace.
With it, that kind of change is contained to one file per affected table.

### Service Layer
Business rules that touch more than one repository (or that don't belong
purely to data access) live in a service. **Why:** without this layer,
either the router grows business logic (breaking the "transport-only"
rule) or repositories start calling each other (breaking the "repositories
only talk to the database" rule). The service layer is where "register a
user AND provision their learning profile" correctly lives.

### Dependency Injection
FastAPI's `Depends()` system is used throughout — `get_db` yields a
session, `get_user_service` builds a service from that session,
`get_current_user` resolves an authenticated user from a request. **Why:**
this is what makes the test suite possible without a real database — see
`tests/conftest.py`, which swaps `get_db`'s implementation with an
in-memory SQLite session via `app.dependency_overrides`, with zero changes
to application code.

### Configuration Management
One `Settings` class (`pydantic-settings`), reading from environment
variables / `.env`, validated at startup. **Why:** "fail fast" — a missing
or malformed config value surfaces immediately at process start, not three
requests into production traffic. It also means nothing in the codebase
reads `os.environ` directly, so every dependency the app has on external
config is discoverable in one file.

### Middleware
Request logging and global exception handling are implemented as
middleware/exception handlers registered once in `main.py`, not
per-route. **Why:** every route gets consistent error shape and request
logging for free — a new route added in Phase 2+ doesn't need to
remember to add either.

### Abstraction / Interfaces
`BaseLLM` and `BaseAgent` are abstract classes with zero concrete logic in
Phase 1. **Why:** this is Dependency Inversion applied deliberately early —
the Supervisor Agent (Phase 3) and every individual agent can be designed
and even partially tested against these interfaces before a single model
provider is wired in, and swapping providers later is a subclass, not a
rewrite.

---

## 4. Database Architecture

| Table | Purpose | Future Usage |
|---|---|---|
| `users` | Identity and ownership root for every other table. | Auth routes (Phase 2), per-user scoping of every future retrieval/memory/agent call. |
| `documents` | Uploaded file metadata only — no content processing in Phase 1. | Phase 2 attaches parsing, chunking, and NLP metadata directly to this table's lifecycle (`DocumentStatus`). |
| `conversations` | Groups messages into a resumable, nameable session. | Phase 2's Conversation Agent will read/write these; `document_ids` scopes which documents ground a conversation's answers. |
| `messages` | One row per chat turn (append-only). | `agent_name` (currently always null) will be populated once real agents exist, powering the frontend's per-message attribution. |
| `learning_profiles` | Materialized, per-user summary of learning state (weak/strong topics, quiz accuracy, streaks). | Gap Analysis and Recommendation Agents (later phases) read and write this table directly. |
| `memory` | Synthesized, durable insight about a learner — not a transcript — discriminated by `memory_type` (short-term / long-term / conversation / document). | Backs personalization once the Memory Agent exists. |
| `agent_execution_logs` | Structured telemetry: one row per agent invocation, including confidence, latency, and status. | Populated for real starting with Phase 2's first concrete agent (PDF Parsing Agent); powers the future Agent Activity Timeline UI. |

---

## 5. APIs

| Endpoint | Purpose |
|---|---|
| `GET /` | Root — confirms the API is up and points to `/docs` and the health endpoint. |
| `GET /api/v1/health` | Operational health check; actually pings the database via `check_database_connection()`, not just a hardcoded "ok". Returns `"healthy"` or `"degraded"`. |
| `GET /api/v1/version` | Returns app name, version, and environment — useful for confirming which build/environment a client is talking to. |

All three return the same `APIResponse` envelope (`success`, `data`,
`error`) that every future endpoint will also use.

---

## 6. Request Lifecycle

```
Browser
   │  HTTP request
   ▼
Router (api/routes/*.py)         — HTTP-only, no business logic
   │  calls a service via Depends()
   ▼
Service (services/*.py)          — orchestration, business rules
   │  calls one or more repositories
   ▼
Repository (repositories/*.py)   — the only layer with query logic
   │  uses a Session from database/session.py
   ▼
Database (PostgreSQL)
   │
   ▼
Response (schemas/*.py -> APIResponse envelope)
   │
   ▼
Browser
```

Every layer only ever calls the layer directly below it — a router never
touches a repository, and a repository never contains business rules.

---

## 7. What I Learned

**Software Engineering concepts:** the Repository Pattern and Service
Layer as a genuine separation of concerns (not just folder naming);
Dependency Injection as the mechanism that makes a system testable without
mocking frameworks; centralized configuration and exception handling as
"fail fast, fail consistently" disciplines; the Template Method pattern
(`BaseAgent.run()`) as a way to guarantee cross-cutting behavior (timing,
logging, error containment) without every subclass re-implementing it.

**Backend concepts:** connection pooling and session lifecycle management;
structured logging with named channels; JWT-based auth primitives
(hashing, signing, decoding) kept separate from the HTTP flow that will use
them; building a test suite that swaps real infrastructure for in-memory
substitutes via dependency overrides, rather than hitting a real database.

**How Phase 1 prepares for NLP:** none of Phase 1 touches text processing,
but it built the exact seams NLP work will plug into — `Document.status`
as a state machine for the ingestion pipeline, `AgentExecutionLog`'s
confidence/latency columns as the evaluation substrate for judging AI
output quality, and `BaseAgent`/`BaseLLM` as the interfaces the first real
NLP component (Phase 2's PDF Parsing Agent) will implement.

---

## 8. Challenges

| Issue | Cause | Resolution |
|---|---|---|
| `sqlalchemy.exc.CompileError` on `conversations.document_ids` and similar columns | Postgres-only `ARRAY`/`JSONB` column types don't compile against the SQLite engine used in tests. | Switched those columns to the dialect-portable `JSON` type. Production behavior on PostgreSQL is unaffected. |
| `ValueError: password cannot be longer than 72 bytes` on every call to `hash_password`, even for short passwords | `passlib`'s bcrypt backend has a known incompatibility with `bcrypt>=4.1`'s internal version-detection self-test. | Pinned `bcrypt<4.1` in `requirements.txt`. |
| Relationship resolution errors when running `configure_mappers()` in isolation | SQLAlchemy resolves string-based relationship references (`Mapped["Document"]`) lazily — every model must be imported somewhere before the mapper graph is built. | Centralized every model import in `models/__init__.py`, imported once from `main.py` and from `tests/conftest.py`. |
| Environment variable / configuration drift risk | Without a single settings object, config values could be read inconsistently across modules (typos, different defaults). | `core/config.py`'s single cached `Settings` instance, validated by Pydantic at import time — every consumer imports the same `settings` object. |

---

## 9. Future Dependencies

- **Phase 2 (Document Intelligence Pipeline)** depends on Phase 1 for: the
  `Document` model and its `DocumentStatus` lifecycle, the `BaseAgent`
  interface (the PDF Parsing Agent is the first concrete subclass),
  `AgentExecutionLog` (the first agent to actually write rows there), the
  repository/service pattern (new `DocumentChunkRepository` and
  `DocumentService` follow the exact same shape as Phase 1's), and the
  global exception handler (new document-processing exceptions plug into
  the existing `AppException` hierarchy with zero handler changes).
- **Phase 3 (Retrieval & Embeddings)** depends on Phase 1's `BaseLLM`
  interface (the `embed()` method is called for real for the first time)
  and on Phase 2's chunk storage as its input.
- **Phase 4 (Knowledge Graph)** depends on Phase 1's `LearningProfile`
  schema (currently plain string arrays for `weak_topics`/`strong_topics`,
  designed to migrate to foreign keys against the future graph node table)
  and the `agents/` interface for its own Knowledge Graph Agent.

---

## 10. Summary

Phase 1 delivered a fully working, fully tested backend with no AI
capability whatsoever — by design. Every architectural seam a future
phase needs (agent interface, model abstraction, confidence/explainability
schemas, memory categories, execution logging) exists and compiles, but
contains no logic. The payoff of that discipline shows up starting in
Phase 2: the first real agent (PDF Parsing) is built by implementing an
interface that already exists, logging to a table that already exists,
and returning a response shape that already exists — rather than
inventing all of that under time pressure alongside the first real feature.
