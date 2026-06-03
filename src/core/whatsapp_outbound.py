from __future__ import annotations

import os
from typing import Any

from src.core.pending_executions import PendingExecutionsStore
from src.core.structured_logging import log_json
from src.observability.metrics import MetricsCollector
import logging

logger = logging.getLogger(__name__)
_outbound_metrics = MetricsCollector("kirp_whatsapp_outbound")
_pending_metrics = MetricsCollector("kirp_pending_executions")


def _pending_store() -> PendingExecutionsStore:
    uri = os.getenv(
        "MONGO_URI",
        "mongodb://root:example@localhost:27017/kirp?authSource=admin",
    )
    return PendingExecutionsStore(uri)


async def enqueue_whatsapp_outbound(
    tenant_id: str,
    user_id: str,
    space_id: str,
    to: str,
    text: str,
    *,
    idempotency_key: str | None = None,
    source: str = "outbound",
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not tenant_id or not str(tenant_id).strip():
        return {"ok": False, "error": "tenant_id required"}
    if not to or not text:
        return {"ok": False, "error": "to and text required"}

    payload: dict[str, Any] = {"to": to, "text": text, "source": source}
    if extra_payload:
        payload.update(extra_payload)
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key

    store = _pending_store()
    await store.connect()
    pending_id, duplicate = await store.add_or_get_pending(
        tenant_id=tenant_id,
        user_id=user_id,
        space_id=space_id,
        command_type="send_whatsapp",
        payload=payload,
        idempotency_key=idempotency_key,
    )
    depth = await store.count_pending(tenant_id)
    _pending_metrics.gauge("queue_depth", float(depth), labels={"tenant_id": tenant_id})
    log_json(
        logger,
        "info",
        "whatsapp_outbound_queued",
        tenant_id=tenant_id,
        user_id=user_id,
        pending_id=pending_id,
        duplicate=duplicate,
        source=source,
    )
    _outbound_metrics.inc("queued_total", labels={"tenant_id": tenant_id, "source": source})
    return {
        "ok": True,
        "pending_id": pending_id,
        "queued": True,
        "duplicate": duplicate,
    }


async def dispatch_pending_whatsapp(
    pending_id: str,
    tenant_id: str,
    user_id: str,
    space_id: str,
) -> dict[str, Any]:
    from src.core.execution_engine import execute_command

    store = _pending_store()
    await store.connect()
    doc = await store.get(pending_id, tenant_id)
    if not doc:
        return {"ok": False, "error": "pending_not_found"}
    if doc.get("status") != "pending":
        return {"ok": False, "error": f"status_{doc.get('status')}"}
    result = await execute_command(
        command_type=doc["command_type"],
        payload=doc["payload"],
        tenant_id=doc["tenant_id"],
        user_id=doc["user_id"],
        space_id=doc["space_id"],
        governance_approved=True,
    )
    await store.set_status(pending_id, "executed", executed_result=result)
    return result


async def enqueue_and_dispatch_whatsapp(
    tenant_id: str,
    user_id: str,
    space_id: str,
    to: str,
    text: str,
    *,
    idempotency_key: str | None = None,
    source: str = "outbound",
    extra_payload: dict[str, Any] | None = None,
    governance_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from src.core.config import get_settings
    from src.core.governance import GovernanceEngine
    from src.core.governance_bundles import GovernanceEnforcement

    enforcement = GovernanceEnforcement(GovernanceEngine(get_settings().opa_url))
    ctx = dict(governance_context or {})
    ctx.setdefault("resource_type", "whatsapp_outbound")
    ctx.setdefault("source", source)
    check = await enforcement.enforce(
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        action="execute",
        resource="send_whatsapp",
        context=ctx,
    )
    if not check.allowed:
        return {
            "ok": False,
            "governance_denied": True,
            "error": check.reason or "governance_denied",
        }

    queued = await enqueue_whatsapp_outbound(
        tenant_id=tenant_id,
        user_id=user_id,
        space_id=space_id,
        to=to,
        text=text,
        idempotency_key=idempotency_key,
        source=source,
        extra_payload=extra_payload,
    )
    if not queued.get("ok"):
        return queued
    if check.requires_approval:
        return {**queued, "dispatched": False, "requires_approval": True}
    if queued.get("duplicate"):
        return {**queued, "dispatched": False}

    pending_id = str(queued.get("pending_id") or "")
    if not pending_id:
        return {**queued, "dispatched": False, "error": "missing_pending_id"}

    dispatched = await dispatch_pending_whatsapp(
        pending_id, tenant_id, user_id, space_id
    )
    return {
        **queued,
        "dispatched": bool(dispatched.get("ok")),
        "dispatch_result": dispatched,
    }
