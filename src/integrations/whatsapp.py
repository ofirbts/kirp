"""
WhatsApp Integration — Bi-directional.

- Inbound: webhooks → Events
- Outbound: send messages → Actions
- Real-time notifications
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppMessage:
    to: str
    text: str
    user_id: str = "system"


class WhatsAppIntegration:
    """
    WhatsApp API (Twilio / Meta). Bi-directional.
    """

    def __init__(self) -> None:
        import os
        self._provider = (os.getenv("WHATSAPP_PROVIDER", "mock") or "mock").lower()
        self._client: Any = None

    def connect(self) -> None:
        """Initialize provider client."""
        if self._provider == "twilio":
            try:
                from twilio.rest import Client
                import os
                sid = os.getenv("TWILIO_ACCOUNT_SID", "")
                token = os.getenv("TWILIO_AUTH_TOKEN", "")
                if sid and token:
                    self._client = Client(sid, token)
                    logger.info("WhatsAppIntegration (Twilio) connected")
            except Exception as e:
                logger.error("WhatsApp Twilio init failed: %s", e)
        else:
            logger.info("WhatsAppIntegration using mock")

    async def send_message(self, to: str, text: str, user_id: str = "system") -> dict[str, Any]:
        """Send WhatsApp message. Outbound action."""
        if not self._client and self._provider == "twilio":
            self.connect()
        if self._provider == "mock" or not self._client:
            logger.info("[MOCK WhatsApp] to=%s text=%s", to, text[:80])
            return {"ok": True, "provider": "mock", "to": to}
        try:
            from twilio.rest import Client
            # Twilio: use messaging service or from number
            msg = self._client.messages.create(
                body=text,
                from_=str(self._client).split("'")[0],  # placeholder
                to=to,
            )
            return {"ok": True, "provider": "twilio", "sid": msg.sid}
        except Exception as e:
            logger.error("WhatsApp send failed: %s", e)
            return {"ok": False, "error": str(e)}

    def parse_webhook_payload(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse Meta/Twilio webhook body into unified event payloads (tenant_id etc. set by caller)."""
        events: list[dict[str, Any]] = []
        # Meta format
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                val = change.get("value", {})
                for msg in val.get("messages", []):
                    msg_id = msg.get("id")
                    text = (msg.get("text") or {}).get("body", "")
                    events.append({
                        "source": "whatsapp",
                        "content": text,
                        "metadata": {"external_id": msg_id or "", "from": msg.get("from"), "msg_id": msg_id},
                    })
        # Simple format
        if not events and "from" in body and "text" in body:
            ext_id = body.get("msg_id") or body.get("from", "") + "_" + str(body.get("timestamp", ""))
            events.append({
                "source": "whatsapp",
                "content": body["text"],
                "metadata": {"external_id": ext_id, "from": body["from"]},
            })
        return events
