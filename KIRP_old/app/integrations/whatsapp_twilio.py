# app/integrations/whatsapp_twilio.py
"""
Twilio WhatsApp Provider for KIRP
- משתמש ב-HTTP API של Twilio
- תומך במצב mock אם אין קונפיגורציה אמיתית
"""

import os
import logging
from typing import Dict, Any

import requests

from app.integrations.whatsapp_gateway import WhatsAppGateway

logger = logging.getLogger(__name__)


class TwilioWhatsAppGateway(WhatsAppGateway):
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")  # e.g. 'whatsapp:+14155238886'

        if not self.account_sid or not self.auth_token or not self.from_number:
            logger.warning(
                "TwilioWhatsAppGateway initialized in MOCK mode "
                "(missing TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_NUMBER)"
            )

        self.url = (
            f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            if self.account_sid and self.account_sid != "mock"
            else None
        )

    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        # Mock mode – no real call
        if not self.url:
            logger.info(f"🧪 [MOCK TWILIO WA] → {to}: {text[:160]}")
            return {
                "status": "mock_success",
                "provider": "twilio",
                "target": to,
                "preview": text[:160],
            }

        payload = {
            "From": self.from_number,
            "To": f"whatsapp:{to}",
            "Body": text,
        }

        try:
            response = requests.post(
                self.url,
                data=payload,
                auth=(self.account_sid, self.auth_token),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Twilio WA sent: sid={data.get('sid')}")
            return {
                "status": "success",
                "provider": "twilio",
                "message_id": data.get("sid"),
                "raw": data,
            }
        except Exception as e:
            logger.error(f"Twilio Send Error: {str(e)}")
            return {
                "status": "error",
                "provider": "twilio",
                "message": str(e),
            }
