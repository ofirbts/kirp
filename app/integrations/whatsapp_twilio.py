import os
import logging
from typing import Dict, Any
from app.integrations.whatsapp_gateway import WhatsAppGateway

logger = logging.getLogger(__name__)

class TwilioWhatsAppGateway(WhatsAppGateway):
    def __init__(self):
        # Twilio דורש Account SID ו-Auth Token
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_WHATSAPP_NUMBER") # בדרך כלל 'whatsapp:+14155238886'
        
        # כתובת ה-API של Twilio
        self.url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        if not self.account_sid or self.account_sid == "mock":
            return {"status": "mock_success", "provider": "twilio", "target": to}

        import requests
        
        # Twilio משתמש ב-Basic Auth
        payload = {
            "From": self.from_number,
            "To": f"whatsapp:{to}",
            "Body": text,
        }
        
        try:
            response = requests.post(
                self.url,
                data=payload,
                auth=(self.account_sid, self.auth_token)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Twilio Send Error: {str(e)}")
            return {"status": "error", "message": str(e)}