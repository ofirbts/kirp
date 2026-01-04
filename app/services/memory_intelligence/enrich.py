from app.models.memory import MemoryRecord,提醒
from app.llm.client import llm_call


async def enrich_memory(memory: MemoryRecord) -> dict:
    prompt = f"""
    Analyze the following memory and return:
    - memory_type (MESSAGE / TASK / FACT / IDEA)
    - importance (1-5)
    - tags (list)
    
    Memory:
    {memory.content}
    """

    response = await llm_call(prompt)

    return {
        "memory_type": response["memory_type"],
        "importance": response["importance"],
        "tags": response["tags"],
    }
