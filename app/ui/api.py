import os
import asyncio
# ייבוא ישיר של הלוגיקה מהפרויקט שלך
from app.agent.agent import agent
from app.core.persistence import PersistenceManager
from app.core.metrics import metrics

# פונקציה לעזרה בהרצת קוד אסינכרוני בתוך Streamlit
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def get_health():
    # בדיקה ישירה של המטריקות
    return {"status": "healthy", "metrics": metrics.snapshot()}

def ingest(text):
    # הוספה ישירה למסד הנתונים דרך ה-PersistenceManager
    event_id = PersistenceManager.append_event(
        "knowledge_add", 
        {"text": text, "source": "ui_manual"}
    )
    return {"status": "success", "event_id": event_id}

def get_tasks():
    # שליפת משימות ישירות מה-DB
    return PersistenceManager.get_pending_approvals()

def ask(question, debug=False):
    # הפעלת הסוכן ישירות (בלי לעבור ב-API חיצוני)
    res = run_async(agent.query(question))
    return res

def get_status():
    return metrics.snapshot()