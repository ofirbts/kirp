"""
Stripe webhooks — verify signatures and map billing events to tenant lifecycle.

Subscription metadata must include ``tenant_id`` (Postgres ``tenants.id`` UUID string).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import stripe

from src.services.tenants_service import TenantLifecycleError, update_tenant_lifecycle

logger = logging.getLogger(__name__)


def verify_webhook_signature(payload: bytes, sig_header: str) -> dict[str, Any]:
    """
    Validate ``Stripe-Signature`` and return the event as a plain dict.
    """
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET is not configured")
    if not sig_header or not sig_header.strip():
        raise ValueError("missing Stripe-Signature header")

    event = stripe.Webhook.construct_event(payload, sig_header, secret)
    to_dict = getattr(event, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(event, dict):
        return event
    raise TypeError("unexpected Stripe event type")


def _tenant_id_from_subscription(sub: dict[str, Any]) -> str | None:
    md = sub.get("metadata") or {}
    tid = md.get("tenant_id")
    if isinstance(tid, str) and tid.strip():
        return tid.strip()
    return None


async def handle_webhook(event: dict[str, Any]) -> None:
    """
    Apply lifecycle updates for supported Stripe event types.

    - ``customer.subscription.created`` → ``active``
    - ``customer.subscription.deleted`` → ``suspended``
    """
    etype = event.get("type")
    data = event.get("data") or {}
    obj = data.get("object")
    if not isinstance(obj, dict):
        return

    if etype == "customer.subscription.created":
        tid = _tenant_id_from_subscription(obj)
        if not tid:
            logger.warning("Stripe subscription.created: missing metadata.tenant_id")
            return
        try:
            await update_tenant_lifecycle(tid, "active")
        except TenantLifecycleError as e:
            logger.warning("Stripe subscription.created: %s", e)
        return

    if etype == "customer.subscription.deleted":
        tid = _tenant_id_from_subscription(obj)
        if not tid:
            logger.warning("Stripe subscription.deleted: missing metadata.tenant_id")
            return
        try:
            await update_tenant_lifecycle(tid, "suspended")
        except TenantLifecycleError as e:
            logger.warning("Stripe subscription.deleted: %s", e)
        return
