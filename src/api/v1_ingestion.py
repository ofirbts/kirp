"""
API routes for ingestion: webhooks (Slack, WhatsApp, Notion) and connector sync (Gmail, Calendar, Slack).

All events are normalized to unified format and published to Kafka only.
The Kafka processor runs the pipeline and writes to EventStore.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


async def _ingest_one(tenant_id: str, space_id: str, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Publish one unified payload to Kafka only. Processor runs pipeline and stores."""
    from src.agents.kafka_event_agent import KafkaEventAgent, EventEnvelope

    KafkaEventAgent().emit(EventEnvelope(
        type="ingest",
        payload={
            "tenant_id": tenant_id,
            "space_id": space_id,
            "user_id": user_id,
            "content": payload.get("content", ""),
            "metadata": payload.get("metadata") or {},
            "source": payload.get("source", "webhook"),
        },
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
    ))
    return {"ok": True}


# --- Webhooks ---


@router.post("/webhooks/slack")
async def webhook_slack(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """
    Slack Events API webhook. Parses event and ingests as unified events.
    Expects body.tenant_id, body.space_id, body.user_id (or defaults: default, all, system).
    """
    from src.integrations.slack import SlackIntegration
    tenant_id = body.get("tenant_id", "default")
    space_id = body.get("space_id", "all")
    user_id = body.get("user_id", "system")
    slack = SlackIntegration()
    slack.connect()
    events = slack.parse_webhook(body)
    results = []
    for ev in events:
        try:
            r = await _ingest_one(tenant_id, space_id, user_id, ev)
            results.append(r)
        except Exception as e:
            logger.warning("Slack webhook ingest failed: %s", e)
            results.append({"ok": False, "error": str(e)})
    return {"ok": True, "processed": len(results), "results": results}


def _verify_notion_signature(body_bytes: bytes, signature_header: str | None) -> bool:
    """Verify X-Notion-Signature: HMAC-SHA256(body, NOTION_WEBHOOK_SECRET)."""
    secret = os.getenv("NOTION_WEBHOOK_SECRET", "").strip()
    if not secret or not signature_header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())


@router.post("/webhooks/notion")
async def webhook_notion(request: Request) -> dict[str, Any]:
    """
    Notion webhook: subscription verification (verification_token) or event delivery (X-Notion-Signature).
    On page update events, re-fetches the page and updates our event + schema (bi-directional sync).
    """
    body_bytes = await request.body()
    try:
        body = body_bytes.decode("utf-8") if isinstance(body_bytes, bytes) else body_bytes
        import json
        data = json.loads(body) if isinstance(body, str) else body
    except Exception as e:
        logger.warning("Notion webhook invalid JSON: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    verification_token = data.get("verification_token")
    if verification_token:
        return {"verification_token": verification_token}

    sig = request.headers.get("X-Notion-Signature")
    raw = body_bytes if isinstance(body_bytes, bytes) else body_bytes.encode("utf-8")
    if not _verify_notion_signature(raw, sig):
        logger.warning("Notion webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    events = data.get("events") or data.get("event") or []
    if not isinstance(events, list):
        events = [events] if events else []
    page_ids = []
    for ev in events:
        ev_type = ev.get("type") or ev.get("event_type") or ""
        entity = ev.get("entity") or {}
        eid = entity.get("id") if isinstance(entity, dict) else None
        if not eid and ev.get("page_id"):
            eid = ev.get("page_id")
        if eid and ("page" in ev_type or "database" in ev_type or eid):
            page_ids.append(str(eid))

    page_ids = list(dict.fromkeys(page_ids))
    if not page_ids:
        return {"ok": True, "processed": 0, "message": "No page events to process"}

    tenant_id = os.getenv("NOTION_WEBHOOK_TENANT_ID", "default")
    space_id = os.getenv("NOTION_WEBHOOK_SPACE_ID", "all")
    user_id = os.getenv("NOTION_WEBHOOK_USER_ID", "system")

    from src.integrations.notion import NotionIntegration
    from src.agents.kafka_event_agent import KafkaEventAgent, EventEnvelope
    notion = NotionIntegration()
    notion.connect()

    processed = 0
    for page_id in page_ids:
        try:
            payload = await notion.fetch_page(page_id, tenant_id, space_id, user_id)
            if not payload:
                continue
            meta = payload.get("metadata") or {}
            meta["external_id"] = page_id
            KafkaEventAgent().emit(EventEnvelope(
                type="ingest",
                payload={
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "content": payload["content"],
                    "metadata": meta,
                    "source": "notion",
                },
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
            ))
            processed += 1
        except Exception as e:
            logger.exception("Notion webhook process page %s: %s", page_id, e)

    return {"ok": True, "processed": processed}


@router.post("/webhooks/whatsapp")
async def webhook_whatsapp(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """
    WhatsApp (Meta/Twilio) webhook. Parses payload and ingests as unified events.
    Expects body.tenant_id, body.space_id, body.user_id or defaults.
    """
    from src.integrations.whatsapp import WhatsAppIntegration
    tenant_id = body.get("tenant_id", "default")
    space_id = body.get("space_id", "all")
    user_id = body.get("user_id", "system")
    wa = WhatsAppIntegration()
    events = wa.parse_webhook_payload(body)
    results = []
    for ev in events:
        try:
            r = await _ingest_one(tenant_id, space_id, user_id, ev)
            results.append(r)
        except Exception as e:
            logger.warning("WhatsApp webhook ingest failed: %s", e)
            results.append({"ok": False, "error": str(e)})
    return {"ok": True, "processed": len(results), "results": results}


# --- Connector sync (pull-based) ---


@router.post("/gmail/sync")
async def gmail_sync(
    tenant_id: str = "default",
    space_id: str = "all",
    user_id: str = "system",
    max_results: int = 50,
) -> dict[str, Any]:
    """Pull Gmail messages and ingest new ones (idempotent by message id)."""
    from src.workers.connector_sync import run_gmail_sync
    result = await run_gmail_sync(tenant_id=tenant_id, space_id=space_id, user_id=user_id, max_results=max_results)
    return {"ok": True, **result}


@router.post("/calendar/sync")
async def calendar_sync(
    tenant_id: str = "default",
    space_id: str = "all",
    user_id: str = "system",
    limit: int = 100,
) -> dict[str, Any]:
    """Pull calendar events and ingest new ones (idempotent by event id)."""
    from src.workers.connector_sync import run_calendar_sync
    result = await run_calendar_sync(tenant_id=tenant_id, space_id=space_id, user_id=user_id, limit=limit)
    return {"ok": True, **result}


@router.post("/slack/sync")
async def slack_sync(
    channel_id: str,
    tenant_id: str = "default",
    space_id: str = "all",
    user_id: str = "system",
    limit: int = 50,
) -> dict[str, Any]:
    """Pull Slack channel messages and ingest new ones (idempotent by ts)."""
    from src.workers.connector_sync import run_slack_sync
    result = await run_slack_sync(
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        channel_id=channel_id,
        limit=limit,
    )
    return {"ok": True, **result}
