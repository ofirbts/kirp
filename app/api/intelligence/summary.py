from fastapi import APIRouter
from app.services.memory_intelligence.summarize import summarize_cluster
from app.storage.memory import fetch_recent_memories
from app.models.memory import MemoryRecord, MemoryType
from app.services.pipeline import ingest_memory

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

@router.post("/summary")
async def create_summary(limit: int = 20):
    memories = await fetch_recent_memories(limit)
    summary_text = await summarize_cluster(memories)

    summary_memory = MemoryRecord(
        source="system_summary",
        content=summary_text,
        memory_type=MemoryType.SUMMARY
    )

    await ingest_memory(summary_memory)

    return {
        "summary": summary_text,
        "stored": True,
        "based_on": len(memories)
    }
