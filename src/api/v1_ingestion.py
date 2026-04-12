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
from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, Request

from src.auth.tenant_context import get_tenant_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


async def _ingest_one(tenant_id: str, space_id: str, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Publish one unified payload to Kafka only. Processor runs pipeline and stores."""
    from src.agents.kafka_event_agent import KafkaEventAgent, EventEnvelope

    run_id = payload.get("run_id") or f"run_{uuid4().hex}"
    trace_id = payload.get("trace_id") or f"tr_{uuid4().hex[:12]}"
    workflow_type = payload.get("workflow_type") or "ingest_event"
    idempotency_key = payload.get("idempotency_key")
    KafkaEventAgent().emit(EventEnvelope(
        type="ingest",
        payload={
            "tenant_id": tenant_id,
            "space_id": space_id,
            "user_id": user_id,
            "content": payload.get("content", ""),
            "trace_id": trace_id,
            "run_id": run_id,
            "workflow_type": workflow_type,
            "idempotency_key": idempotency_key,
            "metadata": {
                **(payload.get("metadata") or {}),
                "trace_id": trace_id,
                "run_id": run_id,
                "workflow_type": workflow_type,
            },
            "source": payload.get("source", "webhook"),
        },
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        run_id=run_id,
        workflow_type=workflow_type,
        trace_id=trace_id,
        idempotency_key=idempotency_key,
    ))
    return {"ok": True, "run_id": run_id, "trace_id": trace_id}


# --- Webhooks ---


@router.post("/webhooks/slack")
async def webhook_slack(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """
    Slack Events API webhook. Parses event and ingests as unified events.
    Tenant routing: env SLACK_WEBHOOK_TENANT_ID / SLACK_WEBHOOK_SPACE_ID / SLACK_WEBHOOK_USER_ID only
    (do not trust tenant fields in the JSON body — anyone can POST to a public URL).
    """
    from src.integrations.slack import SlackIntegration
    tenant_id = os.getenv("SLACK_WEBHOOK_TENANT_ID", "default").strip() or "default"
    space_id = os.getenv("SLACK_WEBHOOK_SPACE_ID", "all").strip() or "all"
    user_id = os.getenv("SLACK_WEBHOOK_USER_ID", "system").strip() or "system"
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
                    "trace_id": f"tr_{uuid4().hex[:12]}",
                    "run_id": f"run_{uuid4().hex}",
                    "workflow_type": "ingest_event",
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


async def _parse_webhook_body(request: Request) -> dict[str, Any]:
    """Parse WhatsApp webhook body: Twilio sends form-urlencoded, Meta may send JSON."""
    ct = (request.headers.get("content-type") or "").lower()
    if "application/x-www-form-urlencoded" in ct or "multipart/form-data" in ct:
        form = await request.form()
        return dict(form)  # Twilio sends one value per key
    try:
        return await request.json()
    except Exception:
        return {}


@router.post("/webhooks/whatsapp")
async def webhook_whatsapp(request: Request) -> dict[str, Any]:
    """
    WhatsApp (Meta/Twilio) webhook. Parses payload and ingests as unified events.
    Twilio sends application/x-www-form-urlencoded; we accept that and JSON.
    Tenant routing: env WHATSAPP_WEBHOOK_TENANT_ID / _SPACE_ID / _USER_ID only (not from body).

    For Twilio, validates X-Twilio-Signature when TWILIO_AUTH_TOKEN is set.
    """
    from src.integrations.whatsapp import WhatsAppIntegration

    body = await _parse_webhook_body(request)

    # Optional Twilio signature validation (best-effort; skips if misconfigured).
    try:
        import os
        from twilio.request_validator import RequestValidator  # type: ignore[import]

        if os.getenv("WHATSAPP_PROVIDER", "").lower() == "twilio":
            auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
            signature = request.headers.get("X-Twilio-Signature", "")
            if auth_token and signature:
                validator = RequestValidator(auth_token)
                # Behind ngrok/proxy: Twilio signed the public URL; use X-Forwarded-* to reconstruct it.
                forwarded_host = request.headers.get("X-Forwarded-Host")
                forwarded_proto = request.headers.get("X-Forwarded-Proto", "https")
                if forwarded_host:
                    path = request.scope.get("path", "/")
                    query = request.scope.get("query_string", b"").decode()
                    url = f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}{path}"
                    if query:
                        url += "?" + query
                else:
                    url = str(request.url)
                if not validator.validate(url, body, signature):
                    logger.warning("WhatsApp webhook Twilio signature validation failed (url=%s)", url[:80])
                    raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        logger.warning("WhatsApp webhook signature validation skipped: %s", e)

    tenant_id = os.getenv("WHATSAPP_WEBHOOK_TENANT_ID", "default").strip() or "default"
    space_id = os.getenv("WHATSAPP_WEBHOOK_SPACE_ID", "all").strip() or "all"
    user_id = os.getenv("WHATSAPP_WEBHOOK_USER_ID", "system").strip() or "system"

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
    # Notify user in the bell so they see a new WhatsApp message
    if events and user_id and user_id != "system":
        try:
            from src.core.notifications import notify_user
            first_content = (events[0].get("content") or "")[:120].strip() or "New message"
            await notify_user(
                tenant_id=tenant_id,
                user_id=user_id,
                type="whatsapp_message",
                title="WhatsApp",
                body=first_content,
                space_id=space_id,
                meta={"source": "whatsapp", "count": len(events)},
            )
        except Exception as e:
            logger.warning("WhatsApp notification failed: %s", e)
    return {"ok": True, "processed": len(results), "results": results}


# --- Connector sync (pull-based) ---


@router.post("/gmail/sync")
async def gmail_sync(
    request: Request,
    max_results: int = 50,
) -> dict[str, Any]:
    """Pull Gmail messages and ingest new ones (idempotent by message id). Scoped to JWT tenant."""
    ctx = get_tenant_context(request)
    from src.workers.connector_sync import run_gmail_sync
    result = await run_gmail_sync(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "all",
        user_id=ctx.user_id,
        max_results=max_results,
    )
    return {"ok": True, **result}


@router.post("/calendar/sync")
async def calendar_sync(
    request: Request,
    limit: int = 100,
) -> dict[str, Any]:
    """Pull calendar events and ingest new ones (idempotent by event id). Scoped to JWT tenant."""
    ctx = get_tenant_context(request)
    from src.workers.connector_sync import run_calendar_sync
    result = await run_calendar_sync(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "all",
        user_id=ctx.user_id,
        limit=limit,
    )
    return {"ok": True, **result}


@router.post("/slack/sync")
async def slack_sync(
    request: Request,
    channel_id: str,
    limit: int = 50,
) -> dict[str, Any]:
    """Pull Slack channel messages and ingest new ones (idempotent by ts). Scoped to JWT tenant."""
    ctx = get_tenant_context(request)
    from src.workers.connector_sync import run_slack_sync
    result = await run_slack_sync(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "all",
        user_id=ctx.user_id,
        channel_id=channel_id,
        limit=limit,
    )
    return {"ok": True, **result}
