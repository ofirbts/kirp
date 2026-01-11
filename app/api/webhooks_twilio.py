from fastapi import APIRouter, Request, Form
from app.agent.agent import agent
from app.core.tenant import TenantContext
import requests
import os
import json

router = APIRouter(prefix="/webhooks/twilio", tags=["Twilio"])

# נתוני Twilio מה-.env
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER", "whatsapp:+14155238886")

@router.post("/")
async def receive_twilio_whatsapp(
    From: str = Form(...), 
    Body: str = Form(...)
):
    """קבלת הודעה מ-Twilio ועיבודה על ידי הסוכן"""
    print(f"\n📩 הודעה חדשה מ-{From}: {Body}")
    
    try:
        # 1. ניקוי מספר הטלפון לזיהוי משתמש
        phone = From.replace("whatsapp:", "")
        TenantContext.set(f"user_{phone}")

        # 2. הרצת השאילתה מול ה-Agent
        print("🤖 הסוכן חושב...")
        result = await agent.agent_query(Body)
        
        # הדפסת התוצאה המלאה לטרמינל לצרכי ניפוי שגיאות
        print(f"DEBUG: תוצאת הסוכן המלאה: {json.dumps(result, indent=2, ensure_ascii=False)}")

        # בדיקה אם יש תשובה או שהסוכן החזיר שגיאה
        if "answer" in result and result["answer"]:
            answer = result["answer"]
        elif "detail" in result:
            answer = f"מצטער, הסוכן החזיר שגיאה: {result['detail']}"
        else:
            answer = "מצטער, לא הצלחתי לנסח תשובה."

        # 3. שליחת התשובה חזרה לוואטסאפ
        print(f"📤 שולח תשובה חזרה: {answer}")
        twilio_res = send_reply_via_twilio(From, answer)
        
        # בדיקה אם Twilio הצליחה לשלוח
        if "sid" in twilio_res:
            print("✅ התשובה נשלחה בהצלחה לוואטסאפ!")
        else:
            print(f"❌ שגיאה בשליחה דרך Twilio: {twilio_res}")

        return {"status": "success"}

    except Exception as e:
        print(f"❌ קריסה ב-Webhook: {str(e)}")
        # שליחת הודעת שגיאה למשתמש בוואטסאפ כדי שלא יישאר בלי מענה
        send_reply_via_twilio(From, "חלה שגיאה טכנית בעיבוד ההודעה שלך.")
        return {"status": "error", "detail": str(e)}

def send_reply_via_twilio(to_number, message):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    data = {
        "From": TWILIO_NUMBER,
        "To": to_number,
        "Body": message
    }
    response = requests.post(url, data=data, auth=(TWILIO_SID, TWILIO_AUTH_TOKEN))
    return response.json()