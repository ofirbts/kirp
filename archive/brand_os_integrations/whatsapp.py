"""
Twilio WhatsApp integration for Brand OS v3.
Sends messages via Twilio WhatsApp API. Requires TWILIO_SID, TWILIO_TOKEN, TWILIO_WHATSAPP_FROM.
"""

import os
from typing import Optional


def send_whatsapp(to: str, message: str) -> dict:
    """
    Send a WhatsApp message via Twilio.
    to: E.164 format (e.g. +1234567890).
    message: Body text.
    Returns dict with sid and status or error.
    """
    sid = os.environ.get("TWILIO_SID")
    token = os.environ.get("TWILIO_TOKEN")
    from_ = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    if not sid or not token:
        return {"ok": False, "error": "TWILIO_SID or TWILIO_TOKEN not set"}
    to_whatsapp = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    if not from_.startswith("whatsapp:"):
        from_ = f"whatsapp:{from_}"
    try:
        from twilio.rest import Client
        client = Client(sid, token)
        msg = client.messages.create(
            body=message,
            from_=from_,
            to=to_whatsapp,
        )
        return {"ok": True, "sid": msg.sid, "status": msg.status}
    except Exception as e:
        return {"ok": False, "error": str(e)}
