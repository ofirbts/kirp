"""
Notion Sync Worker — Pull pages from Notion DB and ingest as events (idempotent).

Uses NOTION_TASKS_DB_ID / NOTION_DATABASE_ID. Each page becomes one event with
source=notion and metadata.external_id=notion_page_id. Skips pages already ingested.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


async def run_notion_sync(
    tenant_id: str,
    space_id: str,
    user_id: str,
    *,
    event_store: Any = None,
    pipeline: Any = None,
    notion: Any = None,
) -> dict[str, Any]:
    """
    Pull Notion database pages and ingest new ones (idempotent by external_id + source).
    Returns { "ingested": int, "skipped": int, "errors": list }.
    """
    if event_store is None:
        from src.core.event_store import EventStore
        import os
        event_store = EventStore(
            os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin")
        )
        await event_store.connect()
    if pipeline is None:
        from src.main import get_pipeline
        pipeline = await get_pipeline()
    if notion is None:
        from src.integrations.notion import NotionIntegration
        notion = NotionIntegration()
        notion.connect()

    payloads = await notion.ingest_database(tenant_id=tenant_id, space_id=space_id, user_id=user_id)
    ingested = 0
    skipped = 0
    errors: list[str] = []

    for p in payloads:
        meta = p.get("metadata") or {}
        external_id = meta.get("external_id") or meta.get("page_id")
        if not external_id:
            errors.append("missing external_id in payload")
            continue
        existing = await event_store.find_by_external_id(
            tenant_id=tenant_id,
            source="notion",
            external_id=external_id,
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
                    workflow_type="notion_sync",
                    tenant_id=p["tenant_id"],
                    trace_id=tr,
                    run_id=rid,
                )
                meta_out["run_id"] = rid
                meta_out.setdefault("trace_id", tr)
                meta_out.setdefault("workflow_type", "notion_sync")
            await pipeline.run(
                tenant_id=p["tenant_id"],
                space_id=p["space_id"],
                user_id=p["user_id"],
                source=p.get("source", "notion"),
                content=p.get("content", ""),
                metadata=meta_out,
            )
            ingested += 1
        except Exception as e:
            logger.exception("Notion ingest failed for page %s: %s", external_id, e)
            errors.append(f"{external_id}: {e}")

    return {"ingested": ingested, "skipped": skipped, "errors": errors}
