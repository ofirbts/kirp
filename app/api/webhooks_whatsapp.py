from fastapi import APIRouter, Request, HTTPException, Query
from app.agent.agent import agent
from app.integrations.whatsapp_gateway import wa_gateway
from app.core.tenant import TenantContext
import os

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_secure_token")

@router.get("/")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    """אימות ה-Webhook מול Meta (קורה פעם אחת בהגדרה)"""
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/")
async def receive_whatsapp(request: Request):
    """קבלת הודעה חיה ממשתמש"""
    body = await request.json()
    
    try:
        # חילוץ נתוני ההודעה מהמבנה של Meta
        entry = body["entry"][0]["changes"][0]["value"]
        if "messages" not in entry:
            return {"ok": True} # התעלמות מאירועים שהם לא הודעה (כמו Status)

        msg = entry["messages"][0]
        text = msg.get("text", {}).get("body")
        phone = msg["from"]

        if not text:
            return {"ok": True}

        # 1. זיהוי Tenant (לוגיקה פשוטה כרגע, אפשר לשכלל)
        # בהמשך תוכל לממש: TenantContext.set(resolve_tenant(phone))
        TenantContext.set("whatsapp_user") 

        # 2. הרצת ה-Agent
        # משתמשים ב-agent_query שתומך ב-Planner ו-Tools
        result = await agent.agent_query(text)
        answer = result.get("answer", "מצטער, לא הצלחתי לעבד את הבקשה.")

        # 3. שליחת תשובה חזרה
        wa_gateway.send_message(phone, answer)

        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}