import requests
import os
from typing import Optional

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")

class WhatsAppGateway:
    def send_message(self, to: str, text: str) -> dict:
        if not WHATSAPP_TOKEN or WHATSAPP_TOKEN == "mock":
            print(f"🚫 WhatsApp Mock: To {to} -> {text}")
            return {"status": "mock_sent"}

        url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        
        response = requests.post(url, json=payload, headers=headers)
        return response.json()

wa_gateway = WhatsAppGateway()