from datetime import datetime
from bson import ObjectId
from app.storage.mongo import jobs_collection

async def create_job(job: dict):
    job["created_at"] = datetime.utcnow()
    result = await jobs_collection.insert_one(job)
    return str(result.inserted_id)

async def update_job_status(job_id: str, status: str):
    await jobs_collection.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": status}}
    )
