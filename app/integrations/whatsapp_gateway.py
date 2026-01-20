import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WhatsAppGateway:
    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        raise NotImplementedError()

class MockWhatsAppGateway(WhatsAppGateway):
    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        logger.info(f"🧪 [MOCK WA] To {to}: {text}")
        return {"status": "success", "id": "mock_123"}

def get_whatsapp_gateway() -> WhatsAppGateway:
    provider = os.getenv("WHATSAPP_PROVIDER", "mock").lower()
    if provider == "twilio":
        from app.integrations.whatsapp_twilio import TwilioWhatsAppGateway
        return TwilioWhatsAppGateway()
    # כאן תוכל להוסיף את Meta בעתיד
    return MockWhatsAppGateway()

wa_gateway = get_whatsapp_gateway()