from app.models.memory import MemoryRecord, MemoryType
from app.storage.memory import save_memory, fetch_memories_by_days
from app.services.memory_intelligence.summarize import summarize_cluster


async def generate_weekly_summary(days: int = 7) -> MemoryRecord:
    memories = await fetch_memories_by_days(days)

    if not memories:
        raise ValueError("No memories found for weekly summary")

    summary_text = await summarize_cluster(memories)

    summary_memory = MemoryRecord(
        source="intelligence.weekly",
        content=summary_text,
        memory_type=MemoryType.SUMMARY
    )

    await save_memory(summary_memory)

    return summary_memory
