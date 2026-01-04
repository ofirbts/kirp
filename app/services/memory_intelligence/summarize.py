from app.models.memory import MemoryRecord
from app.llm.client import llm_call



async def summarize_cluster(memories: list[MemoryRecord]) -> str:
    joined = "\n".join(m.content for m in memories)

    prompt = f"""
    Summarize the following memories into clear insights:
    {joined}
    """

    return await llm_call(prompt)
