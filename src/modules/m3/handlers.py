"""
M3 IdentityOS — Event Registry handlers.

Each M3 event type is dispatched through the same KIRP pipeline (governance → store → embed → …)
with event_type and metadata.module = "m3" preserved for audit.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.models.event import CanonicalEvent
from src.modules.m3.events import ensure_m3_metadata, is_m3_event_type

logger = logging.getLogger(__name__)


async def _get_pipeline() -> Any:
    """Lazy init pipeline (same pattern as event_registry_handlers)."""
    import os
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


async def handle_m3_event(event: CanonicalEvent) -> UUID:
    """
    Handle any M3 event: ensure metadata.module = m3, then run full pipeline.
    Preserves event_type (e.g. m3.daily_reflection_submitted) for audit and filtering.
    """
    if not event.tenant_id or event.tenant_id == "*":
        raise ValueError("tenant_id is required (multi-tenant isolation)")
    if not is_m3_event_type(event.event_type):
        raise ValueError(f"Expected M3 event_type, got {event.event_type}")

    meta = ensure_m3_metadata(event.metadata)
    if event.trace_id:
        meta.setdefault("trace_id", event.trace_id)
    if event.run_id:
        meta.setdefault("run_id", event.run_id)
    if event.workflow_type:
        meta.setdefault("workflow_type", event.workflow_type)
    if event.idempotency_key:
        meta.setdefault("idempotency_key", event.idempotency_key)
    if event.parent_run_id:
        meta.setdefault("parent_run_id", event.parent_run_id)

    # Content: for ingest-like M3 events use content or a stringified payload from metadata
    content = event.content or ""
    if not content and meta.get("reflection_text"):
        content = str(meta.get("reflection_text", ""))[:4096]
    if not content and meta.get("summary"):
        content = str(meta.get("summary", ""))[:4096]

    logger.info(
        "handle_m3_event: type=%s tenant=%s space=%s user=%s source=%s",
        event.event_type, event.tenant_id, event.space_id, event.user_id, event.source or "m3",
    )
    pipe = await _get_pipeline()
    event_id = await pipe.run(
        tenant_id=event.tenant_id,
        space_id=event.space_id,
        user_id=event.user_id,
        source=event.source or "m3",
        content=content,
        metadata=meta,
        event_id=event.id,
        event_type=event.event_type,
    )
    # Stage 9 writeback: update M3 Typed Memory (reflection_entries, micro_actions, etc.)
    from src.modules.m3.writeback import m3_memory_writeback
    await m3_memory_writeback(
        event_type=event.event_type,
        tenant_id=event.tenant_id,
        space_id=event.space_id,
        user_id=event.user_id,
        event_id=event_id,
        metadata=meta,
        content=content,
    )
    # Stages 2–5: context retrieval + M3 agents (ReflectionClassifier, GapAnalysis, MicroActionGenerator, Discriminator, Synthesis/Evolution)
    from src.modules.m3.stages import run_m3_stages
    await run_m3_stages(
        event_type=event.event_type,
        tenant_id=event.tenant_id,
        space_id=event.space_id,
        user_id=event.user_id,
        metadata=meta,
        content=content,
    )
    return event_id
