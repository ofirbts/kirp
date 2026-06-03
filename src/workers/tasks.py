"""
Celery tasks — ingest, WhatsApp send, agent triggers.
"""

from __future__ import annotations

import os
import logging
import random
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.workers.celery_app import celery_app
from src.observability.metrics import MetricsCollector

logger = logging.getLogger(__name__)
_worker_metrics = MetricsCollector("kirp_worker")


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
    metadata = payload.get("metadata")

    async def _run() -> dict[str, Any]:
        from src.core.pipeline_factory import create_connected_event_pipeline

        pipe = await create_connected_event_pipeline()
        from src.core.run_controller import get_run_controller

        meta = dict(metadata or {})
        if not meta.get("run_id"):
            rid = f"run_{uuid4().hex}"
            tr = f"tr_{uuid4().hex[:12]}"
            wf = str(meta.get("workflow_type") or "celery_ingest")
            await get_run_controller().create_run(
                workflow_type=wf,
                tenant_id=tenant_id,
                trace_id=tr,
                run_id=rid,
            )
            meta["run_id"] = rid
            meta.setdefault("trace_id", tr)
            meta.setdefault("workflow_type", wf)
        ev_id = await pipe.run(
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            source=source,
            content=content,
            metadata=meta,
        )
        _worker_metrics.inc("ingest_success_total", labels={"tenant_id": tenant_id or "unknown"})
        return {"ok": True, "event_id": str(ev_id)}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out = loop.run_until_complete(_run())
        loop.close()
        return out
    except Exception as e:
        logger.exception("ingest_task failed: %s", e)
        _worker_metrics.inc("ingest_failure_total", labels={"tenant_id": tenant_id or "unknown"})
        return {"ok": False, "error": str(e)}


def _run_async_sync(coro):
    """Run async connector sync in Celery worker."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="gmail_sync_task")
def gmail_sync_task(self: Any, tenant_id: str, space_id: str, user_id: str, max_results: int = 50) -> dict[str, Any]:
    """Scheduled pull from Gmail → ingest (idempotent)."""
    from src.workers.connector_sync import run_gmail_sync
    return _run_async_sync(run_gmail_sync(tenant_id=tenant_id, space_id=space_id, user_id=user_id, max_results=max_results))


@celery_app.task(bind=True, name="calendar_sync_task")
def calendar_sync_task(self: Any, tenant_id: str, space_id: str, user_id: str, limit: int = 100) -> dict[str, Any]:
    """Scheduled pull from Calendar → ingest (idempotent)."""
    from src.workers.connector_sync import run_calendar_sync
    return _run_async_sync(run_calendar_sync(tenant_id=tenant_id, space_id=space_id, user_id=user_id, limit=limit))


@celery_app.task(bind=True, name="slack_sync_task")
def slack_sync_task(
    self: Any,
    tenant_id: str,
    space_id: str,
    user_id: str,
    channel_id: str,
    limit: int = 50,
) -> dict[str, Any]:
    """Scheduled pull from Slack channel → ingest (idempotent)."""
    from src.workers.connector_sync import run_slack_sync
    return _run_async_sync(
        run_slack_sync(
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            channel_id=channel_id,
            limit=limit,
        )
    )


@celery_app.task(bind=True, name="notion_sync_task")
def notion_sync_task(self: Any, tenant_id: str, space_id: str, user_id: str) -> dict[str, Any]:
    """Scheduled pull from Notion DB → ingest (idempotent)."""
    from src.workers.notion_sync import run_notion_sync
    return _run_async_sync(run_notion_sync(tenant_id=tenant_id, space_id=space_id, user_id=user_id))


@celery_app.task(bind=True, name="reminder_run_task")
def reminder_run_task(
    self: Any,
    tenant_id: str = "default",
    space_id: str = "all",
    user_id: str = "system",
    horizon_days: int = 7,
) -> dict[str, Any]:
    """Run ReminderAgent: detect upcoming obligations and send reminders (WhatsApp, Email, Notification)."""
    from src.core.agent_registry import get_agent_framework_with_all_agents

    async def _run() -> dict[str, Any]:
        af = get_agent_framework_with_all_agents()
        return await af.run(
            "ReminderAgent",
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            context={"horizon_days": horizon_days},
        )

    return _run_async_sync(_run())


@celery_app.task(bind=True, name="refresh_missing_embeddings_task")
def refresh_missing_embeddings_task(
    self: Any,
    tenant_id: str,
    space_id: str | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """
    Refresh embeddings in Qdrant for events that have no embedding yet.

    This is part of the embedding refresh pipeline (vector lifecycle).
    """
    import asyncio

    async def _run() -> dict[str, Any]:
        from datetime import datetime, timedelta, timezone
        from src.core.event_store import EventStore
        from src.core.rag_engine import RAGEngine
        from src.core.config import get_settings
        from src.core.embedding_provider import embedding_model_name, embedding_provider_name

        try:
            settings = get_settings()
            store = EventStore(settings.mongo_uri)
            await store.connect()

            rag = RAGEngine(
                qdrant_url=settings.qdrant_url,
                collection=settings.qdrant_collection,
                qdrant_api_key=settings.qdrant_api_key,
                embedding_provider=embedding_provider_name(),
                embedding_model=embedding_model_name(),
            )
            await rag.connect()

            # Fetch events without embedding
            window_hours = settings.embedding_refresh_window_hours
            effective_limit = limit or settings.embedding_refresh_limit_per_run
            since = datetime.now(timezone.utc) - timedelta(hours=window_hours)

            q: dict[str, Any] = {"tenant_id": tenant_id}
            if space_id:
                q["space_id"] = space_id
            q["embedding"] = []
            q["timestamp"] = {"$gte": since}

            db = store._db  # type: ignore[attr-defined]
            cursor = db.events.find(q).sort("timestamp", -1).limit(effective_limit)
            docs = await cursor.to_list(length=effective_limit)

            updated = 0
            points: list[dict[str, Any]] = []
            for doc in docs:
                content = doc.get("content", "")
                if not content:
                    continue
                try:
                    emb = await rag.embed(content)
                except Exception as e:
                    logger.warning("Embedding refresh failed for %s: %s", doc.get("_id"), e)
                    continue
                doc["embedding"] = emb
                points.append(
                    {
                        "id": doc["_id"],
                        "embedding": emb,
                        "content": content,
                        "source": doc.get("source", "unknown"),
                        "user_id": doc.get("user_id", ""),
                    }
                )
                updated += 1

            if points:
                await rag.upsert(points, tenant_id=tenant_id, space_id=space_id or "default")
                # Persist updated embeddings back to Mongo
                for doc in docs:
                    await db.events.update_one({"_id": doc["_id"]}, {"$set": {"embedding": doc.get("embedding", [])}})

            logger.info(
                "Refreshed embeddings for %d events (tenant=%s, space=%s)",
                updated,
                tenant_id,
                space_id,
            )

            return {"ok": True, "tenant_id": tenant_id, "space_id": space_id, "updated": updated}
        except Exception as e:
            logger.exception("refresh_missing_embeddings_task failed: %s", e)
            return {"ok": False, "error": str(e)}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out = loop.run_until_complete(_run())
        loop.close()
        return out
    except Exception as e:
        logger.exception("refresh_missing_embeddings_task failed: %s", e)
        return {"ok": False, "error": str(e)}


@celery_app.task(bind=True, name="whatsapp_send_task")
def whatsapp_send_task(
    self: Any,
    to: str,
    text: str,
    user_id: str = "system",
    tenant_id: str = "default",
    space_id: str = "all",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Queue WhatsApp send via pending executions (governed path)."""
    import asyncio
    from src.core.whatsapp_outbound import enqueue_whatsapp_outbound

    async def _send() -> dict[str, Any]:
        return await enqueue_whatsapp_outbound(
            tenant_id=tenant_id,
            user_id=user_id,
            space_id=space_id,
            to=to,
            text=text,
            idempotency_key=idempotency_key,
            source="celery_whatsapp_send_task",
        )

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
        from src.core.embedding_provider import embedding_model_name, embedding_provider_name
        
        try:
            store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
            await store.connect()
            rag = RAGEngine(
                qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
                qdrant_api_key=os.getenv("QDRANT_API_KEY"),
                embedding_provider=embedding_provider_name(),
                embedding_model=embedding_model_name(),
            )
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


