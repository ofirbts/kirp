"""
Service Registry — Central Dependency Injection registry for managing database connections
and core engines (MongoDB, PostgreSQL, Qdrant, Redis, OPA).
"""

from __future__ import annotations

import logging
import os
from typing import Any
from functools import lru_cache

from src.core.config import get_settings

logger = logging.getLogger(__name__)


def _allow_degraded_dependency_connect() -> bool:
    env = (os.getenv("ENV") or get_settings().env or "development").strip().lower()
    if env in ("development", "local", "test"):
        return True
    return os.getenv("KIRP_ALLOW_DEGRADED_DEPS", "").lower() in ("1", "true", "yes")


class ServiceRegistry:
    """
    Central dependency injection registry.
    Manages lazy initialization and caching of database clients and engines.
    """

    _instance: ServiceRegistry | None = None

    def __new__(cls) -> ServiceRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_registry()
        return cls._instance

    def _init_registry(self) -> None:
        self._mongo_client: Any = None
        self._mongo_db: Any = None
        self._postgres_engine: Any = None
        self._qdrant_client: Any = None
        self._redis_client: Any = None
        self._redis_async: Any = None
        self._governance_engine: Any = None
        self._event_store: Any = None
        self._rag_engine: Any = None
        self._schema_engine: Any = None
        self._agent_framework: Any = None
        self._pipeline: Any = None

    async def get_mongo_client(self) -> Any:
        if self._mongo_client is None:
            from motor.motor_asyncio import AsyncIOMotorClient
            settings = get_settings()
            self._mongo_client = AsyncIOMotorClient(settings.mongo_uri, maxPoolSize=50, minPoolSize=5)
            logger.info("ServiceRegistry initialized MongoDB client")
        return self._mongo_client

    async def get_mongo_db(self) -> Any:
        if self._mongo_db is None:
            client = await self.get_mongo_client()
            db_name = os.getenv("MONGO_DB_NAME", "kirp")
            self._mongo_db = client[db_name]
        return self._mongo_db

    def get_postgres_engine(self) -> Any:
        if self._postgres_engine is None:
            from sqlalchemy import create_engine
            settings = get_settings()
            # Construct standard sync engine (similar to integrations.py)
            url = settings.postgres_uri.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
            self._postgres_engine = create_engine(
                url,
                echo=False,
                future=True,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True,
            )
            logger.info("ServiceRegistry initialized PostgreSQL sync engine")
        return self._postgres_engine

    def get_postgres_session(self) -> Any:
        from sqlalchemy.orm import sessionmaker
        engine = self.get_postgres_engine()
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        return Session()

    async def get_qdrant_client(self) -> Any:
        if self._qdrant_client is None:
            from qdrant_client import QdrantClient
            settings = get_settings()
            client_kw: dict[str, Any] = {"url": settings.qdrant_url}
            if settings.qdrant_api_key:
                client_kw["api_key"] = settings.qdrant_api_key
            self._qdrant_client = QdrantClient(**client_kw)
            logger.info("ServiceRegistry initialized Qdrant client")
        return self._qdrant_client

    def get_redis_client(self) -> Any:
        if self._redis_client is None:
            import redis
            host = os.getenv("REDIS_HOST", "redis")
            port = int(os.getenv("REDIS_PORT", "6379"))
            self._redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            logger.info("ServiceRegistry initialized Redis sync client")
        return self._redis_client

    def get_redis_async(self) -> Any:
        if self._redis_async is None:
            import redis.asyncio as redis_async
            url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            self._redis_async = redis_async.from_url(url, decode_responses=True)
            logger.info("ServiceRegistry initialized Redis async client")
        return self._redis_async

    def get_governance(self) -> Any:
        if self._governance_engine is None:
            from src.core.governance import GovernanceEngine
            settings = get_settings()
            self._governance_engine = GovernanceEngine(settings.opa_url)
            logger.info("ServiceRegistry initialized GovernanceEngine")
        return self._governance_engine

    async def get_event_store(self) -> Any:
        if self._event_store is None:
            from src.core.event_store import EventStore
            settings = get_settings()
            store = EventStore(settings.mongo_uri)
            await store.connect()
            self._event_store = store
            logger.info("ServiceRegistry initialized EventStore")
        return self._event_store

    async def get_rag_engine(self) -> Any:
        if self._rag_engine is None:
            from src.core.rag_engine import RAGEngine
            settings = get_settings()
            rag = RAGEngine(
                qdrant_url=settings.qdrant_url,
                qdrant_api_key=settings.qdrant_api_key,
                embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
                embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            )
            try:
                await rag.connect()
            except Exception as exc:
                if not _allow_degraded_dependency_connect():
                    raise
                logger.warning("RAGEngine connect failed (degraded mode): %s", exc)
            self._rag_engine = rag
            logger.info("ServiceRegistry initialized RAGEngine")
        return self._rag_engine

    async def get_schema_engine(self) -> Any:
        if self._schema_engine is None:
            from src.core.schema_engine import SchemaEngine
            settings = get_settings()
            schema = SchemaEngine(settings.postgres_uri)
            try:
                await schema.connect()
            except Exception as exc:
                if not _allow_degraded_dependency_connect():
                    raise
                logger.warning("SchemaEngine connect failed (degraded mode): %s", exc)
            self._schema_engine = schema
            logger.info("ServiceRegistry initialized SchemaEngine")
        return self._schema_engine

    def get_agent_framework(self) -> Any:
        if self._agent_framework is None:
            from src.core.agent_framework import AgentFramework
            from src.core.agent_registry import register_all_agents
            af = AgentFramework()
            register_all_agents(af)
            self._agent_framework = af
            logger.info("ServiceRegistry initialized AgentFramework")
        return self._agent_framework

    async def get_pipeline(self) -> Any:
        if self._pipeline is None:
            from src.core.pipeline import EventPipeline
            store = await self.get_event_store()
            rag = await self.get_rag_engine()
            schema = await self.get_schema_engine()
            gov = self.get_governance()
            agents = self.get_agent_framework()
            self._pipeline = EventPipeline(store, rag, schema, gov, agents)
            logger.info("ServiceRegistry initialized EventPipeline")
        return self._pipeline

    async def check_health(self) -> dict[str, Any]:
        """Runs checks on managed database connections."""
        health: dict[str, Any] = {}

        # Mongo
        try:
            db = await self.get_mongo_db()
            await db.command("ping")
            health["mongodb"] = "ok"
        except Exception as e:
            health["mongodb"] = f"error: {e}"

        # Redis
        try:
            r = self.get_redis_async()
            await r.ping()
            health["redis"] = "ok"
        except Exception as e:
            health["redis"] = f"error: {e}"

        # Postgres
        try:
            from sqlalchemy import text
            with self.get_postgres_session() as session:
                session.execute(text("SELECT 1"))
            health["postgres"] = "ok"
        except Exception as e:
            health["postgres"] = f"error: {e}"

        return health


_registry = ServiceRegistry()


def get_registry() -> ServiceRegistry:
    return _registry
