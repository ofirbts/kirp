"""
M3 IdentityOS — Human governance: WhatsApp escalation when requires_approval (score >= 0.6).

Per spec 8: identity_entropy_score ≥ 0.6 or resource_type m3.monthly_evolution →
WhatsApp prompt to tenant/user for approval. Per-tenant isolation.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def send_m3_whatsapp_escalation(
    tenant_id: str,
    space_id: str,
    user_id: str,
    event_type: str,
    reason: str,
    identity_entropy_score: float | None,
    resource_type: str | None = None,
) -> dict[str, Any]:
    """
    Send WhatsApp prompt for M3 human approval. Uses tenant_id + user_id for routing.
    Phone number resolved from env (M3_ESCALATION_PHONE_<tenant_id>_<user_id>) or
    M3_ESCALATION_PHONE for single-tenant dev; otherwise logs and returns (no-op).
    """
    to_phone = _resolve_m3_escalation_phone(tenant_id, user_id)
    if not to_phone:
        logger.info(
            "M3 escalation (no phone): tenant=%s user=%s event_type=%s score=%s reason=%s",
            tenant_id, user_id, event_type, identity_entropy_score, reason,
        )
        return {"ok": False, "reason": "no_phone_configured"}

    text = _m3_escalation_message(event_type, reason, identity_entropy_score, resource_type)
    try:
        from src.integrations.whatsapp import WhatsAppIntegration
        wa = WhatsAppIntegration()
        wa.connect()
        result = await wa.send_message(to=to_phone, text=text, user_id=user_id)
        logger.info("M3 WhatsApp escalation sent to %s tenant=%s user=%s", to_phone, tenant_id, user_id)
        return result
    except Exception as e:
        logger.warning("M3 WhatsApp escalation send failed: %s", e)
        return {"ok": False, "error": str(e)}


def _resolve_m3_escalation_phone(tenant_id: str, user_id: str) -> str | None:
    """Resolve WhatsApp destination for tenant/user. Env: M3_ESCALATION_PHONE or M3_ESCALATION_PHONE_<tenant_id>_<user_id>."""
    import os
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
    """Template message per spec 8."""
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
