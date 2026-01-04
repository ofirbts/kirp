from app.storage.mongo import db
from app.models.memory import MemoryRecord

memory_collection = db["memories"]


async def save_memory(record: MemoryRecord) -> str:
    result = await memory_collection.insert_one(record.dict())
    return str(result.inserted_id)
