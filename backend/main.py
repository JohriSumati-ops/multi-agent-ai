"""
main.py

Application entry point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

import models  # noqa: F401
from api.routes import auth, documents, health, version
from core.config import settings
from core.logging import configure_logging, get_logger
from database.init_db import init_db
from middleware.error_handler import register_exception_handlers
from middleware.logging_middleware import RequestLoggingMiddleware

configure_logging()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (env=%s, debug=%s)",
        settings.APP_NAME,
        settings.ENVIRONMENT,
        settings.DEBUG,
    )

    # Create database tables
    init_db()

    logger.info("Database initialized successfully.")

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

    # Phase 1
    app.include_router(health.router, prefix=settings.API_V1_PREFIX)
    app.include_router(version.router, prefix=settings.API_V1_PREFIX)

    # Phase 2
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
    app.include_router(documents.router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["System"])
    def root():
        return {
            "message": f"{settings.APP_NAME} API",
            "docs": "/docs",
            "health": f"{settings.API_V1_PREFIX}/health",
        }

    # -----------------------------
    # Swagger JWT Bearer Support
    # -----------------------------
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        openapi_schema.setdefault("components", {})
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }

        # Protect every documents endpoint
        for path, methods in openapi_schema["paths"].items():
            if path.startswith("/api/v1/documents"):
                for method in methods.values():
                    method["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app


app = create_app()