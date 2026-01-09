from fastapi import APIRouter, HTTPException
from app.core.persistence import PersistenceManager

router = APIRouter(prefix="/governance", tags=["Governance"])

@router.get("/approvals")
async def get_pending_approvals():
    # שולף מהאירועים את כל מה שמחכה לאישור
    events = PersistenceManager.get_events_by_type("human_approval_required")
    return {"pending": [e for e in events if not e.get("resolved")]}

@router.post("/approve/{event_id}")
async def approve_tool(event_id: str):
    # כאן תהיה הלוגיקה שמפעילה את הכלי אחרי אישור
    return {"status": "approved", "event_id": event_id}