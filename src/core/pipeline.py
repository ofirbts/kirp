"""
Event Processing Pipeline (MANDATORY) — 9 steps.

1. Ingest event
2. Store raw in Mongo
3. Generate embedding -> Qdrant
4. Store metadata -> Postgres
5. Publish event -> Kafka / Redis Streams
6. Trigger agents
7. Governance check
8. Execute action
9. Emit new event

No state mutation without event. Every decision auditable, explainable, replayable.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.event_store import Event, EventStore, Sensitivity
from src.core.rag_engine import RAGEngine
from src.core.schema_engine import SchemaEngine
from src.core.governance import GovernanceEngine
from src.core.agent_framework import AgentFramework
from src.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class EventPipeline:
    """9-step event processing pipeline."""

    def __init__(
        self,
        event_store: EventStore,
        rag_engine: RAGEngine,
        schema_engine: SchemaEngine,
        governance: GovernanceEngine,
        agent_framework: AgentFramework,
    ) -> None:
        self._events = event_store
        self._rag = rag_engine
        self._schema = schema_engine
        self._governance = governance
        self._agents = agent_framework
        self._event_bus = EventBus()

    async def run(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        source: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
    ) -> UUID:
        """
        Execute full pipeline: ingest -> store -> embed -> Qdrant -> metadata -> publish
        -> trigger agents -> governance -> execute -> emit.
        """
        trace_id = f"tr_{uuid4().hex[:12]}"
        ev = Event(
            id=uuid4(),
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            source=source,
            content=content,
            metadata=metadata or {},
            embedding=[],
            timestamp=datetime.now(timezone.utc),
            sensitivity=sensitivity,
            event_type="ingest",
            trace_id=trace_id,
        )

        # 1. Ingest event (already have ev)
        # 2. Store raw in Mongo
        await self._events.ingest(ev)

        # 3. Generate embedding -> Qdrant
        emb = await self._rag.embed(content)
        ev.embedding = emb
        points = [{"id": str(ev.id), "embedding": emb, "content": content, "source": source, "user_id": user_id}]
        await self._rag.upsert(points, tenant_id=tenant_id, space_id=space_id)

        # 4. Store metadata -> Postgres (via schema_engine; optional for raw ingest)
        # Skip if no schema nodes extracted; schema_structure agent can do it later.

        # 5. Publish event -> Kafka / Redis Streams (JSON-safe payload)
        await self._event_bus.connect()
        await self._event_bus.publish("kirp-events", {
            "type": "ingest",
            "data": ev.to_json_payload(),
            "trace_id": trace_id,
        })

        # 6. Trigger agents
        for spec in self._agents.list_by_trigger("ingest"):
            rag_resp = await self._rag.search(content, tenant_id=tenant_id, space_id=space_id, user_id=user_id, limit=5)
            ctx = {"rag_response": rag_resp, "events": [ev], "trace_id": trace_id}
            agent_result = await self._agents.run(spec.name, tenant_id=tenant_id, space_id=space_id, user_id=user_id, context=ctx)
            # If agent requires approval, emit approval event
            if agent_result.get("requires_approval"):
                approval_ev = Event(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    space_id=space_id,
                    user_id=user_id,
                    source="governance",
                    content=f"Approval required for {spec.name}",
                    metadata={"agent": spec.name, "result": agent_result, "original_trace": trace_id},
                    embedding=[],
                    timestamp=datetime.now(timezone.utc),
                    sensitivity=sensitivity,
                    event_type="human_approval_required",
                    trace_id=trace_id,
                )
                await self._events.ingest(approval_ev)

        # 7. Governance check
        check = await self._governance.check(
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            action="ingest",
            resource="event",
            context={"trace_id": trace_id, "sensitivity": sensitivity.value, "resource_type": "event"},
        )
        if not check.allowed:
            logger.warning("Governance denied ingest trace=%s reason=%s risk=%.2f", trace_id, check.reason, check.risk_score)
            await self._governance.log_audit(
                tenant_id=tenant_id,
                user_id=user_id,
                action="ingest",
                resource="event",
                result="denied",
                details={"trace_id": trace_id, "reason": check.reason, "risk_score": check.risk_score},
            )
            raise PermissionError(check.reason)

        if check.requires_approval:
            # Emit approval-required event
            approval_ev = Event(
                id=uuid4(),
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
                source="governance",
                content=f"High-risk action requires approval (risk={check.risk_score:.2f})",
                metadata={"original_event_id": str(ev.id), "risk_score": check.risk_score, "reason": check.reason},
                embedding=[],
                timestamp=datetime.now(timezone.utc),
                sensitivity=sensitivity,
                event_type="human_approval_required",
                trace_id=trace_id,
            )
            await self._events.ingest(approval_ev)

        # 8. Execute action (ingest itself is the action; outbound e.g. Notion happens in agents)
        # 9. Emit new event (already stored; emit completion event)
        completion_ev = Event(
            id=uuid4(),
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            source="pipeline",
            content=f"Ingest completed: {content[:100]}",
            metadata={"original_event_id": str(ev.id), "status": "completed"},
            embedding=[],
            timestamp=datetime.now(timezone.utc),
            sensitivity=sensitivity,
            event_type="ingest_completed",
            trace_id=trace_id,
        )
        await self._events.ingest(completion_ev)

        return ev.id
