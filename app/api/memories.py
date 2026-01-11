from fastapi import APIRouter
from app.storage.memory_ledger import load_all_memories

router = APIRouter(prefix="/memories", tags=["memories"])

@router.get("/")
def list_memories(limit: int = 100):
    memories = load_all_memories(limit)
    return {
        "count": len(memories),
        "memories": memories
    }
