from app.models.memory import MemoryRecord, MemoryType
from app.storage.memory import save_memory
from app.llm.client import llm_call


async def summarize_memories(memories: list[MemoryRecord]) -> MemoryRecord:
    text_blob = "\n".join(m.content for m in memories)

    prompt = f"""
    סכם את הזיכרונות הבאים למשפט אחד ברור:
    {text_blob}
    """

    summary = await llm_call(prompt)

    record = MemoryRecord(
        source="llm_summary",
        content=summary,
        memory_type=MemoryType.SUMMARY,
        strength=3
    )

    await save_memory(record)
    return record
