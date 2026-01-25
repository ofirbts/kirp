import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WhatsAppGateway:
    """
    Interface for WhatsApp Communication.
    """
    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        raise NotImplementedError("WhatsApp provider not implemented. Use a specific subclass.")

class MockWhatsAppGateway(WhatsAppGateway):
    """
    A Mock provider for testing and development.
    """
    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        logger.info(f"🧪 [MOCK WHATSAPP] Sending to {to}: {text}")
        return {"status": "success", "provider": "mock", "message_id": "mock_123"}

def get_whatsapp_gateway() -> WhatsAppGateway:
    """
    Factory function to return the correct provider based on ENV.
    """
    provider = os.getenv("WHATSAPP_PROVIDER", "mock").lower()
    
    if provider == "meta":
        try:
            from app.integrations.whatsapp_meta import MetaWhatsAppGateway
            return MetaWhatsAppGateway()
        except ImportError:
            logger.error("MetaWhatsAppGateway not found, falling back to mock.")
            return MockWhatsAppGateway()
            
    elif provider == "twilio":
        try:
            from app.integrations.whatsapp_twilio import TwilioWhatsAppGateway
            return TwilioWhatsAppGateway()
        except ImportError:
            logger.error("TwilioWhatsAppGateway not found, falling back to mock.")
            return MockWhatsAppGateway()
    
    # במקום להחזיר את ה-Interface הריק, מחזירים את ה-Mock
    return MockWhatsAppGateway()

# יצירת אובייקט סינגלטון לשימוש ברחבי האפליקציה
wa_gateway = get_whatsapp_gateway()