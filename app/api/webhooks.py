from fastapi import APIRouter, Request, BackgroundTasks
from app.core.persistence import PersistenceManager
from app.models.schemas import IngestionJob
import uuid

router = APIRouter(prefix="/webhooks")

@router.post("/slack")
async def slack_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    # Slack Verification (Challenge)
    if "challenge" in data:
        return {"challenge": data["challenge"]}
    
    # חילוץ ההודעה והמשתמש
    event = data.get("event", {})
    if event.get("type") == "message" and not event.get("bot_id"):
        user_id = event.get("user")  # כאן אנחנו ממפים משתמש אמיתי
        content = event.get("text")
        
        # יצירת Job אמיתי ב-Pipeline
        job = IngestionJob(
            id=str(uuid.uuid4()),
            source="Slack",
            content=content,
            status="RECEIVED"
        )
        background_tasks.add_task(process_ingestion_pipeline, user_id, job)
        
    return {"status": "accepted"}

# פונקציית הצינור (Pipeline) האסינכרונית
async def process_ingestion_pipeline(user_id: str, job: IngestionJob):
    # 1. נרמול
    # 2. Chunking & Embedding (קריאה ל-Qdrant)
    # 3. שמירה ל-Persistence
    await PersistenceManager.update_job_status(job) # מעדכן ל-DONE בסוף