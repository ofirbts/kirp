"""
Single construction path for EventPipeline in workers and event-registry handlers.

API requests use ``main.get_pipeline()`` (cached singletons + shared RAG). Everything
that today built EventPipeline manually with fresh store/rag/schema should call
``create_connected_event_pipeline`` here so wiring stays consistent.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def create_connected_event_pipeline() -> Any:
    """
    Build EventPipeline with dedicated store/rag/schema connections.

    Defaults match worker-oriented env (localhost service names); production sets
    MONGO_URI / POSTGRES_URI / QDRANT_URL / OPA_URL via compose.
    """
    from src.core.agent_registry import get_agent_framework_with_all_agents
    from src.core.event_store import EventStore
    from src.core.governance import GovernanceEngine
    from src.core.pipeline import EventPipeline
    from src.core.rag_engine import RAGEngine
    from src.core.schema_engine import SchemaEngine

    store = EventStore(
        os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin")
    )
    await store.connect()
    rag = RAGEngine(
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    await rag.connect()
    schema = SchemaEngine(
        os.getenv(
            "POSTGRES_URI",
            "postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp",
        )
    )
    await schema.connect()
    gov = GovernanceEngine(os.getenv("OPA_URL"))
    af = get_agent_framework_with_all_agents()
    return EventPipeline(store, rag, schema, gov, af)
