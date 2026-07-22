# Phase 4 — Memory System

**Status:** Written before implementation, per the mandatory Phase 4 process.

---

## 1. Why AI Needs Memory

Every phase before this one treated each request as if it started from
nothing: Phase 3's `SemanticSearchService.search()` takes a query and
returns chunks, with zero awareness that the same user asked a related
question five minutes ago, or that they've searched this exact phrase
before, or that a past conversation already covered the prerequisite
concept. That's fine for a single stateless lookup — it breaks down the
moment the goal becomes "help someone learn over time," which is this
entire project's stated purpose (see the Phase 0 architecture doc's
Project Vision).

Memory is what turns a sequence of independent request/response pairs into
something that accumulates: a system that knows what's already been
uploaded, what's already been asked, what was retrieved last time, and
what the user seems to care about — without any of that requiring a
reasoning model to re-derive it from scratch on every call. That last
point is what makes memory the right thing to build *before* a Supervisor
or reasoning agent, not after: an agent that reasons over accumulated
context is far more useful, and far cheaper to run, than one that
re-establishes context from raw history on every turn.

## 2. Human Memory vs. AI Memory

Human memory research distinguishes several systems by *duration* and
*content type* — this phase borrows that taxonomy deliberately, because
each human category maps to a real, distinct engineering need:

| Human memory concept | What it captures | This system's analog |
|---|---|---|
| Working memory | What you're actively holding in mind *right now*, gone once you stop thinking about it | Working Memory (Section 4.1) |
| Short-term memory | The last few things that happened, still fresh | Short-Term Memory (Section 4.2) |
| Long-term memory | Durable, consolidated knowledge and experience | Long-Term Memory (Section 4.3) |
| Episodic memory | Memory of specific events ("I asked about trees on Tuesday") | A `Memory` row with `memory_type=CONVERSATION`, timestamped |
| Semantic memory | Memory of facts/concepts, detached from when you learned them | Embedded, semantically-searchable long-term memory content |

The distinction that matters most for engineering purposes isn't
biological accuracy — it's that these categories have genuinely different
**lifecycle, storage, and access patterns**, which is exactly what drives
Section 4's implementation split.

## 3. Working Memory / Short-Term / Long-Term / Session Memory

### 3.1 Working Memory

Scope: **one request**. Lives only as long as that request is being
handled, holds whatever a service needs to pass to itself mid-computation,
and disappears the instant the request finishes — never written to a
database, never shared between requests, never even shared between two
different users' concurrent requests.

This isn't a new concept for this project — `core/agent_bus.py::TaskContext`
(Phase 1) already *is* a working-memory object in every meaningful sense:
constructed at the start of one pipeline run, passed through each agent,
discarded after. Phase 4's `WorkingMemoryService` generalizes that same
pattern into a small, explicit service any part of the system can use, not
just the agent pipeline.

### 3.2 Short-Term Memory

Scope: **recent, bounded, per-user**. Recent conversation turns, recent
searches, recent uploads, recent retrievals — all things that matter for a
little while and then stop being useful. This is genuinely persisted (in
PostgreSQL — losing it on a server restart would be a real regression),
but bounded and self-expiring, which is precisely what Phase 1's `Memory`
table already anticipated: `MemoryType.SHORT_TERM` plus a nullable
`expires_at` column, both defined in Phase 1 and unused until now.

### 3.3 Long-Term Memory

