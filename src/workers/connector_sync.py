"""
Connector sync workers — Pull from Gmail, Calendar, Slack and ingest (idempotent by external_id).

Same pattern as notion_sync: fetch payloads → for each check find_by_external_id → if new, pipeline.run().
Unified event format: tenant_id, space_id, user_id, source, content, metadata.external_id.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


async def _ingest_payloads_idempotent(
    payloads: list[dict[str, Any]],
    pipeline: Any,
    event_store: Any,
) -> tuple[int, int, list[str]]:
    """Ingest payloads; skip when metadata.external_id + source already exist. Returns (ingested, skipped, errors)."""
    ingested = 0
    skipped = 0
    errors: list[str] = []
    for p in payloads:
        meta = p.get("metadata") or {}
        external_id = meta.get("external_id") or meta.get("id")
        source = p.get("source", "")
        if not external_id:
            errors.append("missing external_id")
            continue
        existing = await event_store.find_by_external_id(
            tenant_id=p["tenant_id"],
            source=source,
            external_id=str(external_id),
        )
        if existing:
            skipped += 1
            continue
        try:
            from src.core.run_controller import get_run_controller

            meta_out = dict(meta)
            if not meta_out.get("run_id"):
                rid = f"run_{uuid4().hex}"
                tr = f"tr_{uuid4().hex[:12]}"
                await get_run_controller().create_run(
                    workflow_type="connector_sync",
                    tenant_id=p["tenant_id"],
                    trace_id=tr,
                    run_id=rid,
                )
                meta_out["run_id"] = rid
                meta_out.setdefault("trace_id", tr)
                meta_out.setdefault("workflow_type", "connector_sync")
            await pipeline.run(
                tenant_id=p["tenant_id"],
                space_id=p["space_id"],
                user_id=p["user_id"],
                source=source,
                content=p.get("content", ""),
                metadata=meta_out,
            )
            ingested += 1
        except Exception as e:
            logger.exception("Ingest failed for %s: %s", external_id, e)
            errors.append(f"{external_id}: {e}")
    return ingested, skipped, errors


def _get_store_and_pipeline():
    """Build store and pipeline (used when not injected). Avoids importing main."""
    import os
    from src.core.event_store import EventStore
    from src.core.pipeline import EventPipeline
    from src.core.rag_engine import RAGEngine
    from src.core.schema_engine import SchemaEngine
    from src.core.governance import GovernanceEngine
    from src.core.agent_registry import get_agent_framework_with_all_agents
    return EventStore, EventPipeline, RAGEngine, SchemaEngine, GovernanceEngine, get_agent_framework_with_all_agents


async def run_gmail_sync(
    tenant_id: str,
    space_id: str,
    user_id: str,
    *,
    event_store: Any = None,
    pipeline: Any = None,
    gmail: Any = None,
    max_results: int = 50,
    page_token: str | None = None,
) -> dict[str, Any]:
    """Pull Gmail messages and ingest new ones (idempotent). Returns {ingested, skipped, errors, next_page_token}."""
    import os
    if event_store is None or pipeline is None:
        EStore, EPipeline, RAG, Schema, Gov, get_af = _get_store_and_pipeline()
        store = EStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
        await store.connect()
        rag = RAG(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        await rag.connect()
        schema = Schema(os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp"))
        await schema.connect()
        event_store = store
        pipeline = EPipeline(store, rag, schema, Gov(os.getenv("OPA_URL")), get_af())
    if gmail is None:
        from src.integrations.gmail import GmailIntegration
        gmail = GmailIntegration()
        gmail.connect()
    payloads, next_page_token = await gmail.list_messages(
        tenant_id=tenant_id, space_id=space_id, user_id=user_id, max_results=max_results, page_token=page_token
    )
    ingested, skipped, errors = await _ingest_payloads_idempotent(payloads, pipeline, event_store)
    result = {"ingested": ingested, "skipped": skipped, "errors": errors}
    if next_page_token is not None:
        result["page_token"] = next_page_token
    return result


async def run_calendar_sync(
    tenant_id: str,
    space_id: str,
    user_id: str,
    *,
    event_store: Any = None,
    pipeline: Any = None,
    calendar: Any = None,
    limit: int = 100,
    sync_token: str | None = None,
) -> dict[str, Any]:
    """Pull calendar events (7d back + future) and ingest (idempotent). Returns {ingested, skipped, errors, sync_token}."""
    import os
    if event_store is None or pipeline is None:
        EStore, EPipeline, RAG, Schema, Gov, get_af = _get_store_and_pipeline()
        store = EStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
        await store.connect()
        rag = RAG(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        await rag.connect()
        schema = Schema(os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp"))
        await schema.connect()
        event_store = store
        pipeline = EPipeline(store, rag, schema, Gov(os.getenv("OPA_URL")), get_af())
    if calendar is None:
        from src.integrations.calendar import CalendarIntegration
        calendar = CalendarIntegration()
        calendar.connect()
    payloads, next_sync_token = await calendar.list_events(
        tenant_id=tenant_id, space_id=space_id, user_id=user_id, limit=limit, sync_token=sync_token
    )
    ingested, skipped, errors = await _ingest_payloads_idempotent(payloads, pipeline, event_store)
    result = {"ingested": ingested, "skipped": skipped, "errors": errors}
    if next_sync_token:
        result["sync_token"] = next_sync_token
    return result


async def run_slack_sync(
    tenant_id: str,
    space_id: str,
    user_id: str,
    channel_id: str,
    *,
    event_store: Any = None,
    pipeline: Any = None,
    slack: Any = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Pull Slack channel messages and ingest new ones (idempotent). Returns {ingested, skipped, errors}."""
    import os
    if event_store is None or pipeline is None:
        EStore, EPipeline, RAG, Schema, Gov, get_af = _get_store_and_pipeline()
        store = EStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
        await store.connect()
        rag = RAG(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        await rag.connect()
        schema = Schema(os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp"))
        await schema.connect()
        event_store = store
        pipeline = EPipeline(store, rag, schema, Gov(os.getenv("OPA_URL")), get_af())
    if slack is None:
        from src.integrations.slack import SlackIntegration
        slack = SlackIntegration()
        slack.connect()
    payloads, _ = await slack.fetch_recent_messages(
        tenant_id=tenant_id, space_id=space_id, user_id=user_id, channel_id=channel_id, limit=limit
    )
    ingested, skipped, errors = await _ingest_payloads_idempotent(payloads, pipeline, event_store)
    return {"ingested": ingested, "skipped": skipped, "errors": errors}
