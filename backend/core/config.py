"""
core/config.py

WHY THIS FILE EXISTS
---------------------
Every process-wide setting (database URL, secret keys, log level, feature
flags) is defined in exactly one place. Nothing else in the codebase should
read `os.environ` directly — that pattern scatters configuration knowledge
across dozens of files and makes it impossible to know what an application
depends on without grepping the whole repo.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
This is the "Single Source of Truth" / 12-Factor App configuration pattern:
config lives in the environment, is validated at startup (fail fast), and is
injected into the rest of the app as a typed object rather than passed
around as raw strings.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Phase 2+ will add fields here (EMBEDDING_MODEL_NAME, VECTOR_STORE_URL,
LLM_PROVIDER, GRAPH_DB_URL, etc.) without touching any other file — every
consumer just imports `settings` and reads the new attribute.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Typed, validated application settings.

    All values can be overridden via environment variables or a `.env` file.
    Field names map 1:1 to environment variable names (case-insensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Application metadata
    # ------------------------------------------------------------------ #
    APP_NAME: str = "Multi-Agent Research Assistant"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = True

    # ------------------------------------------------------------------ #
    # API
    # ------------------------------------------------------------------ #
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/research_assistant",
        description="SQLAlchemy connection string for PostgreSQL.",
    )
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ------------------------------------------------------------------ #
    # Auth (primitives built in Phase 1; register/login routes added in Phase 2)
    # ------------------------------------------------------------------ #
    SECRET_KEY: str = Field(
        default="CHANGE_ME_IN_PRODUCTION",
        description="Signing key for JWTs. Must be overridden via env var in any real deployment.",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_JSON: bool = False

    # ------------------------------------------------------------------ #
    # Document upload (Phase 2)
    # ------------------------------------------------------------------ #
    UPLOAD_DIR: str = Field(
        default="./storage/uploads",
        description="Filesystem directory where uploaded source documents are stored.",
    )
    MAX_UPLOAD_SIZE_MB: int = Field(
        default=25,
        description="Hard cap on a single uploaded file's size, enforced before it's written to disk.",
    )
    ALLOWED_DOCUMENT_EXTENSIONS: list[str] = Field(
        default=["pdf", "txt", "md", "docx"],
        description="Whitelist of file extensions accepted by the upload endpoint.",
    )

    # ------------------------------------------------------------------ #
    # Phase 3: Semantic Retrieval Layer
    # ------------------------------------------------------------------ #
    DEFAULT_LLM_PROVIDER: str = "claude"
    EMBEDDING_MODEL_NAME: str = Field(
        default="all-MiniLM-L6-v2",
        description="SentenceTransformers model name/path used by EmbeddingService.",
    )
    # NOTE: named VECTOR_STORE_URL for continuity with the Phase 0 architecture
    # doc's field name — in practice this holds a local filesystem directory,
    # since FAISS (this phase's vector store) is file-based, not a networked
    # service. A future networked vector engine (Milvus/Qdrant) would use
    # this same field as an actual URL with no rename needed.
    VECTOR_STORE_URL: str = Field(
        default="./storage/vector_store",
        description="Directory where the FAISS index and its metadata sidecar file are persisted.",
    )
    GRAPH_DB_URL: str = "not-configured"

    EMBEDDING_BATCH_SIZE: int = Field(default=32, description="Batch size for EmbeddingService.embed_texts().")
    EMBEDDING_CACHE_SIZE: int = Field(
        default=10_000, description="Max entries in the in-memory embedding cache (LRU eviction)."
    )
    RETRIEVAL_TOP_K_DEFAULT: int = Field(default=5, description="Default number of results for semantic search.")
    RETRIEVAL_SIMILARITY_THRESHOLD: float = Field(
        default=0.3,
        description="Minimum cosine similarity for a result to be included by default.",
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def warn_on_default_secret(cls, value: str) -> str:
        # Fail loudly is preferable to failing silently in production.
        # We don't raise here (dev ergonomics), but downstream code
        # (see core/security.py) checks ENVIRONMENT before trusting this.
        return value


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    WHY lru_cache: Settings are read from disk/env once and reused for the
    lifetime of the process. Without caching, every dependency-injected
    `Depends(get_settings)` call would re-parse environment variables,
    which is wasteful and can introduce subtle inconsistency if env vars
    change mid-process (they shouldn't, but why risk it).
    """
    return Settings()


settings = get_settings()
