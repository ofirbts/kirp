from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.persistence import PersistenceManager
from app.services.notion import notion
from app.agent.agent import agent # הוספנו את ה-Agent
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/governance", tags=["Governance"])

class DecisionRequest(BaseModel):
    event_id: str
    notes: str = "Approved via Dashboard"

@router.get("/pending")
async def list_pending():
    return {"pending": PersistenceManager.get_pending_approvals()}

@router.post("/approve")
async def approve(req: DecisionRequest):
    events = PersistenceManager.get_all_events(limit=500)
    event = next((e for e in events if e['id'] == req.event_id), None)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event['type'] == "task_identified":
        task_title = event['data'].get('task', 'New Task from KIRP')
        if notion.enabled():
            notion.create_task(title=f"✅ {task_title}", trace_id=req.event_id, source="KIRP OS")
    
    PersistenceManager.update_event_status(req.event_id, "approved", req.notes)
    return {"status": "success", "action": "approved"}

# הוספת ה-Endpoints החדשים מהמשימה לתוך הקובץ הקיים שלך:
@router.post("/scrape")
async def scrape(task: dict):
    # כאן אנחנו משתמשים בלוגיקת ה-Persistence ישירות
    eid = PersistenceManager.append_event("task_identified", task, requires_approval=True)
    return {"status": "success", "event_id": eid}