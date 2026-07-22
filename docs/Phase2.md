# Phase 2 — Document Intelligence Pipeline

**Status:** Complete and verified (58/58 tests passing, full pipeline confirmed against both in-memory SQLite and a real SQLite file database).

---

## 1. Architecture

Phase 2 extends Phase 1's architecture additively — no folder was renamed,
no Phase 1 file's public interface was broken. New capability was added
along the exact seams Phase 1 left for it:

```
document_processing/          <- NEW: parsers, text cleaning, NLP preprocessing, pipeline orchestration
├── parsers/
│   ├── base_parser.py         (Adapter interface: ParsedDocument, ParsedPage)
│   ├── pdf_parser.py          (pypdf)
│   ├── txt_parser.py
│   ├── markdown_parser.py
│   ├── docx_parser.py         (python-docx)
│   └── factory.py             (format -> parser dispatch)
├── text_cleaner.py             (whitespace, Unicode, header/footer, page-number cleanup)
├── nlp_preprocessor.py         (sentence/paragraph segmentation, counts, language detection)
└── pipeline.py                 (orchestrates: parse -> metadata -> clean -> chunk, DB-free)

retrieval/
└── chunker.py                  <- NEW: four chunking strategies (fixed/paragraph/sentence/sliding-window)

agents/
├── pdf_parsing_agent.py        <- NEW: first concrete BaseAgent subclass
└── metadata_extraction_agent.py <- NEW: second concrete BaseAgent subclass

models/
├── document.py                  <- EXTENDED: file_format, author, page_count, language,
│                                    word_count, char_count, reading_time_minutes,
│                                    CHUNKED status (all additive columns)
└── document_chunk.py            <- NEW: DocumentChunk table

services/
└── document_service.py          <- NEW: validation, storage, pipeline orchestration, persistence

api/routes/
├── auth.py                      <- NEW: minimal register/login (see Section 5's note)
└── documents.py                 <- NEW: upload/list/get/delete/chunks
```

