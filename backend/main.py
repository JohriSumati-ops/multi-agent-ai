"""
main.py

WHY THIS FILE EXISTS
---------------------
The single composition point where configuration, logging, middleware,
exception handling, and routers are all wired together into one FastAPI
`app` instance. Nothing else in the codebase should construct a FastAPI
app — every other module either gets imported by this one or is invoked
independently (e.g., a future Celery worker, a future CLI script).

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Composition Root, applied at the application level (see api/deps.py for
the per-request version of the same idea). Keeping this file thin — it
delegates to `core.logging`, `middleware.*`, and `api.routes.*` rather than
defining logic inline — is what keeps the app understandable as it grows
across future phases.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Phase 2+ routers (documents, chat, quiz, knowledge_graph, progress) get
included here with `app.include_router(...)`, exactly like Phase 1's
health/version routers. No other change to this file should be needed as
the API surface grows.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401 — see models/__init__.py: importing this registers all ORM mappers
from api.routes import health, version
from core.config import settings
from core.logging import configure_logging, get_logger
from middleware.error_handler import register_exception_handlers
from middleware.logging_middleware import RequestLoggingMiddleware

configure_logging()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s, debug=%s)", settings.APP_NAME, settings.ENVIRONMENT, settings.DEBUG)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)

    # Phase 1 routes only. Future routers (documents, chat, quiz,
    # knowledge_graph, progress) mount here under settings.API_V1_PREFIX.
    app.include_router(health.router, prefix=settings.API_V1_PREFIX)
    app.include_router(version.router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["system"])
    def root() -> dict:
        return {
            "message": f"{settings.APP_NAME} API",
            "docs": "/docs",
            "health": f"{settings.API_V1_PREFIX}/health",
        }

    return app


app = create_app()