@celery_app.task(bind=True, name="demo_data_generator_task")
def demo_data_generator_task(
    self: Any,
    tenant_id: str = "demo-tenant",
    space_id: str = "default-space",
) -> dict[str, Any]:
    """
    Generate demo data periodically:
    - 100+ synthetic events in the EventStore (MongoDB) with tenant_id support.
    - 10+ synthetic "agent" events representing agents in the system.

    This task is idempotent in the sense that data is always additive and
    scoped by tenant/space, suitable for demo dashboards.
    """
    import asyncio

    async def _run() -> dict[str, Any]:
        from src.core.event_store import EventStore, Event, Sensitivity

        try:
            store = EventStore(
                os.getenv(
                    "MONGO_URI",
                    "mongodb://root:example@localhost:27017/kirp?authSource=admin",
                )
            )
            await store.connect()

            now = datetime.now(timezone.utc)

            # Generate 100+ generic activity events.
            base_events: list[Event] = []
            for i in range(120):
                ev = Event(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    space_id=space_id,
                    user_id="demo-user",
                    source="demo-generator",
                    content=f"Demo activity event #{i+1}",
                    metadata={
                        "kind": random.choice(
                            ["ingest", "decision", "alert", "task_update"]
                        ),
                        "demo": True,
                        "seq": i + 1,
                    },
                    embedding=[],
                    timestamp=now,
                    sensitivity=Sensitivity.PRIVATE,
                    event_type="demo_activity",
                    trace_id=None,
                )
                base_events.append(ev)

            # Generate 10+ agent-related events to simulate active agents.
            agent_events: list[Event] = []
            for i in range(15):
                agent_id = f"agent-{i+1}"
                ev = Event(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    space_id=space_id,
                    user_id="demo-agent-runner",
                    source="demo-generator",
                    content=f"Demo agent {agent_id} executed successfully.",
                    metadata={
                        "agent_id": agent_id,
                        "status": random.choice(["success", "success", "warning"]),
                        "latency_ms": random.randint(50, 800),
                        "demo": True,
                    },
                    embedding=[],
                    timestamp=now,
                    sensitivity=Sensitivity.PRIVATE,
                    event_type="demo_agent_run",
                    trace_id=None,
                )
                agent_events.append(ev)

            # Ingest all events.
            created_ids: list[str] = []
            for ev in base_events + agent_events:
                ev_id = await store.ingest(ev)
                created_ids.append(str(ev_id))

            logger.info(
                "Demo data generator created %d events (tenant=%s, space=%s)",
                len(created_ids),
                tenant_id,
                space_id,
            )

            return {
                "ok": True,
                "tenant_id": tenant_id,
                "space_id": space_id,
                "events_created": len(created_ids),
            }
        except Exception as e:
            logger.exception("demo_data_generator_task failed: %s", e)
            return {"ok": False, "error": str(e)}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out = loop.run_until_complete(_run())
        loop.close()
        return out
    except Exception as e:
        logger.exception("demo_data_generator_task failed: %s", e)
        return {"ok": False, "error": str(e)}


