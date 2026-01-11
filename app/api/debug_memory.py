from fastapi import APIRouter
from app.rag.vector_store import list_memories_for_ui

router = APIRouter()

@router.get("/debug/memories")
async def debug_memories():
    memories = list_memories_for_ui(limit=20)
    return {
        "count": len(memories),
        "memories": memories
    }

