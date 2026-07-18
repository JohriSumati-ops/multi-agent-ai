# Multi-Agent Research Assistant — Backend (Phase 1)

Production-quality backend **skeleton**. No AI logic — no PDF parsing, no
embeddings, no LLM calls, no agents. Phase 1 is architecture, made
runnable and testable.

See `docs/PROJECT_STRUCTURE.md` for the folder map and
`docs/PHASE_1_LEARNING_NOTES.md` for the "what does this teach me" writeup.

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

| Implemented in Phase 1 | Reserved for later phases |
|---|---|
| FastAPI app, routing, DI, middleware | PDF parsing, chunking, embeddings |
| Config, logging, exception handling | Retrieval / hybrid search |
| PostgreSQL models + repositories + service layer | Knowledge graph construction |
| Auth primitives (hashing, JWT encode/decode) | Login/signup HTTP routes |
| Agent interface (`BaseAgent`) | Every concrete agent (Reading, Quiz, ...) |
| LLM abstraction interface (`BaseLLM`) | Every concrete provider implementation |
| Confidence + Explainability schema frameworks | Agents that actually populate them |
| Agent execution logging table + repository | Agents that actually write to it |

Every "reserved" item above has a docstring at its intended location
explaining exactly how a future phase will fill it in — see `retrieval/__init__.py`,
`knowledge_graph/__init__.py`, and the `NotImplementedError` bodies in
`llm/providers/*.py`.