**Why `document_processing/` is a new top-level package rather than being
squeezed into an existing folder:** Phase 1's folder list didn't anticipate
a dedicated NLP/document-processing layer because Phase 1 explicitly had no
text-processing capability. Adding it as its own package — rather than
overloading `utils/` (stateless helpers only, by Phase 1's own rule) or
`retrieval/` (reserved for retrieval-specific logic) — keeps the
single-responsibility boundaries Phase 1 established intact. `chunker.py`
specifically DOES live in `retrieval/`, because Phase 0's original
architecture doc explicitly pre-assigned chunking to that folder.

**Why the PDF Parsing Agent and Metadata Extraction Agent are thin:** both
subclass `BaseAgent` and implement only `validate_input` / `execute` /
`validate_output` — timing, logging, and error containment are inherited
from Phase 1's `run()` for free. This is the payoff of Phase 1's Template
Method design showing up on the very first concrete agent.

---

## 2. Data Flow

### 2.1 Upload → Full Pipeline

```
POST /documents/upload (multipart file)
        │
        ▼
DocumentService.validate_upload()        — extension + size + non-empty checks
        │
        ▼
DocumentService.store_file()             — UUID-named file written to UPLOAD_DIR
        │
        ▼
Document row created (status=UPLOADED)
        │
        ▼
document_processing.pipeline.process_document()
        │
        ├──▶ PDFParsingAgent.run()        — status=PARSING; extract text (+pages if PDF)
        │
        ├──▶ MetadataExtractionAgent.run() — title/author/language/word_count/etc.
        │
        ├──▶ text_cleaner.clean_text()     — whitespace, Unicode, header/footer, page-number cleanup
        │
        └──▶ retrieval.chunker.chunk_text() — one of 4 strategies produces Chunk objects
        │
        ▼
DocumentService persists:
  - AgentExecutionLog rows (one per agent step)     — status=PARSED
  - Document.title/author/language/word_count/...
  - DocumentChunk rows (bulk insert)                — status=CHUNKED
        │
        ▼
DocumentOut returned to client
```

Any `AppException` raised at any stage (corrupted file, empty document,
encrypted PDF, unsupported type) short-circuits this chain; the `Document`
row is marked `FAILED` with `processing_error` set to a human-readable
message, and the same exception (with its original HTTP status/error code
preserved — see Section 6) propagates to the client.

### 2.2 Retrieval-Ready State

After a successful run, `GET /documents/{id}/chunks` returns every
`DocumentChunk` for that document, ordered by `chunk_index` — this is
exactly the shape Phase 3's Embedding Agent will iterate over.

---

## 3. NLP Concepts Learned

| Concept | Where implemented | What it teaches |
|---|---|---|
| **Unicode normalization (NFKC)** | `text_cleaner.normalize_unicode` | Real-world text has multiple byte-level representations of the same visual character; canonicalizing early prevents downstream tokenization from treating them as different. |
| **Whitespace normalization** | `text_cleaner.normalize_whitespace` | PDF extraction in particular produces irregular spacing from column layouts; a naive `.split()` isn't enough for clean paragraph reconstruction. |
| **Heuristic header/footer removal** | `text_cleaner.remove_repeated_lines` | Cross-page repetition frequency is a simple but effective statistical signal for boilerplate detection — no ML model needed. |
| **Sentence boundary disambiguation** | `nlp_preprocessor.segment_sentences` (via `pysbd`) | Periods are ambiguous (abbreviations, decimals, initials); rule-based segmentation is a real, still-used middle ground between naive regex and a learned model. |
| **Paragraph segmentation** | `nlp_preprocessor.segment_paragraphs` | A structural (not linguistic) segmentation task — contrasting it with sentence segmentation clarifies which NLP problems are "hard" (ambiguity-driven) vs. "easy" (structure-driven). |
| **Tokenization (word-level)** | `nlp_preprocessor.count_words` | Deliberately NOT a subword/BPE tokenizer — see Section 3.1 below for why that distinction is the whole point. |
| **Statistical language detection** | `nlp_preprocessor.detect_language` (via `langdetect`) | A classical Bayesian classifier over character n-gram frequency profiles — genuinely different from, and predates, neural language ID models. |
| **Chunking as a text-structuring decision** | `retrieval/chunker.py`, four strategies | The core RAG-ingestion tradeoff (topical focus vs. complete-idea preservation) exists and matters *before* any embedding model is chosen. |

### 3.1 Why `token_count` Is a Deliberate Approximation

`nlp_preprocessor.count_words` counts whitespace/punctuation-delimited
words, not the subword units a real LLM tokenizer (BPE, SentencePiece)
would produce. This is not a shortcut taken by mistake — it's the literal
boundary the Phase 2 spec draws ("NO Embeddings"): a real tokenizer is
*tied to a specific embedding/LLM model's vocabulary*, which Phase 3
hasn't chosen yet. Building a real tokenizer dependency into Phase 2 would
mean re-doing this work once Phase 3 picks a model. `DocumentChunk.token_count`
will be recomputed with a real tokenizer at that point.

---

## 4. Software Engineering Concepts Learned

- **Adapter pattern** (`document_processing/parsers/`) — four unrelated
  libraries (`pypdf`, `python-docx`, plain file I/O, Markdown) unified
  behind one `BaseParser.parse() -> ParsedDocument` contract.
- **Simple Factory pattern** (`parsers/factory.py`) — format-to-parser
  dispatch centralized in one place instead of `if/elif` chains scattered
  across callers.
- **Template Method in practice, not just in theory** — Phase 1's
  `BaseAgent.run()` was written with zero concrete subclasses to validate
  it against. Phase 2's two agents are the first proof it actually
  provides free timing/logging/error-containment without modification.
- **Pure-function pipeline / impure orchestrator split**
  (`document_processing/pipeline.py` vs. `services/document_service.py`)
  — the pipeline never touches a database session, which makes it testable
  with nothing but a temp file (see `tests/test_metadata_extraction.py`,
  which never imports a repository).
- **Preserving typed error information across an abstraction boundary** —
  `BaseAgent.run()` swallows exceptions into `AgentResult` by design (a
  Phase 1 decision), which meant the *type* of a failure was initially lost
  by the time `DocumentService` needed to react to it. Fixed by carrying
  `error_code`/`error_status_code` through `AgentResult` itself (see
  Section 6) rather than re-deriving them from a string.
- **Security-conscious file handling** — uploaded filenames are never
  trusted for disk paths (UUID-generated names prevent path traversal and
  collisions); file size is validated before any content is read into
  memory in full.

---

## 5. Future Dependencies

- **Phase 3 (Retrieval & Embeddings)** consumes `DocumentChunk` rows
  directly — the Embedding Agent iterates `chunk_text` per chunk and calls
  `BaseLLM.embed()` (Phase 1's interface, still unimplemented). It also
  replaces the word-count `token_count` approximation with the real
  tokenizer belonging to whichever embedding model is chosen.
- **Phase 4 (Knowledge Graph)** will run concept extraction over
  `Document.status == CHUNKED` documents' chunks — the same `AgentExecutionLog`
  and `BaseAgent` infrastructure Phase 2 exercised for the first time will
  log the Knowledge Graph Agent's runs identically.
- **A note on scope:** Phase 2 required a genuinely authenticated
  `owner_id` to attach to uploaded documents, which Phase 1 built the
  primitives for (`core/security.py`, `UserService`) but never exposed over
  HTTP. `api/routes/auth.py` (`POST /auth/register`, `POST /auth/login`) is
  a small, flagged extension of Phase 1's scope to unblock this — not a
  redesign. Every underlying primitive it calls was already built and
  tested in Phase 1.

---

## 6. Common Errors (and how they were solved)

| Error | Cause | Fix |
|---|---|---|
| `sqlite3.OperationalError: no such table: users` appearing intermittently only in HTTP-level tests | FastAPI runs synchronous route handlers in a worker thread pool; SQLAlchemy's default pooling for `sqlite:///:memory:` creates a **separate, empty in-memory database per thread** unless told otherwise. Register and login landing on different worker threads meant login queried a database that never had `create_all` run against it. | Added `poolclass=StaticPool` to the test engine (`tests/conftest.py`) so every thread shares one physical connection/database — the standard fix for FastAPI + SQLite in-memory testing. |
| `AttributeError: 'str' object has no attribute 'hex'` when calling `get_current_user` | `create_access_token(subject=str(user.id))` stores the JWT subject as a string; `get_current_user` passed that string directly to `UserRepository.get()`, but the `id` column is `UUID(as_uuid=True)`, whose bind processor expects an actual `uuid.UUID` instance. **This was a real bug, not a test artifact** — it would have failed identically against production PostgreSQL. | `api/deps.py::get_current_user` now explicitly converts the JWT subject back to `uuid.UUID` before querying, raising `UnauthorizedError` if it isn't a valid UUID. |
| `pydantic_core.ValidationError: owner_id — Input should be a valid string` when returning `DocumentOut` | `DocumentOut.owner_id` (and `DocumentChunkOut.document_id`) were typed `str`, but SQLAlchemy returns actual `uuid.UUID` Python objects for `UUID(as_uuid=True)` columns, and Pydantic v2 doesn't silently coerce `UUID -> str`. **This exact bug exists latent in several Phase 1 schemas** (`ConversationOut.owner_id`, `MessageOut.conversation_id`, etc.) that were never exercised by a real route — flagged here rather than fixed there, per the "do not modify previously completed architecture" instruction; it will need the same one-line type fix when those routes are built. | Changed `owner_id`/`document_id` field types to `UUID` in `schemas/document.py` and `schemas/document_chunk.py` — matches `TimestampedSchema.id`'s existing (already-correct) pattern. |
| Losing HTTP status/error code across the agent boundary — a corrupted PDF was reported as a generic `500` instead of `422 corrupted_document` | `BaseAgent.run()` deliberately swallows exceptions into `AgentResult.error_message` (a plain string) so agent failures never crash the Supervisor. The pipeline needed the *original exception type* back to let `DocumentService`/the global handler report the correct status. | Added `error_code`/`error_status_code` fields to `AgentResult`, populated by `BaseAgent.run()` from any caught `AppException`'s attributes. `pipeline.py::_reraise_original_failure` reconstructs a typed exception carrying that preserved status/code. |
| `passlib`/`bcrypt` incompatibility (carried over from Phase 1) | `bcrypt>=4.1`'s internal self-test breaks `passlib`. | Already pinned `bcrypt<4.1` in Phase 1; no new occurrence in Phase 2. |

---

## 7. Testing Strategy

58 tests across 8 files, organized by what they exercise without needing
a database, versus what requires the full HTTP + database stack:

**Pure unit tests (no database, no HTTP):**
- `tests/test_text_cleaning.py` (8 tests) — each cleaning function in isolation.
- `tests/test_nlp_preprocessing.py` (9 tests) — segmentation, counting, language detection.
- `tests/test_chunking.py` (9 tests) — all four strategies, boundary conditions, error cases.
- `tests/test_document_parsers.py` (11 tests) — real PDF (via `reportlab`), real DOCX (via
  `python-docx`), TXT, Markdown, plus every Phase 2 error case (corrupted, encrypted, empty).

**Agent-level tests (TaskContext, no database):**
- `tests/test_metadata_extraction.py` (4 tests) — chains `PDFParsingAgent` -> `MetadataExtractionAgent`
  through a shared `TaskContext`, exactly as the pipeline does, proving Phase 1's `BaseAgent` design
  works for real subclasses.

**Full-stack integration tests (SQLite + real HTTP requests):**
- `tests/test_documents.py` (12 tests) — upload for all 4 formats, chunk retrieval, ownership
  isolation between users, every error status code, auth enforcement, deletion cascade.

**Why this split matters:** the pure unit tests run in milliseconds and
pinpoint exactly which layer broke; the integration tests catch the kind
of cross-layer bug (the `StaticPool` threading issue, the UUID/str
mismatches) that unit tests structurally cannot see, because those bugs
only exist at the seams between layers.

---

## 8. Phase Summary

Phase 2 turned Phase 1's empty scaffolding into a working document
ingestion pipeline: four file formats, two concrete agents (the first ever
built against Phase 1's `BaseAgent` interface), a five-stage cleaning
pipeline, four chunking strategies, and full CRUD over the result — all
without a single embedding, vector store, or LLM call, exactly as scoped.

Three real bugs were found and fixed along the way (SQLite thread pooling,
JWT-subject UUID conversion, and Pydantic UUID/str schema typing) — all
three were latent in the design as written and only surfaced once Phase 2
actually exercised the code paths for the first time, which is itself a
concrete demonstration of why integration testing matters even when unit
tests are green.

Every document uploaded through this pipeline now has: extracted text,
structured metadata (title, author, language, word/char counts, reading
time), a fully cleaned version of its content, and a set of database-backed
chunks — everything Phase 3's Embedding Agent needs, and nothing it
doesn't.
