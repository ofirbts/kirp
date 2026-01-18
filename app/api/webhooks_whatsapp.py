import os
import logging
from fastapi import APIRouter, Request, HTTPException, Query
from app.agent.agent import agent
from app.integrations.whatsapp_gateway import wa_gateway

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])
logger = logging.getLogger(__name__)

# טוקן האימות שאתה מגדיר ב-Facebook Developer Portal
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "kirp_secure_token")

@router.get("/")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    """אימות ראשוני מול Meta"""
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ WhatsApp Webhook Verified Successfully")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/")
async def receive_whatsapp(request: Request):
    """קבלת הודעה חיה ועיבודה דרך הסוכן"""
    body = await request.json()
    try:
        # שליפת נתוני ההודעה ממבנה ה-JSON של Meta
        entry = body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
        if "messages" not in entry:
            return {"ok": True}

        message = entry["messages"][0]
        text = message.get("text", {}).get("body")
        sender_phone = message.get("from")

        if text and sender_phone:
            logger.info(f"📱 New WA message from {sender_phone}: {text[:30]}...")
            
            # הפעלה של ה-Agent (משתמש ב-RAG ובזיכרון)
            result = await agent.query(text, user_id=sender_phone)
            answer = result["answer_text"]

            # שליחה חזרה דרך ה-Gateway הישיר שלך
            wa_gateway.send_message(sender_phone, answer)
            
        return {"ok": True}
    except Exception as e:
        logger.error(f"❌ WhatsApp Webhook Error: {e}")
        return {"ok": False, "error": str(e)}