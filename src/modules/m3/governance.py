from __future__ import annotations

import logging
import os
from typing import Any

from src.core.structured_logging import log_json

logger = logging.getLogger(__name__)


async def enqueue_m3_whatsapp_escalation(
    tenant_id: str,
    space_id: str,
    user_id: str,
    event_type: str,
    reason: str,
    identity_entropy_score: float | None,
    resource_type: str | None = None,
    *,
    trace_id: str | None = None,
) -> dict[str, Any]:
    to_phone = _resolve_m3_escalation_phone(tenant_id, user_id)
    if not to_phone:
        logger.info(
            "M3 escalation (no phone): tenant=%s user=%s event_type=%s score=%s reason=%s",
            tenant_id,
            user_id,
            event_type,
            identity_entropy_score,
            reason,
        )
        return {"ok": False, "reason": "no_phone_configured"}

    text = _m3_escalation_message(event_type, reason, identity_entropy_score, resource_type)
    idem = (trace_id or "").strip() or f"m3:{tenant_id}:{user_id}:{event_type}"
    from src.core.whatsapp_outbound import enqueue_whatsapp_outbound

    result = await enqueue_whatsapp_outbound(
        tenant_id=tenant_id,
        user_id=user_id,
        space_id=space_id,
        to=to_phone,
        text=text,
        idempotency_key=idem,
        source="m3_escalation",
        extra_payload={
            "m3_escalation": True,
            "event_type": event_type,
            "reason": reason,
            "identity_entropy_score": identity_entropy_score,
            "resource_type": resource_type,
            "trace_id": trace_id,
        },
    )
    log_json(
        logger,
        "info",
        "m3_whatsapp_escalation_queued",
        tenant_id=tenant_id,
        user_id=user_id,
        pending_id=result.get("pending_id"),
        event_type=event_type,
        duplicate=result.get("duplicate"),
    )
    return result


async def send_m3_whatsapp_escalation(
    tenant_id: str,
    space_id: str,
    user_id: str,
    event_type: str,
    reason: str,
    identity_entropy_score: float | None,
    resource_type: str | None = None,
) -> dict[str, Any]:
    return await enqueue_m3_whatsapp_escalation(
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        event_type=event_type,
        reason=reason,
        identity_entropy_score=identity_entropy_score,
        resource_type=resource_type,
    )


def _resolve_m3_escalation_phone(tenant_id: str, user_id: str) -> str | None:
    key = f"M3_ESCALATION_PHONE_{tenant_id}_{user_id}".upper().replace("-", "_")
    phone = os.getenv(key, "").strip()
    if phone:
        return phone
    return os.getenv("M3_ESCALATION_PHONE", "").strip() or None


def _m3_escalation_message(
    event_type: str,
    reason: str,
    identity_entropy_score: float | None,
    resource_type: str | None,
) -> str:
    if "monthly_evolution" in (event_type or "") or resource_type == "m3.monthly_evolution":
        return (
            "M3 Identity: Monthly evolution suggests new goals or direction. "
            "Approve? Reply YES/NO or EDIT."
        )
    if identity_entropy_score is not None and identity_entropy_score >= 0.6:
        return (
            f"M3 Identity: High-impact change (score {identity_entropy_score:.2f}). "
            "Approve? Reply YES/NO."
        )
    return f"M3 Identity: Approval required. {reason}. Reply YES/NO."
