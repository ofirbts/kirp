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
        Execute full pipeline with reasoning-aware context and improved sequencing.
        Enforces multi-tenant isolation.
        """
        # Enforce multi-tenant isolation
        if not tenant_id or tenant_id == "*":
            raise ValueError("tenant_id is required (multi-tenant isolation)")
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
        try:
            emb = await self._rag.embed(content)
            ev.embedding = emb
            points = [{"id": str(ev.id), "embedding": emb, "content": content, "source": source, "user_id": user_id}]
            await self._rag.upsert(points, tenant_id=tenant_id, space_id=space_id)
        except Exception as e:
            logger.warning("Embedding generation failed for event %s: %s. Continuing without embedding.", ev.id, e)
            # Continue without embedding - event is still stored

        # 4. Extract and store schema nodes via SchemaStructureAgent
        schema_nodes: list[Any] = []
        try:
            # Get existing schema nodes for context
            schema_nodes = await self._schema.list_nodes(tenant_id=tenant_id, space_id=space_id, limit=100)
            
            # Trigger SchemaStructureAgent to extract new nodes from this event
            schema_agent_spec = self._agents.get("SchemaStructureAgent")
            if schema_agent_spec:
                rag_resp = await self._rag.search(content, tenant_id=tenant_id, space_id=space_id, user_id=user_id, limit=5)
                schema_ctx = {
                    "rag_response": rag_resp,
                    "events": [ev],
                    "trace_id": trace_id,
                    "schema_engine": self._schema,
                    "schema_nodes": schema_nodes,
                }
                schema_result = await self._agents.run(
                    "SchemaStructureAgent",
                    tenant_id=tenant_id,
                    space_id=space_id,
                    user_id=user_id,
                    context=schema_ctx,
                )
                if schema_result.get("ok"):
                    # Refresh schema nodes after extraction
                    schema_nodes = await self._schema.list_nodes(tenant_id=tenant_id, space_id=space_id, limit=100)
                    logger.info("Schema extraction completed: %d nodes upserted", schema_result.get("nodes_upserted", 0))
        except Exception as e:
            logger.warning("Schema extraction failed for event %s: %s. Continuing.", ev.id, e)
            # Continue - schema extraction is best-effort

        # 5. Publish event -> Kafka / Redis Streams (JSON-safe payload)
        try:
            await self._event_bus.connect()
            await self._event_bus.publish("kirp-events", {
                "type": "ingest",
                "data": ev.to_json_payload(),
                "trace_id": trace_id,
            })
        except Exception as e:
            logger.warning("Event bus publish failed for event %s: %s. Continuing.", ev.id, e)
            # Continue - event is stored, bus publish is best-effort
        
        # 6. Trigger agents with reasoning-aware context
        # Build enriched context with multi-hop RAG and schema relationships
        reasoning_context: dict[str, Any] = {
            "original_content": content,
            "trace_id": trace_id,
            "schema_engine": self._schema,
            "schema_nodes": schema_nodes,
        }
        
        # Get RAG context with multi-hop reasoning for better context
        try:
            rag_resp = await self._rag.search(
                content,
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
                limit=10,  # More context for reasoning
                use_multihop=True,  # Enable multi-hop for better context
            )
            reasoning_context["rag_response"] = rag_resp
            
            # Build reasoning chain: extract key concepts from RAG
            if rag_resp.results:
                key_concepts = [r.text[:100] for r in rag_resp.results[:5]]
                reasoning_context["key_concepts"] = key_concepts
        except Exception as e:
            logger.warning("RAG search failed for agent context: %s", e)
            # Fallback to empty RAG response
            from src.core.rag_engine import RAGResponse, RetrievalResult
            reasoning_context["rag_response"] = RAGResponse(
                results=[],
                context_text="",
                confidence=0.0,
                query_scopes={"tenant_id": tenant_id, "space_id": space_id, "user_id": user_id},
            )
        
        # Add event history for reasoning
        try:
            recent_events = await self._events.list(
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
                limit=10,
            )
            reasoning_context["recent_events"] = recent_events
        except Exception as e:
            logger.warning("Failed to fetch recent events: %s", e)
            reasoning_context["recent_events"] = [ev]
        
        # Trigger agents in priority order (schema first, then analysis, then presentation)
        agent_priority = {
            "SchemaStructureAgent": 1,
            "PatternAnalyzerAgent": 2,
            "RiskOpportunityAgent": 2,
            "ForecasterAgent": 2,
            "TodayTomorrowPlannerAgent": 3,
            "PresentationAgent": 4,
            "SelfImprovementAgent": 5,
        }
        
        triggered_agents = self._agents.list_by_trigger("ingest")
        triggered_agents.sort(key=lambda s: agent_priority.get(s.name, 99))
        
        for spec in triggered_agents:
            try:
                # Build agent-specific context
                agent_ctx = {
                    **reasoning_context,
                    "events": [ev],
                }
                
                agent_result = await self._agents.run(
                    spec.name,
                    tenant_id=tenant_id,
                    space_id=space_id,
                    user_id=user_id,
                    context=agent_ctx,
                )
                
                # If SchemaStructureAgent created nodes, update schema_nodes list
                if spec.name == "SchemaStructureAgent" and agent_result.get("ok"):
                    created_nodes = agent_result.get("nodes_upserted", 0)
                    if created_nodes > 0:
                        # Refresh schema nodes from engine
                        try:
                            schema_nodes = await self._schema.list_nodes(tenant_id=tenant_id, space_id=space_id)
                        except Exception as e:
                            logger.warning("Failed to refresh schema nodes: %s", e)
                
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
            except Exception as e:
                logger.error("Agent %s failed for event %s: %s", spec.name, ev.id, e)
                # Continue with other agents - don't fail entire pipeline

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
