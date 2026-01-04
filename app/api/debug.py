from fastapi import APIRouter
from app.rag.vector_store import debug_info
from app.storage.memory import memory_collection

router = APIRouter(tags=["Debug"])


@router.get("/vector-store")
def vector_store_debug():
    return debug_info()


@router.get("/memory")
async def debug_memory():
    cursor = memory_collection.find()
    items = []

    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)

    return {
        "total": len(items),
        "items": items
    }

