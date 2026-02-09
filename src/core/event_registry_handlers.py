"""
Event Registry Handlers — Implementations for ingest.v1 and agent_run.v1.

Delegates to EventPipeline and AgentEngine. Uses CanonicalEvent as input.
"""

from __future__ import annotations

import os
import logging
from typing import Any
from uuid import UUID, uuid4

from src.models.event import CanonicalEvent, EVENT_TYPE_INGEST, EVENT_TYPE_AGENT_RUN

logger = logging.getLogger(__name__)


async def _get_pipeline() -> Any:
    """Lazy init pipeline components (same as kafka_processor)."""
    from src.core.event_store import EventStore, Sensitivity
    from src.core.rag_engine import RAGEngine
    from src.core.schema_engine import SchemaEngine
    from src.core.governance import GovernanceEngine
    from src.core.agent_registry import get_agent_framework_with_all_agents
    from src.core.pipeline import EventPipeline

    store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
    await store.connect()
    rag = RAGEngine(
        qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    await rag.connect()
    schema = SchemaEngine(
        os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp")
    )
    await schema.connect()
    gov = GovernanceEngine(os.getenv("OPA_URL", "http://opa:8181"))
    af = get_agent_framework_with_all_agents()
    return EventPipeline(store, rag, schema, gov, af)


async def handle_ingest_v1(event: CanonicalEvent) -> UUID:
    """
    Handle ingest.v1: run full pipeline (governance → store → embed → history → schema).
    Returns event ID.
    """
    if not event.tenant_id or event.tenant_id == "*":
        raise ValueError("tenant_id is required (multi-tenant isolation)")

    logger.info(
        "handle_ingest_v1: tenant=%s space=%s user=%s source=%s content_len=%d",
        event.tenant_id, event.space_id, event.user_id, event.source, len(event.content or ""),
    )
    pipe = await _get_pipeline()
    meta = dict(event.metadata or {})
    if event.trace_id:
        meta.setdefault("trace_id", event.trace_id)

    return await pipe.run(
        tenant_id=event.tenant_id,
        space_id=event.space_id,
        user_id=event.user_id,
        source=event.source,
        content=event.content,
        metadata=meta,
        event_id=event.id,
    )


async def handle_agent_run_v1(event: CanonicalEvent) -> dict[str, Any]:
    """
    Handle agent_run.v1: execute agent by agent_id with input context.
    Returns agent result dict.
    """
    agent_id = event.agent_id
    if not agent_id:
        return {"ok": False, "error": "agent_id is required for agent_run.v1"}

    from src.core.agent_framework import get_agent_framework_with_all_agents
    from src.core.agent_engine import get_agent_engine

    af = get_agent_framework_with_all_agents()
    spec = af.get(agent_id)
    if not spec or not getattr(spec, "handler", None):
        return {"ok": False, "error": f"Agent not found or no handler: {agent_id}"}

    engine = get_agent_engine()
    run_id = event.id
    result = await engine.execute_run(
        run_id=run_id,
        agent_name=agent_id,
        tenant_id=event.tenant_id,
        space_id=event.space_id,
        user_id=event.user_id,
        context=event.input or {},
        handler=spec.handler,
    )
    return result
