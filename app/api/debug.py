from fastapi import APIRouter
from app.rag.vector_store import debug_info
from app.storage.memory import memory_collection

router = APIRouter(tags=["Debug"])


@router.get("/vector-store")
def vector_store_debug():
    return debug_info()


@router.get("/memory")
async def memory_debug():
    total = await memory_collection.count_documents({})
    by_type = {}

    async for doc in memory_collection.find():
        t = doc.get("memory_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total_memories": total,
        "by_type": by_type,
        "vector_store": debug_info(),
        "status": "memory system alive"
    }
