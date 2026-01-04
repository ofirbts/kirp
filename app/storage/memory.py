from datetime import datetime, timedelta, timezone
from typing import List

from app.models.memory import MemoryRecord
from app.storage.mongo import db

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


async def fetch_recent_memories(limit: int = 20) -> List[MemoryRecord]:
    cursor = (
        memory_collection
        .find()
        .sort("created_at", -1)
        .limit(limit)
    )

    return [MemoryRecord(**doc) async for doc in cursor]


async def fetch_memories_by_days(days: int) -> List[MemoryRecord]:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    cursor = memory_collection.find({
        "created_at": {"$gte": since}
    })

    return [MemoryRecord(**doc) async for doc in cursor]
