from fastapi import APIRouter, Request, Response
import logging
from app.integrations.whatsapp_gateway import get_whatsapp_gateway

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("")
async def twilio_webhook(request: Request):
    """
    Handle incoming Twilio WhatsApp/SMS messages.
    """
    try:
        form_data = await request.form()
        incoming_msg = form_data.get('Body', '')
        sender = form_data.get('From', '')

        logger.info(f"Incoming Twilio message from {sender}: {incoming_msg}")

        # שליחה ל-Gateway (לצורך אישור קבלה או תגובה מהירה)
        # gateway = get_whatsapp_gateway()
        # gateway.send_message(to=sender, text="Received!")

        return Response(content="<Response></Response>", media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in Twilio webhook: {str(e)}")
        return Response(status_code=500)
