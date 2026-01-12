from typing import Dict, Any

class WhatsAppGateway:
    """
    Interface for WhatsApp Communication.
    Subclasses must implement the send_message method.
    """
    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        raise NotImplementedError("WhatsApp provider not implemented. Use a specific subclass.")

def get_whatsapp_gateway() -> WhatsAppGateway:
    """
    Factory function to return the correct provider based on ENV.
    """
    import os
    provider = os.getenv("WHATSAPP_PROVIDER", "mock")
    
    if provider == "meta":
        from app.integrations.whatsapp_meta import MetaWhatsAppGateway
        return MetaWhatsAppGateway()
    elif provider == "twilio":
        from app.integrations.whatsapp_twilio import TwilioWhatsAppGateway
        return TwilioWhatsAppGateway()
    
    # Default fallback to a Null/Mock provider if needed
    return WhatsAppGateway()
wa_gateway = WhatsAppGateway() # יוצר את האובייקט שה-API מחפש