"""
Runtime configuration for KIRP Enterprise.

Centralizes environment variables for:
- MongoDB / Postgres / Qdrant
- OPA / JWT
- Environment separation (dev / staging / prod)

This is a soft introduction of data contracts & deployment governance:
all external URIs and secrets flow through a single typed Settings object.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:
    BaseSettings = None  # type: ignore[misc, assignment]
    SettingsConfigDict = None  # type: ignore[misc, assignment]


def _settings_base():
    if BaseSettings is not None and SettingsConfigDict is not None:
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")
            env: Literal["development", "local", "staging", "production"] = Field(default="development")
            mongo_uri: str = Field(default=os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
            postgres_uri: str = Field(default=os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp"))
            qdrant_url: str = Field(default=os.getenv("QDRANT_URL", "http://qdrant:6333"))
            qdrant_collection: str = Field(default=os.getenv("QDRANT_COLLECTION", "kirp_vectors"))
            qdrant_api_key: str | None = Field(default=os.getenv("QDRANT_API_KEY"))
            opa_url: str | None = Field(default=os.getenv("OPA_URL"))
            jwt_secret: str = Field(default=os.getenv("JWT_SECRET", "dev-secret-change-me"))
            embedding_refresh_window_hours: int = Field(default=int(os.getenv("EMBEDDING_REFRESH_WINDOW_HOURS", "24")))
            embedding_refresh_limit_per_run: int = Field(default=int(os.getenv("EMBEDDING_REFRESH_LIMIT", "500")))
            pipeline_seed_mode: bool = Field(default=os.getenv("PIPELINE_SEED_MODE", "").lower() in ("1", "true", "yes"))
            disable_embeddings_in_pipeline: bool = Field(default=os.getenv("DISABLE_EMBEDDINGS", "").lower() in ("1", "true", "yes"))
            disable_schema_extraction_in_pipeline: bool = Field(default=os.getenv("DISABLE_SCHEMA_EXTRACTION", "").lower() in ("1", "true", "yes"))
            disable_agents_in_pipeline: bool = Field(default=os.getenv("DISABLE_AGENTS", "").lower() in ("1", "true", "yes"))
            disable_governance_in_pipeline: bool = Field(default=os.getenv("DISABLE_GOVERNANCE", "").lower() in ("1", "true", "yes"))
        return Settings
    from pydantic import BaseModel
    class Settings(BaseModel):
        model_config = {"extra": "ignore"}
        env: Literal["development", "local", "staging", "production"] = "development"
        mongo_uri: str = Field(default_factory=lambda: os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
        postgres_uri: str = Field(default_factory=lambda: os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp"))
        qdrant_url: str = Field(default_factory=lambda: os.getenv("QDRANT_URL", "http://qdrant:6333"))
        qdrant_collection: str = Field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "kirp_vectors"))
        qdrant_api_key: str | None = Field(default_factory=lambda: os.getenv("QDRANT_API_KEY"))
        opa_url: str | None = Field(default_factory=lambda: os.getenv("OPA_URL"))
        jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-secret-change-me"))
        embedding_refresh_window_hours: int = Field(default=24)
        embedding_refresh_limit_per_run: int = Field(default=500)
        pipeline_seed_mode: bool = Field(default=False)
        disable_embeddings_in_pipeline: bool = Field(default=False)
        disable_schema_extraction_in_pipeline: bool = Field(default=False)
        disable_agents_in_pipeline: bool = Field(default=False)
        disable_governance_in_pipeline: bool = Field(default=False)
    return Settings


class Settings(_settings_base()):
    """Typed runtime configuration. Extra env vars are ignored so Docker/legacy envs don't break loading."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    env: Literal["development", "local", "staging", "production"] = Field(
        default="development",
        description="Runtime environment.",
    )

    # Core stores
    mongo_uri: str = Field(
        default="mongodb://root:example@mongodb:27017/kirp?authSource=admin",
        env="MONGO_URI",
    )
    postgres_uri: str = Field(
        default="postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp",
        env="POSTGRES_URI",
    )
    qdrant_url: str = Field(
        default="http://qdrant:6333",
        env="QDRANT_URL",
    )
    qdrant_collection: str = Field(
        default="kirp_vectors",
        env="QDRANT_COLLECTION",
    )
    qdrant_api_key: str | None = Field(default=None, env="QDRANT_API_KEY")
    # Governance / security
    opa_url: str | None = Field(default=None, env="OPA_URL")
    jwt_secret: str = Field(default="dev-secret-change-me", env="JWT_SECRET")

    # Embedding refresh / RAG policies
    embedding_refresh_window_hours: int = Field(
        default=24,
        env="EMBEDDING_REFRESH_WINDOW_HOURS",
        description="Time window (hours) to consider events for embedding refresh.",
    )
    embedding_refresh_limit_per_run: int = Field(
        default=500,
        env="EMBEDDING_REFRESH_LIMIT",
        description="Maximum number of events to refresh per scheduler run.",
    )

    # Pipeline seed mode — skip LLM-dependent steps so seed_mongo can run without OpenAI
    pipeline_seed_mode: bool = Field(
        default=False,
        env="PIPELINE_SEED_MODE",
        description="When True, skip embeddings, schema extraction, agents, and governance in ingest (for local seeding).",
    )
    disable_embeddings_in_pipeline: bool = Field(
        default=False,
        env="DISABLE_EMBEDDINGS",
        description="Skip embedding generation and Qdrant upsert during ingest.",
    )
    disable_schema_extraction_in_pipeline: bool = Field(
        default=False,
        env="DISABLE_SCHEMA_EXTRACTION",
        description="Skip SchemaStructureAgent and schema node extraction during ingest.",
    )
    disable_agents_in_pipeline: bool = Field(
        default=False,
        env="DISABLE_AGENTS",
        description="Skip agent triggers (RAG, analysis, presentation) during ingest.",
    )
    disable_governance_in_pipeline: bool = Field(
        default=False,
        env="DISABLE_GOVERNANCE",
        description="Skip governance check and audit during ingest (allow completion).",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()