Scope: **durable, semantically searchable, per-user**. Content worth
remembering indefinitely: synthesized insight ("this user has asked about
recursion three separate times"), a running record of documents and
conversations, and — the new capability this phase adds — the ability to
search that history *by meaning*, not just by browsing a list, using the
exact same embedding/FAISS machinery Phase 3 built for document retrieval.

### 3.4 Session Memory

Scope: **one login session, across multiple requests, until it ends**.
This sits between working memory (too short — gone after one request) and
short-term memory (too persistent and too database-heavy for what's
fundamentally ephemeral state, like "what page of results was the user
last looking at"). Since this project has no server-side session/cookie
system yet (Phase 2's auth is stateless JWT), Section 12 documents exactly
how session memory is implemented without one.

## 4. Memory Retrieval, Indexing, Lifecycle, Expiration, Pruning

- **Retrieval** happens two ways: *structured* (list recent memories of a
  given type, filtered by user/conversation/document — plain SQL) and
  *semantic* (find memories whose meaning matches a query — embedding +
  FAISS, reusing Phase 3's `EmbeddingService` unmodified).
- **Indexing** for semantic search means embedding a memory's `content`
  and storing the resulting vector in a FAISS index — a new, *separate*
  index from Phase 3's document-chunk index (Section 12.2 explains why
  they aren't merged).
- **Lifecycle**: `UPLOADED`-style status tracking isn't needed here (a
  memory doesn't get "processed" the way a document does) — instead, a
  memory's lifecycle is: created -> (optionally accessed, tracked via
  `MemoryAccessLog`) -> expires or gets pruned -> deleted.
- **Expiration**: short-term memories get a real `expires_at` timestamp at
  creation (e.g., "expires in 7 days"); long-term memories don't expire on
  a timer at all — they're removed only by explicit pruning.
- **Pruning**: an operator- or schedule-triggered cleanup pass
  (`MemoryCleanupService`) that removes expired short-term memories and
  (optionally) low-importance long-term memories past a size cap —
  distinct from expiration because pruning is an *action*, not a passive
  timestamp check.

## 5. Conversation History / Document History / Memory Search

- **Conversation history** is not re-invented here — Phase 1's
  `Conversation`/`Message` tables already are conversation history. This
  phase's contribution is treating significant conversation events as
  *memory* (a `Memory` row referencing a `conversation_id`), which is a
  distinct, smaller, curated signal layered on top of the full raw
  transcript, not a replacement for it.
- **Document history** similarly reuses Phase 2/3's `Document` table as
  the source of truth for "what was uploaded when" — this phase adds
  `Memory` rows of `memory_type=DOCUMENT` for things worth remembering
  *about* a document's usage (e.g., "revisited three times this week"),
  not a duplicate document log.
- **Memory search** is the new capability: `GET /memory/search`, backed by
  `MemorySearchService`, embedding the query and searching the dedicated
  memory FAISS index — architecturally identical to Phase 3's document
  search, deliberately, since duplicating that design would be its own
  bug source.

## 6. Design Decisions

1. **Reuse Phase 1's `Memory` table as-is** rather than introducing a
   parallel "MemoryRecord" table — it already has the exact shape needed
   (`memory_type` discriminator, `importance_score`, `expires_at`,
   optional `conversation_id`/`document_id` scoping). Only two genuinely
   new tables are added: `MemoryEmbedding` (semantic-search mapping,
   mirroring Phase 3's `Embedding` table exactly) and `MemoryAccessLog`
   (access tracking for statistics/pruning, mirroring `AgentExecutionLog`'s
   shape). See docs/Phase4.md Section 9 for the full schema.
2. **A second, separate FAISS index for memory**, not a shared index with
   documents. Searching "my past conversations" and "my uploaded documents"
   are different retrieval intents; merging them into one index would mean
   every document search accidentally competes against conversation
   history for the same top-K slots, and vice versa. `FAISSVectorStore`
   (Phase 3) is fully reused unmodified — a second *instance*, pointed at
   a different storage directory, is all this requires.
3. **Working memory is not a singleton; session memory is.** Working
   memory's entire correctness property is "gone after one request," which
   falls out for free from being constructed fresh per-request via FastAPI
   `Depends()` (like `DocumentService`) rather than cached. Session memory
   needs to survive *across* requests within a session, so it follows
   `EmbeddingService`/`FAISSVectorStore`'s singleton pattern instead.
4. **No cookie/server-side session infrastructure is introduced.** This
   project's auth (Phase 2) is stateless JWT. Rather than bolting on a
   parallel session system, `SessionMemoryService` treats a client-supplied
   `session_id` string as the session key, with TTL-based expiry as the
   safety net for sessions that are never explicitly ended. This is a
   deliberate, minimal choice — see Section 12 for the full tradeoff.

## 7. Extensibility

- `MemoryManager` is the single facade the future Supervisor Agent will
  depend on — by the time a Supervisor exists, it calls one object
  (`MemoryManager.get_relevant_context(user_id, query)`) instead of
  knowing about four separate memory services individually.
- `MemorySearchService`'s separation from `SemanticSearchService` means a
  future "search everything" endpoint can compose both without either
  needing to change.
- `MemoryAccessLog` is designed to support a future recommendation signal
  ("topics you keep revisiting") without this phase needing to build that
  logic itself — the raw access data is what a Gap Analysis Agent (a later
  phase) would consume.

## 8. Data Flow Diagrams

### 8.1 Write Path (a memory-worthy event happens)

```
Event occurs (e.g., a search is run, a document is uploaded)
        │
        ▼
Calling service constructs a MemoryRecord-worthy payload
        │
        ▼
MemoryManager.remember(...)
        │
        ├─▶ ShortTermMemoryService.write()  — Memory row, memory_type + expires_at set
        │
        └─▶ (if flagged as long-term-worthy) LongTermMemoryService.write()
                    │
                    ▼
            MemorySearchService.index() — embeds content, adds to memory FAISS index,
                                           creates a MemoryEmbedding row
```

### 8.2 Read Path (structured recall)

```
GET /memory/recent  or  GET /memory/history
        │
        ▼
ShortTermMemoryService / repository queries — plain SQL, filtered by user + type + not-expired
        │
        ▼
MemoryOut list returned
```

### 8.3 Read Path (semantic recall)

```
GET /memory/search?query=...
        │
        ▼
MemorySearchService
        │  EmbeddingService.embed_query()  (Phase 3, reused unmodified)
        ▼
Memory FAISS index .search()  (Phase 3's FAISSVectorStore, second instance)
        │
        ▼
MemoryEmbedding -> Memory row resolution (mirrors Phase 3's RetrievalRepository pattern)
        │
        ▼
Ranked, explainable MemorySearchResult list (reuses retrieval/ranking.py's shape)
```

## 9. Backend Architecture / Folder Modifications

No folder renamed. Additions only:

```
memory/
├── interfaces.py        EXISTING (Phase 1) — now genuinely implemented, not just declared
├── working_memory.py     NEW — in-process, per-request store (no persistence, no singleton)
└── session_memory.py     NEW — in-process, singleton, TTL-based session store

models/
├── memory_embedding.py    NEW — mirrors models/embedding.py exactly, but for Memory rows
└── memory_access_log.py   NEW — mirrors models/agent_execution_log.py's shape

repositories/
├── memory_embedding_repository.py    NEW
└── memory_access_log_repository.py   NEW
(repositories/memory_repository.py — EXISTING, Phase 1, extended with a few new query methods)

services/
├── memory_manager.py               NEW — the facade (Section 7)
├── working_memory_service.py       NEW
├── short_term_memory_service.py    NEW
├── long_term_memory_service.py     NEW
├── session_memory_service.py       NEW
├── memory_search_service.py        NEW
├── memory_cleanup_service.py       NEW
└── memory_statistics_service.py    NEW

schemas/
└── memory_api.py    NEW — request/response contracts for the memory API
    (schemas/memory.py — EXISTING, Phase 1, left untouched; memory_api.py is additive)

api/routes/
└── memory.py    NEW — REST endpoints (Section 10)
```

`api/deps.py` gains dependency-injection wiring for the new services,
following the exact `get_x_service` pattern established in Phase 1-3 — no
new pattern introduced.

## 10. New API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /memory/store` | Explicitly store a memory (short-term or long-term) |
| `GET /memory/session` | Read the current session's in-memory state |
| `GET /memory/history` | Structured recall: recent memories by type/scope |
| `GET /memory/search` | Semantic recall: memory search by meaning |
| `GET /memory/recent` | Convenience: most recent memories across all types |
| `GET /memory/statistics` | Aggregate counts, storage size, access patterns |
| `DELETE /memory/session` | End the current session, discarding its session memory |
| `DELETE /memory/history` | Delete memories matching a filter (type/scope) |
| `DELETE /memory/prune` | Trigger cleanup: expired short-term + over-cap long-term |
| `POST /memory/clear` | Danger-zone: clear all of the current user's memory |

## 11. Common Bugs (anticipated, informed by Phase 1-3's actual history)

Based on this project's track record so far (a real SQLite/threading bug
in Phase 2, a real UUID/str bug in Phase 2, a real UUID-conversion auth bug
in Phase 2), the categories most likely to bite this phase specifically:

- **Singleton state leaking across tests** — `SessionMemoryService`
  follows `EmbeddingService`'s singleton pattern, which means it needs the
  exact same `reset_instance()` test hook and autouse fixture treatment
  Phase 3 already built for `EmbeddingService`/`FAISSVectorStore`, or
  session state will leak between test cases.
- **A second FAISS index directory colliding with the first** — since
  Phase 3's vector store and this phase's memory vector store are both
  `FAISSVectorStore` instances, using the same `storage_dir` by accident
  would silently corrupt both indexes' persistence files.
- **UUID/str mismatches in new schemas** — Phase 2's exact bug
  (`DocumentOut.owner_id` typed `str` while the ORM returns `UUID`) is a
  known trap for every new schema this project adds; every new ID field in
  `schemas/memory_api.py` is typed `UUID` from the start, not `str`.

## 12. Design Decision: Session Memory Without Cookies

Since Phase 2 never built server-side sessions (JWTs are stateless by
design), `SessionMemoryService` accepts a `session_id` the client
generates (a UUID string) and passes on every session-scoped request —
similar to how many single-page apps manage a client-side session token
today. The server never issues or validates this ID against a login event;
it's purely a key for grouping ephemeral state. A TTL (default 30 minutes
of inactivity) is the safety net that reclaims memory for sessions that
are never explicitly ended via `DELETE /memory/session`. This is flagged
here as a genuine simplification appropriate to this phase's scope (no
Supervisor, no reasoning) — a real production session system tied to login
state is a reasonable future improvement, not a Phase 4 requirement.

## 13. Testing Strategy

Same layered approach Phase 2/3 established:

- **Pure unit tests** (no database): `memory/working_memory.py`,
  `memory/session_memory.py` — plain Python, testable via `tmp_path`/mocks only where filesystem/singleton state is involved.
- **Repository tests** (SQLite, no HTTP): new repositories, plus extended
  query methods on the existing `MemoryRepository`.
- **Service tests**: `MemoryCleanupService`'s expiration/pruning logic,
  `MemoryStatisticsService`'s aggregation, `MemorySearchService`'s ranking
  — all testable against `FakeEmbeddingBackend` exactly as Phase 3's
  `SemanticSearchService` tests are.
- **Full-stack integration tests**: every new endpoint, through real HTTP
  requests, including the write-then-search-then-prune lifecycle end to
  end.
- **Regression tests**: the full Phase 1-3 suite must stay green — this is
  a hard gate before Phase 4 can be considered complete, not a nice-to-have.
