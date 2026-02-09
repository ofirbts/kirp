"""
Event Pipeline — Ingest → Store → RAG → Governance → Agents → Life Objects.

Single flow: Ingest → Governance check → Store (Mongo) → Embed → Qdrant → Life-object extraction → Schema upsert.
No state mutation without event. Multi-tenant isolated.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4, uuid5

from src.core.event_store import Event, EventStore, Sensitivity
from src.core.life_objects import extract_life_objects
from src.models.schema import SchemaEntity

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

        # History 2.0: human-readable timeline entry by source
        try:
            from src.core.history import record_history
            hist_type = "system"
            title = "Content ingested"
            body = (content[:200] + "…") if len(content) > 200 else content or ""
            if source == "email":
                hist_type = "email_received"
                from_addr = (meta.get("from") or "").strip() or "unknown"
                title = "Email received from " + (from_addr[:60] + "…" if len(from_addr) > 60 else from_addr)
            elif source == "whatsapp":
                hist_type = "whatsapp_message"
                from_addr = (meta.get("from") or meta.get("sender") or "").strip() or "unknown"
                title = "Message from " + (from_addr[:60] + "…" if len(from_addr) > 60 else from_addr)
            elif source == "slack":
                hist_type = "slack_message"
                ch = (meta.get("channel") or meta.get("channel_id") or "").strip() or "channel"
                title = "Slack message in #" + (ch[:40] + "…" if len(ch) > 40 else ch)
            elif source == "calendar":
                hist_type = "calendar_event"
                title = (meta.get("summary") or content.split("\n")[0] if content else "Calendar event")[:80]
                title = "Calendar event: " + (title or "Event")
            elif source == "notion":
                hist_type = "notion_sync"
                title = "Notion page synced"
                body = (content[:150] + "…") if len(content) > 150 else (content or "")
            await record_history(
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
                type_=hist_type,
                title=title,
                body=body,
                source=source,
                entity_id=str(event_id),
                meta={"trace_id": trace_id, "event_id": str(event_id)},
            )
            logger.info(
                "[INGEST] history entry written: tenant=%s user=%s type=%s event_id=%s",
                tenant_id, user_id, hist_type, event_id,
            )
        except Exception as e:
            logger.warning("History record failed after ingest: %s", e)

        # Life-object extraction → classification + NLP dates → SchemaEngine upsert (Phase 2)
        try:
            # Ensure canonical Life Areas exist (Work, Family, Health, Learning)
            await self._schema.ensure_life_areas(tenant_id, space_id)
            objects = extract_life_objects(
                event.content,
                event_id=str(event_id),
                user_id=user_id,
                source=source,
            )
            for obj in objects:
                entity = obj.get("entity") or SchemaEntity.TASK
                title = (obj.get("title") or "").strip() or "(no title)"
                due_date = obj.get("due_date")
                context = obj.get("context")
                # Stable node_id per event + entity + title for upsert idempotency
                node_id = str(uuid5(event_id, f"{entity.value}:{title}"))
                meta: dict[str, Any] = {
                    "source_event_id": str(event_id),
                    "source": source,
                    "user_id": user_id,
                    **(obj.get("metadata") or {}),
                }
                if context:
                    meta["context"] = context
                # Notion bi-directional: store external_id so we can push updates back
                if source == "notion" and event.metadata:
                    if event.metadata.get("external_id"):
                        meta["notion_page_id"] = event.metadata["external_id"]
                    if event.metadata.get("page_id"):
                        meta.setdefault("notion_page_id", event.metadata["page_id"])
                    if event.metadata.get("last_edited_time"):
                        meta["notion_last_edited_time"] = event.metadata["last_edited_time"]
                # Commitments: due_date, source_event_id, owner (already in meta from extract_life_objects)
                await self._schema.upsert_node(
                    tenant_id=tenant_id,
                    space_id=space_id,
                    entity=entity,
                    title=title,
                    node_id=node_id,
                    due_date=due_date,
                    metadata=meta,
                )
        except Exception as e:
            logger.warning("Life-object extraction/upsert failed (event already stored): %s", e)

        return event.id

    async def run_post_ingest_for_event(self, event_id: UUID) -> bool:
        """
        Re-run embed → Qdrant → life-object extraction → schema upsert for an existing event.
        Used after updating an event (e.g. Notion webhook: update_by_external_id then this).
        Does not write to event store. Returns False if event not found.
        """
        event = await self._store.get_by_id(event_id)
        if not event:
            return False
        tenant_id = event.tenant_id
        space_id = event.space_id
        user_id = event.user_id
        source = event.source
        content = event.content
        trace_id = (event.metadata or {}).get("trace_id", "")

        try:
            emb = await self._rag.embed(content)
            await self._rag.upsert(
                points=[{
                    "id": str(event_id),
                    "embedding": emb,
                    "content": content,
                    "source": source,
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "timestamp": event.timestamp.isoformat() if event.timestamp else "",
                    "trace_id": trace_id,
                }],
                tenant_id=tenant_id,
                space_id=space_id,
            )
        except Exception as e:
            logger.warning("RAG embed/upsert failed in run_post_ingest_for_event: %s", e)

        try:
            await self._schema.ensure_life_areas(tenant_id, space_id)
            objects = extract_life_objects(
                content,
                event_id=str(event_id),
                user_id=user_id,
                source=source,
            )
            for obj in objects:
                entity = obj.get("entity") or SchemaEntity.TASK
                title = (obj.get("title") or "").strip() or "(no title)"
                due_date = obj.get("due_date")
                context = obj.get("context")
                node_id = str(uuid5(event_id, f"{entity.value}:{title}"))
                meta: dict[str, Any] = {
                    "source_event_id": str(event_id),
                    "source": source,
                    "user_id": user_id,
                    **(obj.get("metadata") or {}),
                }
                if context:
                    meta["context"] = context
                if source == "notion" and event.metadata:
                    if event.metadata.get("external_id"):
                        meta["notion_page_id"] = event.metadata["external_id"]
                    if event.metadata.get("page_id"):
                        meta.setdefault("notion_page_id", event.metadata["page_id"])
                    if event.metadata.get("last_edited_time"):
                        meta["notion_last_edited_time"] = event.metadata["last_edited_time"]
                await self._schema.upsert_node(
                    tenant_id=tenant_id,
                    space_id=space_id,
                    entity=entity,
                    title=title,
                    node_id=node_id,
                    due_date=due_date,
                    metadata=meta,
                )
        except Exception as e:
            logger.warning("Life-object extraction/upsert failed in run_post_ingest_for_event: %s", e)
        return True
