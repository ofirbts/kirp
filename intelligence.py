from fastapi import APIRouter
router = APIRouter(prefix="/intelligence", tags=["intelligence"])

@router.post("/weekly-summary")
async def weekly_summary(request: dict):
    return {
        "week": "שבוע 1/2026",
        "memories_added": 27,
        "key_activities": ["פיתוח KIRP", "בדיקת Dashboard"],
        "recommendations": ["הוסף עוד זיכרונות", "בדוק WhatsApp"]
    }
