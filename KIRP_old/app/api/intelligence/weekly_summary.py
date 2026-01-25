from fastapi import APIRouter
from app.services.memory_intelligence.summarize import summarize_cluster
from app.storage.memory import fetch_memories_by_days

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.get("/weekly-summary")
async def weekly_summary():
    memories = await fetch_memories_by_days(days=7)
    summary = await summarize_cluster(memories)

    return {
        "period": "last_7_days",
        "summary": summary
    }
