import logging
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

# ייבוא הרכיבים הפנימיים
from app.core.persistence import PersistenceManager
from app.api import (
    sources, agents, insights, improvements, 
    jobs_extra, self_improving, ingest, 
    ingest_batch, auth, auth_google, protected, 
    status, webhooks_whatsapp, webhooks_twilio,
    query  # <--- ייבוא ה-Router החדש שסידרנו
)

# הגדרת לוגר
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIRP-API")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 KIRP OS Core Starting...")
    try:
        # וידוי חיבור לבסיס הנתונים
        await PersistenceManager.get_db() 
        logger.info("✅ Database Connection Verified")
    except Exception as e:
        logger.error(f"❌ Database Connection Failed: {e}")
    
    yield
    logger.info("🛑 SHUTTING DOWN KIRP OS...")

app = FastAPI(title="KIRP Intelligence OS API", lifespan=lifespan)

# --- חיבור ה-Routers ---
# סדר ה-Routers קובע את סדר הופעתם ב-Swagger (docs)
app.include_router(auth.router)
app.include_router(auth_google.router)
app.include_router(query.router)  # <--- הוספנו את הראוטר החדש (מכיל את /query ו-/query/ask)
app.include_router(protected.router)
app.include_router(sources.router)
app.include_router(agents.router)
app.include_router(insights.router)
app.include_router(improvements.router)
app.include_router(jobs_extra.router)
app.include_router(self_improving.router)
app.include_router(ingest.router)
app.include_router(ingest_batch.router)
app.include_router(webhooks_whatsapp.router)
app.include_router(webhooks_twilio.router, prefix="/webhooks/twilio", tags=["Twilio"])

# --- Endpoints כלליים (Dashboard & Logs) ---

@app.get("/health", tags=["System"])
async def health():
    return await PersistenceManager.get_system_health()

@app.get("/dashboard/summary/{user_id}", tags=["Dashboard"])
async def dashboard_summary(user_id: str) -> Dict[str, Any]:
    try:
        metrics = await PersistenceManager.get_dashboard_metrics(user_id)
        health_status = await PersistenceManager.get_system_health()
        return {
            "metrics": metrics,
            "health": health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.exception("Dashboard summary failed")
        raise HTTPException(status_code=500, detail="Dashboard error")

@app.get("/jobs/all", tags=["System"])
async def get_all_jobs():
    return await PersistenceManager.get_all_jobs()

@app.get("/system/logs", tags=["System"])
async def get_system_logs():
    db = await PersistenceManager.get_db()
    cursor = db.events.find().sort("created_at", -1).limit(50)
    events = await cursor.to_list(length=50)
    
    return [
        {
            "timestamp": e.get("created_at", datetime.now()).isoformat(),
            "level": e.get("level", "INFO"), 
            "message": f"{e.get('event_type')} - {e.get('data', {}).get('source', 'unknown')}"
        } for e in events
    ]