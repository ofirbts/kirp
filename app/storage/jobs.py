from datetime import datetime, timezone
from app.models.job import Job
from app.storage.mongo import db

jobs_collection = db["jobs"]

async def create_job(job: Job):
    result = await jobs_collection.insert_one(job.dict())  # ✅ Pydantic v1
    return str(result.inserted_id)

async def update_job_status(job_id: str, status):
    await jobs_collection.update_one(
        {"id": job_id},
        {
            "$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
