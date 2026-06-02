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
