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
        from src.core.agent_framework import AgentFramework
        from src.agents import (
            pattern_analyzer_spec,
            planner_spec,
            forecaster_spec,
            risk_opportunity_spec,
            schema_structure_spec,
            presentation_spec,
            self_improvement_spec,
        )
        store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
        await store.connect()
        rag = RAGEngine(qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"))
        await rag.connect()
        schema = SchemaEngine(os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp:kirp@localhost:5432/kirp"))
        await schema.connect()
        gov = GovernanceEngine(os.getenv("OPA_URL"))
        af = AgentFramework()
        for spec in (
            pattern_analyzer_spec,
            planner_spec,
            forecaster_spec,
            risk_opportunity_spec,
            schema_structure_spec,
            presentation_spec,
            self_improvement_spec,
        ):
            af.register(spec)
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
