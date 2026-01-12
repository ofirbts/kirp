import requests
import os
from typing import Dict, Any
from app.integrations.whatsapp_gateway import WhatsAppGateway

class MetaWhatsAppGateway(WhatsAppGateway):
    def __init__(self):
        self.token = os.getenv("WHATSAPP_TOKEN")
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID")
        self.url = f"https://graph.facebook.com/v18.0/{self.phone_id}/messages"

    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        if not self.token or self.token == "mock":
            return {"status": "mock_success", "target": to}

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        
        response = requests.post(self.url, json=payload, headers=headers)
        return response.json()