@celery_app.task(bind=True, name="agent_run_task")
def agent_run_task(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Process one agent run from Redis queue (agent_run_queue).
    Payload: run_id, agent_name, tenant_id, space_id, user_id, trigger, trigger_ref, input_context.
    """
    import asyncio
    import json
    from uuid import UUID
    from src.core.agent_engine import get_agent_engine, AgentRunState
    from src.core.agent_registry import get_agent_framework_with_all_agents

    async def _run() -> dict[str, Any]:
        engine = get_agent_engine()
        af = get_agent_framework_with_all_agents()
        run_id = UUID(payload["run_id"])
        agent_name = payload.get("agent_name", "")
        tenant_id = payload.get("tenant_id", "")
        space_id = payload.get("space_id", "private")
        user_id = payload.get("user_id", "system")
        context = payload.get("input_context", {})
        spec = af.get(agent_name)
        if not spec or not spec.handler:
            await engine.set_run_state(run_id, AgentRunState.FAILED, error=f"Agent not found or no handler: {agent_name}")
            return {"ok": False, "error": f"Agent not found: {agent_name}"}
        result = await engine.execute_run(run_id, agent_name, tenant_id, space_id, user_id, context, spec.handler)
        return {"ok": True, "run_id": str(run_id), "result": result}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        out = loop.run_until_complete(_run())
        loop.close()
        return out
    except Exception as e:
        logger.exception("agent_run_task failed: %s", e)
        run_id = payload.get("run_id")
        if run_id:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                from src.core.agent_engine import get_agent_engine, AgentRunState
                from uuid import UUID
                engine = get_agent_engine()
                loop.run_until_complete(engine.set_run_state(UUID(run_id), AgentRunState.FAILED, error=str(e)))
                loop.close()
            except Exception:
                pass
        return {"ok": False, "error": str(e)}


@celery_app.task(name="drain_agent_queue_task")
def drain_agent_queue_task() -> dict[str, Any]:
    """Pop one agent run from Redis agent_run_queue and dispatch agent_run_task."""
    from src.core.integrations import get_redis_client
    import json

    r = get_redis_client()
    if not r:
        return {"ok": False, "error": "Redis not available"}
    raw = r.brpop("agent_run_queue", timeout=1)
    if not raw:
        return {"ok": True, "processed": 0}
    _, payload_str = raw
    try:
        payload = json.loads(payload_str)
    except Exception as e:
        logger.warning("drain_agent_queue invalid payload: %s", e)
        return {"ok": False, "error": str(e)}
    agent_run_task.delay(payload)
    return {"ok": True, "processed": 1, "run_id": payload.get("run_id")}


@celery_app.task(bind=True, name="reconcile_partial_runs_task")
def reconcile_partial_runs_task(self: Any, max_runs: int = 50) -> dict[str, Any]:
    """
    Reconcile runs in aggregate `partial` state (replay failed history / Qdrant / schema).
    Scheduled every 15 minutes via Celery beat.
    """
    async def _run() -> dict[str, Any]:
        from src.workers.reconciliation_worker import ReconciliationWorker

        w = await ReconciliationWorker.create()
        return await w.reconcile_partial_runs(max_runs=max_runs)

    return _run_async_sync(_run())


@celery_app.task(bind=True, name="run_m3_stages_task")
def run_m3_stages_task(
    self: Any,
    event_type: str,
    tenant_id: str,
    space_id: str,
    user_id: str,
    metadata: dict[str, Any],
    content: str = "",
) -> dict[str, Any]:
    """Asynchronous background execution of M3 reflection classifier and gap analysis stages."""
    async def _run() -> dict[str, Any]:
        from src.modules.m3.stages import run_m3_stages
        await run_m3_stages(
            event_type=event_type,
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            metadata=metadata,
            content=content,
        )
        return {"ok": True}

    return _run_async_sync(_run())
