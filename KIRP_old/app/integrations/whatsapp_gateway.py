# app/integrations/whatsapp_gateway.py
"""
KIRP Unified WhatsApp Gateway

אחראי על:
- ממשק אחיד לשליחת הודעות WhatsApp
- בחירת ספק (mock / twilio / meta) לפי ENV
- אובייקט סינגלטון wa_gateway לשימוש בכל המערכת
"""

import os
import logging
from typing import Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppMessage:
    to: str
    text: str
    user_id: str = "system"


class WhatsAppGateway(ABC):
    """
    Abstract WhatsApp provider interface.
    כל ספק (Twilio / Meta / Mock) חייב לממש send_message.
    """

    @abstractmethod
    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        raise NotImplementedError


class MockWhatsAppGateway(WhatsAppGateway):
    """
    Mock provider for development & testing.
    לא דורש שום קונפיגורציה.
    """

    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        logger.info(f"🧪 [MOCK WHATSAPP] Sending to {to}: {text[:160]}")
        return {
            "status": "success",
            "provider": "mock",
            "message_id": f"mock_{abs(hash((to, text))) % 999999}",
        }


def get_whatsapp_gateway() -> WhatsAppGateway:
    """
    Factory function to return the correct provider based on ENV.
    WHATSAPP_PROVIDER ∈ {mock, twilio, meta}
    """
    provider = os.getenv("WHATSAPP_PROVIDER", "mock").lower()

    if provider == "twilio":
        try:
            from app.integrations.whatsapp_twilio import TwilioWhatsAppGateway

            logger.info("Using Twilio WhatsApp gateway")
            return TwilioWhatsAppGateway()
        except Exception as e:
            logger.error(f"Failed to init TwilioWhatsAppGateway, falling back to mock: {e}")
            return MockWhatsAppGateway()

    if provider == "meta":
        try:
            from app.integrations.whatsapp_meta import MetaWhatsAppGateway

            logger.info("Using Meta WhatsApp gateway")
            return MetaWhatsAppGateway()
        except Exception as e:
            logger.error(f"Failed to init MetaWhatsAppGateway, falling back to mock: {e}")
            return MockWhatsAppGateway()

    logger.info("Using Mock WhatsApp gateway")
    return MockWhatsAppGateway()


# Singleton instance for global use
wa_gateway: WhatsAppGateway = get_whatsapp_gateway()
