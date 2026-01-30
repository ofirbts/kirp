"""
Event Pipeline — Ingest → Store → RAG → Governance → Agents.

Single flow: Ingest → Governance check → Store (Mongo) → Embed → Qdrant → Publish Kafka → Trigger agents.
No state mutation without event. Multi-tenant isolated.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.event_store import Event, EventStore, Sensitivity

logger = logging.getLogger(__name__)


class EventPipeline:
    """
    Orchestrates ingest: event store, RAG, governance, agents.
    """

    def __init__(
        self,
        store: EventStore,
        rag: Any,
        schema: Any,
        gov: Any,
        agents: Any,
    ) -> None:
        self._store = store
        self._rag = rag
        self._schema = schema
        self._gov = gov
        self._agents = agents

    async def run(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        source: str,
        content: str,
        metadata: dict | None = None,
        sensitivity: Sensitivity | None = None,
        event_id: UUID | None = None,
    ) -> UUID:
        """
        Run full pipeline: governance → store → embed → Qdrant → (optional) trigger agents.
        Returns event ID. Pass event_id when re-ingesting from Kafka to preserve id.
        """
        if not tenant_id or tenant_id == "*":
            raise ValueError("tenant_id is required (multi-tenant isolation)")

        meta = metadata or {}
        sens = sensitivity or Sensitivity.PRIVATE

        # Governance check
        check = await self._gov.check(
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            action="write",
            resource="event",
            context={"sensitivity": sens.value, "resource_type": "event"},
        )
        if not check.allowed:
            raise PermissionError(f"Governance denied: {check.reason}")

        event_id = event_id or uuid4()
        trace_id = meta.get("trace_id") or f"tr_{event_id.hex[:8]}"

        # Create event (embedding filled below)
        event = Event(
            id=event_id,
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            source=source,
            content=content,
            metadata={**meta, "trace_id": trace_id},
            embedding=[],
            timestamp=datetime.now(timezone.utc),
            sensitivity=sens,
            event_type="ingest",
            trace_id=trace_id,
        )

        # Embed and upsert to Qdrant (best-effort)
        try:
            emb = await self._rag.embed(content)
            event.embedding = emb
            await self._rag.upsert(
                points=[{
                    "id": str(event_id),
                    "embedding": emb,
                    "content": content,
                    "source": source,
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "timestamp": event.timestamp.isoformat(),
                    "trace_id": trace_id,
                }],
                tenant_id=tenant_id,
                space_id=space_id,
            )
        except Exception as e:
            logger.warning("RAG embed/upsert failed (event still stored): %s", e)

        # Store in Mongo (source of truth)
        await self._store.ingest(event)
        logger.info("Pipeline stored event %s tenant=%s trace=%s", event_id, tenant_id, trace_id)
        return event.id
