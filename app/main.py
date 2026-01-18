import asyncio
import logging
import uuid  # התיקון לשגיאה שקיבלת
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any

# ייבוא הרכיבים הפנימיים של המערכת
from app.core.persistence import PersistenceManager
from app.core.intelligence_engine import IntelligenceEngine
from app.agent.agent import agent

# הגדרת לוגים של המערכת
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# יצירת אפליקציית ה-FastAPI
app = FastAPI(title="KIRP Intelligence OS API")

@app.on_event("startup")
async def startup_db_client():
    """אתחול בסיס הנתונים עם עליית השרת למניעת קריסות Loop"""
    await PersistenceManager.get_db()
    logger.info("🚀 KIRP API Started & Connected to MongoDB")

@app.get("/health")
async def health_check():
    """סעיף 1.4 באפיון: בדיקת תקינות רכיבי המערכת בזמן אמת"""
    health = await PersistenceManager.get_system_health()
    return health

@app.get("/insights/{user_id}")
async def get_insights(user_id: str):
    """שליפת תובנות עבור המשתמש מתוך בסיס הנתונים"""
    try:
        insights = await PersistenceManager.get_user_insights(user_id)
        # ניקוי ה-ObjectIDs של MongoDB כדי שיהיה אפשר לשלוח אותם ב-JSON
        for insight in insights:
            if "_id" in insight: 
                insight["_id"] = str(insight["_id"])
        return insights
    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch insights")
    
@app.post("/query")
async def process_query(payload: Dict[str, Any]):
    """RAG Hybrid Search - ביצוע שאילתת ידע מול הוקטורים והסוכן"""
    query = payload.get("query")
    user_id = payload.get("user_id", "default")
    
    if not query:
        raise HTTPException(status_code=400, detail="No query provided")
    
    # הפעלת הסוכן (OmniAgent) לביצוע המשימה עם קונטקסט
    answer = await agent.process_task(
        task_description=f"Answer the following based on database context: {query}",
        context_query=query
    )
    return {"answer": answer, "status": "success"}

@app.post("/agents/generate")
async def create_agent_task(payload: Dict[str, Any]):
    """מנוע יצירת הסוכנים (סעיף 6.2 באפיון)"""
    name = payload.get("name")
    goal = payload.get("goal")
    
    if not name or not goal:
        raise HTTPException(status_code=400, detail="Missing name or goal")
        
    logger.info(f"Architecting new agent: {name} for goal: {goal}")
    
    # שימוש ב-uuid תקין
    return {
        "message": f"Agent '{name}' is being architected and deployed",
        "status": "processing",
        "agent_id": str(uuid.uuid4())
    }

@app.post("/logs/analyze")
async def analyze_logs(payload: Dict[str, Any]):
    """קבלת לוגים גולמיים וניתוחם באמצעות מנוע התובנות"""
    raw_logs = payload.get("logs", [])
    if not raw_logs:
        return {"message": "No logs provided", "insights": []}
    
    # שליחה למנוע התובנות שבנינו קודם
    insights = await IntelligenceEngine.analyze_system_logs(raw_logs)
    
    # שמירת התובנות ב-DB כדי שהן יופיעו ב-UI
    for insight in insights:
        await PersistenceManager.save_insight(insight)
        
    return {"status": "success", "insights_generated": len(insights)}