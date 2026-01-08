from fastapi import APIRouter
router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/")
async def get_tasks():
    return {
        "tasks": [
            {"title": "בדוק KIRP Dashboard", "status": "done", "priority": "high"},
            {"title": "הוסף זיכרון חדש", "status": "open", "priority": "medium"}
        ],
        "summary": "2/5 משימות הושלמו"
    }
