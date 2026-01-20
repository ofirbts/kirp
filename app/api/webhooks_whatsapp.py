import os
import logging
import uuid
from app.core.persistence import PersistenceManager
from app.models.schemas import IngestionJob
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
            # 1. יצירת Ingestion Job (כדי שהמידע יישמר ב-Vector Store)
            job_id = str(uuid.uuid4())
            await PersistenceManager.create_ingestion_job(
                IngestionJob(id=job_id, source="WhatsApp", status="PENDING")
            )
            
            # 2. הרצת ה-Agent (מענה מהיר על בסיס זיכרון קיים)
            result = await agent.query(text, user_id=sender_phone)
            
            # 3. שליחה חזרה
            wa_gateway.send_message(sender_phone, result["answer_text"])
                        
        return {"ok": True}
    except Exception as e:
        logger.error(f"❌ WhatsApp Webhook Error: {e}")
        return {"ok": False, "error": str(e)}