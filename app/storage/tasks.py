from datetime import datetime, timezone
from app.models.task import Task
from app.storage.mongo import db

tasks_collection = db["tasks"]

async def create_task(task: Task):
    await tasks_collection.insert_one({
        **task.dict(),
        "status": "open",
        "created_at": datetime.now(timezone.utc)
    })

async def fetch_open_tasks():
    cursor = tasks_collection.find({"status": "open"})
    return [doc async for doc in cursor]
