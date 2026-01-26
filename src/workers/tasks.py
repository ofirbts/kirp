"""
Celery tasks — ingest, WhatsApp send, agent triggers.
"""

from __future__ import annotations

import os
import logging
from typing import Any

from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="ingest_task")
def ingest_task(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Ingest content via pipeline. Called from API or event bus consumer.
    Runs async pipeline in worker; use run_async helper if needed.
    """
    import asyncio
    tenant_id = payload.get("tenant_id", "")
    space_id = payload.get("space_id", "")
    user_id = payload.get("user_id", "")
    content = payload.get("content", "")
    source = payload.get("source", "worker")

    async def _run() -> dict[str, Any]:
        from src.core.pipeline import EventPipeline
        from src.core.event_store import EventStore
        from src.core.rag_engine import RAGEngine
        from src.core.schema_engine import SchemaEngine
        from src.core.governance import GovernanceEngine
        from src.core.agent_registry import get_agent_framework_with_all_agents
        store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
        await store.connect()
        rag = RAGEngine(qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"))
        await rag.connect()
        schema = SchemaEngine(os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp"))
        await schema.connect()
        gov = GovernanceEngine(os.getenv("OPA_URL"))
        af = get_agent_framework_with_all_agents()
        pipe = EventPipeline(store, rag, schema, gov, af)
        ev_id = await pipe.run(tenant_id=tenant_id, space_id=space_id, user_id=user_id, source=source, content=content)
        return {"ok": True, "event_id": str(ev_id)}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out = loop.run_until_complete(_run())
        loop.close()
        return out
    except Exception as e:
        logger.exception("ingest_task failed: %s", e)
        return {"ok": False, "error": str(e)}


@celery_app.task(bind=True, name="whatsapp_send_task")
def whatsapp_send_task(self: Any, to: str, text: str, user_id: str = "system") -> dict[str, Any]:
    """Send WhatsApp message via integration."""
    import asyncio
    from src.integrations.whatsapp import WhatsAppIntegration
    wa = WhatsAppIntegration()
    wa.connect()

    async def _send() -> dict[str, Any]:
        return await wa.send_message(to=to, text=text, user_id=user_id)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out = loop.run_until_complete(_send())
        loop.close()
        return out
    except Exception as e:
        logger.exception("whatsapp_send_task failed: %s", e)
        return {"ok": False, "error": str(e)}


@celery_app.task(bind=True, name="daily_intelligence_task")
def daily_intelligence_task(self: Any, user_id: str, tenant_id: str = "default", space_id: str = "private") -> dict[str, Any]:
    """
    Generate and send daily intelligence via WhatsApp.
    Scheduled at 08:00 via celery beat.
    """
    import asyncio
    
    async def _run() -> dict[str, Any]:
        from src.api.whatsapp_os import daily_intelligence
        try:
            result = await daily_intelligence(user_id=user_id, tenant_id=tenant_id, space_id=space_id)
            return result
        except Exception as e:
            logger.exception("daily_intelligence_task failed: %s", e)
            return {"ok": False, "error": str(e), "message_sent": False}
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out = loop.run_until_complete(_run())
        loop.close()
        return out
    except Exception as e:
        logger.exception("daily_intelligence_task failed: %s", e)
        return {"ok": False, "error": str(e), "message_sent": False}


@celery_app.task(bind=True, name="self_improvement_task")
def self_improvement_task(self: Any, tenant_id: str = "default") -> dict[str, Any]:
    """
    Run self-improvement analysis on recent events and logs.
    Scheduled at 02:00 via celery beat.
    """
    import asyncio
    
    async def _run() -> dict[str, Any]:
        from src.core.event_store import EventStore
        from src.core.rag_engine import RAGEngine
        from src.core.agent_registry import get_agent_framework_with_all_agents
        
        try:
            store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
            await store.connect()
            rag = RAGEngine(qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"))
            await rag.connect()
            
            af = get_agent_framework_with_all_agents()
            
            # Get recent events for analysis
            events = await store.list(tenant_id=tenant_id, limit=100)
            if not events:
                return {"ok": True, "suggestions": [], "message": "No events to analyze"}
            
            # Get RAG context
            rag_resp = await rag.search("recent activity patterns", tenant_id=tenant_id, limit=10)
            
            # Build context with logs/metrics (placeholder for now)
            ctx = {
                "rag_response": rag_resp,
                "events": events,
                "logs": [],  # TODO: Collect from observability
                "metrics": {},  # TODO: Collect from metrics collector
            }
            
            result = await af.run(
                "SelfImprovementAgent",
                tenant_id=tenant_id,
                space_id="private",
                user_id="system",
                context=ctx
            )
            
            return result
        except Exception as e:
            logger.exception("self_improvement_task failed: %s", e)
            return {"ok": False, "error": str(e)}
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out = loop.run_until_complete(_run())
        loop.close()
        return out
    except Exception as e:
        logger.exception("self_improvement_task failed: %s", e)
        return {"ok": False, "error": str(e)}
