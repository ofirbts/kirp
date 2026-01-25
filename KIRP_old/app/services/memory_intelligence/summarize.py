# app/services/memory_intelligence/summarize.py
from app.models.memory import MemoryRecord
from app.llm.client import llm_call

async def summarize_cluster(memories: list[MemoryRecord]) -> str:
    """
    LLM-based summary of multiple memories.
    """
    joined = "\n".join(m.content for m in memories)

    prompt = f"""
    Summarize the following memories into clear, actionable insights:
    {joined}
    """

    return await llm_call(prompt)
