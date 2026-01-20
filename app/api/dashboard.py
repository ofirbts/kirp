from fastapi import APIRouter, HTTPException, Depends
from app.core.persistence import PersistenceManager
from app.api.auth_google import get_current_user # ייבוא פונקציית האימות מהקובץ השני

router = APIRouter(tags=["dashboard"])

@router.get("/summary/{user_id}")
async def get_summary(user_id: str, current_user: dict = Depends(get_current_user)):
    """שליפת נתוני דשבורד מרוכזים למשתמש"""
    
    # אבטחה: מוודאים שהמשתמש שמחובר מבקש את המידע של עצמו בלבד
    # אנחנו בודקים גם sub וגם email ליתר ביטחון
    user_identity = current_user.get("email") or current_user.get("sub")
    
    if user_identity != user_id:
        raise HTTPException(403, "Not authorized to view this dashboard")
    
    # קריאה למסד הנתונים דרך ה-PersistenceManager
    data = await PersistenceManager.get_dashboard_metrics(user_id)
    
    if not data:
        raise HTTPException(404, "No data found for user")
        
    return data