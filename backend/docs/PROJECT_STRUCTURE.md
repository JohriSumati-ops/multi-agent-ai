# Project Structure Reference

Quick-reference companion to the in-code docstrings. Every file listed
below has a full "why this exists / SE concept / how future phases use it"
docstring at the top — this table is just the map.

| Folder | Responsibility | Phase 1 Contents |
|---|---|---|
| `api/` | HTTP transport only — no business logic | `routes/health.py`, `routes/version.py`, `deps.py` |
| `core/` | Cross-cutting concerns every other layer depends on | `config.py`, `logging.py`, `exceptions.py`, `security.py`, `agent_bus.py` |
| `config/` | Environment-specific settings | `.env.example` |
| `database/` | Connection management, declarative base | `base.py`, `session.py` |
| `repositories/` | The ONLY layer allowed to write queries | One file per model + `base_repository.py` |
| `services/` | Business orchestration spanning repositories | `user_service.py` |
| `models/` | ORM / database schema | `user.py`, `document.py`, `conversation.py`, `message.py`, `learning_profile.py`, `memory.py`, `agent_execution_log.py` |
| `schemas/` | API request/response contracts | `base.py`, one file per resource, `agent_response.py`, `explainability.py` |
| `memory/` | Memory *policy* (what to remember), not storage | `interfaces.py` |
| `agents/` | Agent interface + supporting infra (no agents implemented yet) | `base_agent.py`, `activity_timeline.py` |
| `llm/` | Model abstraction layer (no models implemented yet) | `base_llm.py`, `providers/*_provider.py` |
| `retrieval/` | Reserved for Phase 2 (RAG pipeline) | placeholder docstring only |
| `knowledge_graph/` | Reserved for Phase 4 | placeholder docstring only |
| `utils/` | Stateless, dependency-free helpers | `text.py` |
| `middleware/` | Global error handling + request logging | `error_handler.py`, `logging_middleware.py` |
| `tests/` | Pytest suite, SQLite-backed | `conftest.py`, `test_health.py`, `test_user_service.py` |
| `scripts/` | Standalone runnable maintenance scripts | `seed_dev_data.py` |
| `docs/` | This file and the learning notes | `PROJECT_STRUCTURE.md`, `PHASE_1_LEARNING_NOTES.md` |

## Dependency Direction (enforced by convention, not by tooling, in Phase 1)

```
api/routes  →  services  →  repositories  →  database
     ↓
  api/deps (composition root)

agents (future) → llm (future) + memory (future) + repositories
```

Routers never import repositories. Repositories never import services.
Nothing outside `repositories/` and `database/` imports SQLAlchemy query
constructs. This is what makes each layer independently testable and
independently replaceable.
