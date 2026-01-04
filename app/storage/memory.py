from app.storage.mongo import db
from app.models.memory import MemoryRecord
from datetime import datetime, timezone


memory_collection = db["memories"]


async def save_memory(record: MemoryRecord):
    existing = await memory_collection.find_one({
        "memory_type": record.memory_type,
        "content": record.content
    })

    if existing:
        await memory_collection.update_one(
            {"_id": existing["_id"]},
            {
                "$inc": {"strength": 1},
                "$set": {"last_updated": datetime.now(timezone.utc)}
            }
        )
    else:
        await memory_collection.insert_one(record.dict())
